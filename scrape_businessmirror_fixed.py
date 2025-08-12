import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
try:
    from textblob import TextBlob
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    print("Note: Sentiment analysis libraries not available. Install with: pip install textblob vaderSentiment")

# Load environment variables
load_dotenv()

# Initialize sentiment analyzer
if SENTIMENT_AVAILABLE:
    analyzer = SentimentIntensityAnalyzer()

def get_sentiment_analysis(text):
    """Analyze sentiment of text using both TextBlob and VADER"""
    if not SENTIMENT_AVAILABLE or not text:
        print(f"[DEBUG] Sentiment not available or empty text. SENTIMENT_AVAILABLE={SENTIMENT_AVAILABLE}, text='{text}'")
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'Neutral',
            'emotion': 'Neutral'
        }
    try:
        print(f"[DEBUG] Analyzing sentiment for text: {text[:100]}... (len={len(text)})")
        # TextBlob analysis
        blob = TextBlob(text)
        textblob_score = blob.sentiment.polarity
        print(f"[DEBUG] TextBlob score: {textblob_score}")
        # VADER analysis  
        vader_scores = analyzer.polarity_scores(text)
        vader_compound = vader_scores['compound']
        print(f"[DEBUG] VADER compound: {vader_compound}")
        # Combine scores (average)
        combined_score = (textblob_score + vader_compound) / 2
        print(f"[DEBUG] Combined score: {combined_score}")
        # Determine sentiment label
        if combined_score >= 0.1:
            sentiment_label = 'Positive'
            emotion = 'Optimistic' if combined_score > 0.3 else 'Positive'
        elif combined_score <= -0.1:
            sentiment_label = 'Negative'
            emotion = 'Concerning' if combined_score < -0.3 else 'Negative'
        else:
            sentiment_label = 'Neutral'
            emotion = 'Neutral'
        return {
            'sentiment_score': round(combined_score, 3),
            'sentiment_label': sentiment_label,
            'emotion': emotion
        }
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'Neutral',
            'emotion': 'Neutral'
        }

def categorize_news(title, description=""):
    """Categorize news based on keywords in title and description"""
    text = (title + " " + description).lower()
    
    # Define category keywords
    categories = {
        'Banking & Finance': ['bank', 'financial', 'loan', 'credit', 'investment', 'fund', 'bsp', 'interest rate', 'monetary', 'finance', 'budget', 'tax', 'bir', 'dbm', 'gsis'],
        'Stock Market': ['stock', 'share', 'psei', 'market', 'trading', 'equity', 'index', 'surge', 'rally', 'decline', 'navps'],
        'Energy & Utilities': ['fuel', 'oil', 'gas', 'energy', 'power', 'electricity', 'meralco', 'utility', 'renewable', 'erc'],
        'Real Estate': ['property', 'real estate', 'housing', 'construction', 'development', 'land', 'residential', 'megaworld', 'filinvest'],
        'Technology': ['tech', 'digital', 'innovation', 'software', 'app', 'platform', 'online', 'cyber', 'ai', 'artificial intelligence'],
        'Infrastructure': ['infrastructure', 'transport', 'road', 'bridge', 'airport', 'port', 'railway', 'construction', 'bcda'],
        'Retail & Consumer': ['retail', 'consumer', 'shopping', 'mall', 'store', 'sales', 'product', 'brand', 'puregold', 'sm'],
        'Manufacturing': ['manufacturing', 'factory', 'production', 'industrial', 'export', 'import', 'goods', 'smfb'],
        'Agriculture': ['agriculture', 'farming', 'crop', 'rice', 'food', 'agricultural', 'fishery', 'agri', 'coco', 'coconut'],
        'Government & Policy': ['government', 'policy', 'regulation', 'law', 'sec', 'bir', 'dof', 'congress', 'senate', 'marcos', 'president'],
        'International Trade': ['trade', 'export', 'import', 'international', 'global', 'foreign', 'overseas', 'canada', 'india', 'tariff'],
        'Economic Indicators': ['gdp', 'inflation', 'growth', 'economy', 'economic', 'recession', 'recovery'],
        'Companies': ['corp', 'corporation', 'inc', 'company', 'business', 'profit', 'earnings', 'revenue', 'income', 'stockholders'],
        'Health & Medical': ['health', 'medical', 'hospital', 'healthcare', 'medicine', 'doctor', 'pharmaceutical', 'doh']
    }
    
    # Check for category matches
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    
    return 'General Business'

def extract_article_info(article_element):
    """Extract article information from Business Mirror article element"""
    try:
        info = {
            'title': '',
            'url': '',
            'description': '',
            'category': '',
            'author': '',
            'published_date': ''
        }
        
        # Find title and URL - multiple selectors
        title_selectors = ['h2 a', 'h3 a', '.entry-title a', 'a[href*="/2025/"]']
        for selector in title_selectors:
            title_elem = article_element.select_one(selector)
            if title_elem:
                info['title'] = title_elem.get_text(strip=True)
                info['url'] = title_elem.get('href', '')
                break
        
        # Make URL absolute if relative
        if info['url'] and not info['url'].startswith('http'):
            info['url'] = 'https://businessmirror.com.ph' + info['url']
        
        # Extract description/summary
        desc_selectors = ['.entry-content', '.excerpt', 'p', '.summary']
        for selector in desc_selectors:
            desc_elem = article_element.select_one(selector)
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                if len(desc_text) > 20 and len(desc_text) < 500:
                    info['description'] = desc_text[:200] + "..." if len(desc_text) > 200 else desc_text
                    break
        
        # Extract category from breadcrumbs or category links
        category_selectors = ['[class*="category"]', '[href*="/business/"]', '.cat-links a']
        for selector in category_selectors:
            cat_elem = article_element.select_one(selector)
            if cat_elem:
                cat_text = cat_elem.get_text(strip=True)
                if cat_text and cat_text.lower() not in ['business', 'news', '']:
                    info['category'] = cat_text
                    break
        
        # Extract author
        author_selectors = ['.author', '.byline', '[rel="author"]', '.post-author']
        for selector in author_selectors:
            author_elem = article_element.select_one(selector)
            if author_elem:
                info['author'] = author_elem.get_text(strip=True)
                break
        
        # Extract date - enhanced to get actual article dates
        date_text = ''
        
        # First try to extract from URL pattern (/2025/08/11/ or /2025/08/12/)
        if info['url']:
            url_date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', info['url'])
            if url_date_match:
                year, month, day = url_date_match.groups()
                try:
                    # Convert month number to month name
                    date_obj = datetime(int(year), int(month), int(day))
                    date_text = date_obj.strftime("%B %d, %Y")
                    print(f"🔗 URL date extracted: {date_text}")
                except ValueError:
                    pass
        
        # If no URL date, try to extract from article text/headers with multiple approaches
        if not date_text:
            date_selectors = ['.published', '.date', 'time', '.post-date', '.entry-date', '[datetime]', '.byline time', '.entry-meta time']
            for selector in date_selectors:
                date_elem = article_element.select_one(selector)
                if date_elem:
                    # Try datetime attribute first
                    datetime_attr = date_elem.get('datetime')
                    if datetime_attr:
                        try:
                            # Handle various datetime formats
                            datetime_clean = datetime_attr.replace('Z', '+00:00').replace('T', ' ').split('+')[0].split('-')[0:3]
                            if len(datetime_clean) >= 3:
                                year, month, day = datetime_clean[0], datetime_clean[1], datetime_clean[2][:2]
                                parsed_date = datetime(int(year), int(month), int(day))
                                date_text = parsed_date.strftime("%B %d, %Y")
                                print(f"📅 Datetime attr extracted: {date_text}")
                                break
                        except:
                            pass
                    
                    # Try text content with better regex
                    elem_text = date_elem.get_text(strip=True)
                    # Look for various date formats
                    date_patterns = [
                        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
                        r'\d{1,2}[\s/\-](January|February|March|April|May|June|July|August|September|October|November|December)[\s/\-]\d{4}',
                        r'\d{4}[\s/\-]\d{1,2}[\s/\-]\d{1,2}'
                    ]
                    
                    for pattern in date_patterns:
                        date_match = re.search(pattern, elem_text, re.IGNORECASE)
                        if date_match:
                            try:
                                found_date = date_match.group(0)
                                # Try to parse it
                                for fmt in ["%B %d, %Y", "%B %d %Y", "%d %B %Y", "%Y-%m-%d", "%Y/%m/%d"]:
                                    try:
                                        parsed_date = datetime.strptime(found_date, fmt)
                                        date_text = parsed_date.strftime("%B %d, %Y")
                                        print(f"📰 Text date extracted: {date_text}")
                                        break
                                    except ValueError:
                                        continue
                                if date_text:
                                    break
                            except:
                                continue
                    if date_text:
                        break
        
        # If still no date, try to get it from the page's main content or meta tags
        if not date_text and info['url']:
            try:
                response = requests.get(info['url'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if response.status_code == 200:
                    page_soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try meta tags
                    meta_date_selectors = [
                        'meta[property="article:published_time"]',
                        'meta[name="pubdate"]',
                        'meta[name="date"]',
                        'meta[property="og:updated_time"]'
                    ]
                    
                    for selector in meta_date_selectors:
                        meta_elem = page_soup.select_one(selector)
                        if meta_elem:
                            content = meta_elem.get('content', '')
                            if content:
                                try:
                                    # Parse ISO date format
                                    parsed_date = datetime.fromisoformat(content.replace('Z', '+00:00').split('T')[0])
                                    date_text = parsed_date.strftime("%B %d, %Y")
                                    print(f"🏷️ Meta date extracted: {date_text}")
                                    break
                                except:
                                    pass
                        if date_text:
                            break
            except:
                pass
        
        # Final fallback to current date only if we couldn't extract any date
        if not date_text:
            print(f"⚠️ No date found, using current date")
            date_text = datetime.now().strftime("%B %d, %Y")
        
        info['published_date'] = date_text
        
        return info
    
    except Exception as e:
        print(f"Error extracting article info: {e}")
        return None

def is_article_from_target_dates(published_date):
    """Check if article is from today or yesterday (dynamic date filtering)"""
    if not published_date:
        return False
    
    try:
        # Dynamic target dates: today and yesterday
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # Format target dates
        target_dates = [
            today.strftime("%B %d, %Y"),
            yesterday.strftime("%B %d, %Y")
        ]
        
        print(f"🎯 Target dates: {target_dates}")
        print(f"📅 Checking article date: '{published_date}'")
        
        # Clean the date string
        clean_date = published_date.strip()
        
        # Check direct match
        if clean_date in target_dates:
            print(f"✅ Including article from {clean_date}")
            return True
        
        # Try to parse and compare dates more flexibly
        try:
            # Parse the article date
            article_date = datetime.strptime(clean_date, "%B %d, %Y").date()
            
            # Additional check: reject articles more than 7 days old
            days_diff = (today.date() - article_date).days
            if days_diff > 7:
                print(f"📅 Skipping old article from {clean_date} (more than 7 days old)")
                return False
            
            # Check if it matches today or yesterday
            if article_date in [today.date(), yesterday.date()]:
                print(f"✅ Including article from {clean_date}")
                return True
            else:
                print(f"📅 Skipping article from {clean_date} (not {today.strftime('%b %d')} or {yesterday.strftime('%b %d')}, {today.year})")
                return False
                
        except ValueError:
            # Try alternative date parsing
            import re
            date_match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', clean_date)
            if date_match:
                month_str, day_str, year_str = date_match.groups()
                
                # Only accept recent years to avoid old dates
                if int(year_str) < 2025:
                    print(f"📅 Skipping old article from {year_str}")
                    return False
                
                try:
                    article_date = datetime.strptime(f"{month_str} {day_str}, {year_str}", "%B %d, %Y").date()
                    
                    # Additional check: reject articles more than 7 days old
                    days_diff = (today.date() - article_date).days
                    if days_diff > 7:
                        print(f"📅 Skipping old article from {clean_date} (more than 7 days old)")
                        return False
                    
                    if article_date in [today.date(), yesterday.date()]:
                        print(f"✅ Including article from {clean_date}")
                        return True
                    else:
                        print(f"📅 Skipping article from {clean_date} (not {today.strftime('%b %d')} or {yesterday.strftime('%b %d')}, {today.year})")
                        return False
                except ValueError:
                    pass
        
        print(f"⚠️ Could not parse date: {published_date}")
        return False
        
    except Exception as e:
        print(f"Error checking date {published_date}: {e}")
        return False

def scrape_businessmirror_news():
    """Scrape news from Business Mirror business section and all subsections"""
    
    # List of all Business Mirror business URLs to scrape
    business_urls = [
        "https://businessmirror.com.ph/business/",
        "https://businessmirror.com.ph/business/companies/",
        "https://businessmirror.com.ph/news/economy/",
        "https://businessmirror.com.ph/business/export-unlimited/",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    all_news = []
    session = requests.Session()
    
    print(f"📰 Scraping Business Mirror business news from {len(business_urls)} sections...")
    
    for i, url in enumerate(business_urls, 1):
        try:
            print(f"  [{i}/{len(business_urls)}] Scraping: {url}")
            
            response = session.get(url, headers=headers)
            response.raise_for_status()
            
            # Add a delay between requests to be respectful
            time.sleep(1)
            
            soup = BeautifulSoup(response.text, "html.parser")
            news_list = []
            
            # Extract section name for categorization with improved mapping
            section_name = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
            
            # Map section names to cleaner categories
            section_mapping = {
                'business': 'General Business',
                'economy': 'Economy',
                'agri-commodities': 'Agriculture',
                'banking-finance': 'Banking & Finance',
                'businesssense': 'Business Analysis',
                'companies': 'Companies',
                'entrepreneur': 'Entrepreneurship', 
                'executive-views': 'Executive Insights',
                'export-unlimited': 'International Trade',
                'harvard-management-update': 'Management',
                'monday-morning': 'Market Analysis',
                'mutual-funds': 'Investment',
                'stock-market-outlook': 'Stock Market'
            }
            
            section_name = section_mapping.get(section_name, section_name.replace('-', ' ').title())
            
            # Multiple selectors to find articles
            article_selectors = [
                'article',
                '.post',
                '.entry',
                '[class*="post"]',
                '[class*="article"]'
            ]
            
            articles_found = []
            
            for selector in article_selectors:
                articles = soup.select(selector)
                if articles:
                    print(f"    Found {len(articles)} articles with selector '{selector}'")
                    articles_found.extend(articles)
                    break
            
            # Process found articles
            if articles_found:
                for article in articles_found[:20]:  # Limit to first 20 articles per section
                    article_info = extract_article_info(article)
                    
                    if article_info and article_info['title'] and article_info['url']:
                        # Skip if title is too short or URL is invalid
                        if len(article_info['title']) < 10:
                            continue
                        
                        # Filter by date - only include articles from today and yesterday
                        if not is_article_from_target_dates(article_info['published_date']):
                            continue
                        
                        # Use section name for better categorization (avoid redundancy)
                        base_category = article_info['category'] or categorize_news(article_info['title'], article_info['description'])
                        # Avoid redundant section naming like "Economy - Economy"
                        if section_name.lower() in base_category.lower():
                            category = base_category
                        else:
                            category = f"{section_name} - {base_category}"
                        
                        # Perform sentiment analysis
                        sentiment_data = get_sentiment_analysis(article_info['title'] + " " + article_info['description'])
                        
                        news_item = {
                            "title": article_info['title'],
                            "category": category,
                            "description": article_info['description'] or "No description available",
                            "link": article_info['url'],
                            "author": article_info['author'] or "Business Mirror",
                            "published_date": article_info['published_date'],
                            "sentiment_score": sentiment_data['sentiment_score'],
                            "sentiment_label": sentiment_data['sentiment_label'],
                            "emotion": sentiment_data['emotion'],
                            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Avoid duplicates
                        if not any(item['title'] == article_info['title'] for item in all_news):
                            all_news.append(news_item)
                            news_list.append(news_item)
            
            print(f"    ✅ Extracted {len(news_list)} filtered articles from this section")
            
        except Exception as e:
            print(f"    ❌ Error scraping {url}: {e}")
            continue
    
    print(f"📊 Total articles scraped: {len(all_news)}")
    
    if not all_news:
        print("⚠️ No articles found matching the date criteria")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_news)
    
    # Save to Excel with table
    filename = "businessmirror_news.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Business Mirror News', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Business Mirror News']
        
        # Create a table
        from openpyxl.worksheet.table import Table, TableStyleInfo
        table = Table(displayName="NewsTable1", ref=worksheet.dimensions)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                             showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        worksheet.add_table(table)
    
    print(f"📊 Saved {len(df)} news items to {filename} (with table 'NewsTable1')")
    
    # Display summary statistics
    print(f"\n📈 Summary Statistics:")
    print(f"   Total articles: {len(df)}")
    print(f"   Categories: {df['category'].nunique()}")
    print(f"   Sentiment distribution:")
    for sentiment, count in df['sentiment_label'].value_counts().items():
        print(f"     {sentiment}: {count}")
    
    # Upload to Azure Blob Storage
    try:
        print(f"\n☁️ Uploading to Azure Blob Storage...")
        
        # Azure connection setup
        connection_string = os.getenv('AZURE_CONNECTION_STRING')
        container_name = os.getenv('AZURE_CONTAINER_NAME')
        blob_path = "Data/NSI/data/Azure Databricks/Automation Scripts/News/businessmirror_news.xlsx"
        
        if connection_string:
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # Upload file
            with open(filename, "rb") as data:
                blob_service_client.get_blob_client(
                    container=container_name, 
                    blob=blob_path
                ).upload_blob(data, overwrite=True)
            
            print(f"✅ Successfully uploaded {filename} to Azure Blob Storage")
            print(f"📁 Container: {container_name}")
            print(f"🗂️ Path: {blob_path}")
        else:
            print("⚠️ Azure connection string not found in environment variables")
    
    except Exception as e:
        print(f"❌ Error uploading to Azure: {e}")
    
    print(f"✅ Complete! Business Mirror news file uploaded to Azure successfully.")

def upload_to_azure_blob(file_path, blob_name):
    """Upload file to Azure Blob Storage"""
    try:
        # Get Azure connection details from environment
        connection_string = os.getenv('AZURE_CONNECTION_STRING')
        container_name = os.getenv('AZURE_CONTAINER_NAME')
        blob_subfolder = "Data/NSI/data/Azure Databricks/Automation Scripts/News/"
        
        if not connection_string or not container_name:
            print("❌ Error: AZURE_CONNECTION_STRING or AZURE_CONTAINER_NAME not found in .env file")
            return False
        
        # Create the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Create the full blob path
        blob_path = blob_subfolder + blob_name
        
        # Upload the file
        with open(file_path, "rb") as data:
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_path
            )
            blob_client.upload_blob(data, overwrite=True)
        
        print(f"✅ Successfully uploaded {blob_name} to Azure Blob Storage")
        print(f"📁 Container: {container_name}")
        print(f"🗂️ Path: {blob_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error uploading to Azure Blob Storage: {e}")
        return False

if __name__ == "__main__":
    scrape_businessmirror_news()
