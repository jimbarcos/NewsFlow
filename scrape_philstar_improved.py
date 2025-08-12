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
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'Neutral',
            'emotion': 'Neutral'
        }
    
    try:
        # TextBlob analysis
        blob = TextBlob(text)
        textblob_score = blob.sentiment.polarity
        
        # VADER analysis  
        vader_scores = analyzer.polarity_scores(text)
        vader_compound = vader_scores['compound']
        
        # Combine scores (average)
        combined_score = (textblob_score + vader_compound) / 2
        
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

def extract_philstar_date(article_url, soup=None):
    """Extract publication date from Philstar article with support for relative time formats"""
    try:
        # Method 1: Extract from URL pattern 
        url_date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', article_url)
        if url_date_match:
            year, month, day = url_date_match.groups()
            try:
                date_obj = datetime(int(year), int(month), int(day))
                formatted_date = date_obj.strftime("%B %d, %Y")
                print(f"📅 Found URL date: {formatted_date}")
                return formatted_date
            except ValueError:
                pass
        
        # Method 2: Fetch the actual article page to get real publication date
        try:
            print(f"🔍 Fetching article page for date: {article_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(article_url, headers=headers, timeout=10)
            if response.status_code == 200:
                article_soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for actual publication date in article page
                date_selectors = [
                    'time[datetime]',
                    '.date',
                    '.published',
                    '.post-date',
                    '.article-date',
                    '.entry-date',
                    '[data-date]',
                    'meta[property="article:published_time"]',
                    'meta[name="pubdate"]',
                    '.timestamp',
                    '.publish-date'
                ]
                
                for selector in date_selectors:
                    date_elem = article_soup.select_one(selector)
                    if date_elem:
                        # Try datetime attribute first
                        datetime_attr = date_elem.get('datetime') or date_elem.get('content')
                        if datetime_attr:
                            try:
                                # Handle various datetime formats
                                if 'T' in datetime_attr:
                                    parsed_date = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00').split('T')[0])
                                else:
                                    parsed_date = datetime.fromisoformat(datetime_attr.split(' ')[0])
                                
                                formatted_date = parsed_date.strftime("%B %d, %Y")
                                print(f"📅 Found article page datetime: {formatted_date}")
                                return formatted_date
                            except:
                                pass
                        
                        # Try text content and handle relative time formats
                        date_text = date_elem.get_text(strip=True)
                        if date_text:
                            print(f"🔍 Found date text: '{date_text}'")
                            
                            # Handle relative time formats
                            relative_date = parse_relative_time(date_text)
                            if relative_date:
                                formatted_date = relative_date.strftime("%B %d, %Y")
                                print(f"📅 Parsed relative time to: {formatted_date}")
                                return formatted_date
                            
                            # Look for absolute date pattern in text
                            date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', date_text, re.IGNORECASE)
                            if date_match:
                                formatted_date = date_match.group(0)
                                print(f"📅 Found absolute date: {formatted_date}")
                                return formatted_date
                
                # Also check the main content for date patterns
                main_content = article_soup.get_text()
                date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', main_content, re.IGNORECASE)
                if date_match:
                    formatted_date = date_match.group(0)
                    print(f"📅 Found content date: {formatted_date}")
                    return formatted_date
                    
        except Exception as e:
            print(f"⚠️ Error fetching article page: {e}")
        
        # Method 3: If soup is provided (from main page), try to extract relative time
        if soup:
            date_selectors = [
                '.date',
                '.published',
                '.post-date',
                '.timestamp',
                '.time-ago',
                '.relative-time'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    if date_text:
                        print(f"🔍 Found main page date text: '{date_text}'")
                        
                        # Handle relative time formats
                        relative_date = parse_relative_time(date_text)
                        if relative_date:
                            formatted_date = relative_date.strftime("%B %d, %Y")
                            print(f"📅 Parsed main page relative time to: {formatted_date}")
                            return formatted_date
        
        # Fallback to current date
        print(f"⚠️ No date found, using current date")
        return datetime.now().strftime("%B %d, %Y")
        
    except Exception as e:
        print(f"Error extracting Philstar date from {article_url}: {e}")
        return datetime.now().strftime("%B %d, %Y")

def parse_relative_time(time_text):
    """Parse relative time formats like '2 hours ago', '1 day ago', etc."""
    try:
        time_text = time_text.lower().strip()
        now = datetime.now()
        
        # Handle "X hours ago"
        hours_match = re.search(r'(\d+)\s*hours?\s*ago', time_text)
        if hours_match:
            hours = int(hours_match.group(1))
            return now - timedelta(hours=hours)
        
        # Handle "X hour ago" (singular)
        hour_match = re.search(r'(\d+)\s*hour\s*ago', time_text)
        if hour_match:
            hours = int(hour_match.group(1))
            return now - timedelta(hours=hours)
        
        # Handle "X minutes ago"
        minutes_match = re.search(r'(\d+)\s*minutes?\s*ago', time_text)
        if minutes_match:
            minutes = int(minutes_match.group(1))
            return now - timedelta(minutes=minutes)
        
        # Handle "X days ago"
        days_match = re.search(r'(\d+)\s*days?\s*ago', time_text)
        if days_match:
            days = int(days_match.group(1))
            return now - timedelta(days=days)
        
        # Handle "1 day ago" or "a day ago"
        if 'day ago' in time_text or '1 day ago' in time_text:
            return now - timedelta(days=1)
        
        # Handle "yesterday"
        if 'yesterday' in time_text:
            return now - timedelta(days=1)
        
        # Handle "today" 
        if 'today' in time_text:
            return now
        
        # Handle "X weeks ago"
        weeks_match = re.search(r'(\d+)\s*weeks?\s*ago', time_text)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return now - timedelta(weeks=weeks)
        
        return None
        
    except Exception as e:
        print(f"Error parsing relative time '{time_text}': {e}")
        return None

def is_article_from_target_dates(published_date):
    """Check if article is from today or yesterday (dynamic date filtering)"""
    if not published_date:
        return False
    
    try:
        # Dynamic target dates: today and yesterday
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        target_dates = [today.date(), yesterday.date()]
        
        print(f"🎯 Target dates: {[d.strftime('%B %d, %Y') for d in target_dates]}")
        print(f"📅 Checking article date: '{published_date}'")
        
        # Clean the date string first
        clean_date = published_date.strip()
        
        # Try to parse the article date string
        # Handle various date formats
        date_formats = [
            "%B %d, %Y",     # August 12, 2025
            "%b %d, %Y",     # Aug 12, 2025  
            "%Y-%m-%d",      # 2025-08-12
            "%m/%d/%Y",      # 08/12/2025
            "%d %B %Y",      # 12 August 2025
        ]
        
        parsed_date = None
        
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(clean_date, date_format).date()
                break
            except ValueError:
                continue
        
        # If standard parsing failed, try regex extraction
        if not parsed_date:
            # Look for month day, year pattern (more strict)
            date_match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', clean_date)
            if date_match:
                month_str, day_str, year_str = date_match.groups()
                
                # Only accept recent years to avoid old dates
                if int(year_str) < 2025:
                    print(f"📅 Skipping old article from {year_str}")
                    return False
                
                try:
                    parsed_date = datetime.strptime(f"{month_str} {day_str}, {year_str}", "%B %d, %Y").date()
                except ValueError:
                    try:
                        parsed_date = datetime.strptime(f"{month_str} {day_str}, {year_str}", "%b %d, %Y").date()
                    except ValueError:
                        pass
        
        if parsed_date:
            # Additional check: reject articles more than 7 days old
            days_diff = (today.date() - parsed_date).days
            if days_diff > 7:
                print(f"📅 Skipping old article from {clean_date} (more than 7 days old)")
                return False
            
            if parsed_date in target_dates:
                print(f"✅ Including Philstar article from {clean_date}")
                return True
            else:
                print(f"📅 Skipping Philstar article from {clean_date} (not {today.strftime('%b %d')} or {yesterday.strftime('%b %d')}, {today.year})")
                return False
        else:
            print(f"⚠️ Could not parse Philstar date: {published_date}")
            return False
            
    except Exception as e:
        print(f"Error checking Philstar date {published_date}: {e}")
        return False

def scrape_philstar_with_scroll():
    """Scrape Philstar business news with pagination/infinite scroll simulation"""
    # Multiple Philstar business sections to scrape
    base_urls = [
        "https://www.philstar.com/business",
        "https://www.philstar.com/business/technology",
        "https://www.philstar.com/business/real-estate",
        "https://www.philstar.com/business/telecoms"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    session = requests.Session()
    all_links = set()  # Use set to avoid duplicates
    all_articles = []
    
    print("📰 Scraping Philstar business news from multiple sections...")
    
    # Try to get articles from multiple base URLs and their pages
    pages_to_try = []
    for base_url in base_urls:
        pages_to_try.extend([
            base_url,
            f"{base_url}?page=2",
            f"{base_url}?page=3"
        ])
    
    for page_url in pages_to_try:
        try:
            print(f"  🔍 Fetching: {page_url}")
            response = session.get(page_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Updated selectors based on actual Philstar structure (from inspection)
            link_selectors = [
                'a[href*="/business/2025/08/"]',  # August 2025 business articles - most specific
                'a[href*="/business/2025/"]',     # Any 2025 business articles
                'h2 a[href*="/business/"]',       # Business article headlines in h2
                'h3 a[href*="/business/"]',       # Business article headlines in h3  
                'a[href*="/business/"][href*="/2025/"]',  # Any business link with 2025
                '.title a[href*="/business/"]',   # Title links to business
                '.headline a[href*="/business/"]', # Headline links to business
            ]
            
            page_links = set()
            for selector in link_selectors:
                links = soup.select(selector)
                if links:
                    print(f"    Found {len(links)} links with selector '{selector}'")
                    for link in links:
                        href = link.get('href', '')
                        if href and href not in all_links:
                            # Skip social media and external links immediately
                            if any(domain in href for domain in ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 'intent/tweet', 'dialog/feed']):
                                continue
                            
                            # Make absolute URL
                            if href.startswith('/'):
                                href = 'https://www.philstar.com' + href
                            elif not href.startswith('http'):
                                href = 'https://www.philstar.com/' + href
                            
                            # Filter for business articles and exclude social media
                            if (('/business/' in href and '/2025/08/' in href) and 
                                not any(domain in href for domain in ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 'intent/tweet', 'dialog/feed'])):
                                page_links.add(href)
                                all_links.add(href)
            
            # If we didn't get enough specific August links, try broader search
            if len(page_links) < 5:
                print(f"    Expanding search - only found {len(page_links)} August articles")
                broader_links = soup.select('a[href*="/business/2025/"]')
                for link in broader_links:
                    href = link.get('href', '')
                    if href and href not in all_links:
                        # Skip social media and external links immediately
                        if any(domain in href for domain in ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 'intent/tweet', 'dialog/feed']):
                            continue
                        
                        # Make absolute URL
                        if href.startswith('/'):
                            href = 'https://www.philstar.com' + href
                        elif not href.startswith('http'):
                            href = 'https://www.philstar.com/' + href
                        
                        # Filter for business articles 
                        if ('/business/' in href and '/2025/' in href and 
                            not any(domain in href for domain in ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 'intent/tweet', 'dialog/feed'])):
                            page_links.add(href)
                            all_links.add(href)
            
            print(f"    ✅ Found {len(page_links)} new business articles on this page")
            time.sleep(1)  # Be respectful to the server
            
        except Exception as e:
            print(f"    ❌ Error fetching {page_url}: {e}")
            continue
    
    print(f"📊 Total unique business article links found: {len(all_links)}")
    
    # Now process each article
    for i, link in enumerate(all_links, 1):
        try:
            if i > 100:  # Limit to first 100 articles to avoid being too aggressive
                print(f"    ⏹️ Stopping at {i-1} articles to be respectful")
                break
            
            print(f"  [{i}/{min(len(all_links), 100)}] Processing: {link}")
            
            # Skip social media and external links
            if any(domain in link for domain in ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com']):
                print(f"    ❌ Error processing {link}: Skipping social media link")
                continue
            
            # Only process actual Philstar business article URLs from our target sections
            valid_business_sections = [
                'https://www.philstar.com/business/',
                'https://www.philstar.com/business/technology/',
                'https://www.philstar.com/business/real-estate/',
                'https://www.philstar.com/business/telecoms/'
            ]
            
            is_valid_url = any(link.startswith(section) for section in valid_business_sections)
            if not is_valid_url:
                print(f"    ❌ Skipping non-business URL: {link}")
                continue
            
            # Get article page
            response = session.get(link, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract article info
            title_elem = soup.select_one('h1') or soup.select_one('.headline') or soup.select_one('.title') or soup.select_one('[class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            if not title or len(title) < 10:
                print(f"    ⚠️ Skipping - no valid title found")
                continue
            
            # Skip if it's a JavaScript error or generic message
            if any(phrase in title for phrase in ['JavaScript is not available', 'JavaScript is disabled', 'Error 404', 'Page not found']):
                print(f"    ❌ Skipping error page: {title}")
                continue
            
            # Extract description/summary  
            description = ""
            desc_selectors = [
                '.lead',
                '.summary', 
                '.excerpt',
                '.article-content p:first-of-type',
                '.content p:first-of-type',
                'meta[name="description"]',
                'meta[property="og:description"]',
                'p'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    if selector.startswith('meta'):
                        desc_text = desc_elem.get('content', '')
                    else:
                        desc_text = desc_elem.get_text(strip=True)
                    
                    if desc_text and len(desc_text) > 20:
                        description = desc_text[:200] + "..." if len(desc_text) > 200 else desc_text
                        break
            
            # Extract publication date
            published_date = extract_philstar_date(link, soup)
            
            # Apply date filtering
            if not is_article_from_target_dates(published_date):
                continue
            
            # Extract author
            author = ""
            author_selectors = ['.author', '.byline', '[rel="author"]', '.writer']
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = author_elem.get_text(strip=True)
                    break
            
            # Categorize and analyze sentiment
            category = categorize_news(title, description)
            sentiment_data = get_sentiment_analysis(title + " " + description)
            
            article_data = {
                "title": title,
                "category": category,
                "description": description or "No description available",
                "link": link,
                "author": author or "Philstar",
                "published_date": published_date,
                "sentiment_score": sentiment_data['sentiment_score'],
                "sentiment_label": sentiment_data['sentiment_label'],
                "emotion": sentiment_data['emotion'],
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Avoid duplicates
            if not any(item['title'] == title for item in all_articles):
                all_articles.append(article_data)
                print(f"    ✅ Added article: {title[:50]}...")
            
            time.sleep(0.5)  # Small delay between article requests
            
        except Exception as e:
            print(f"    ❌ Error processing {link}: {e}")
            continue
    
    return all_articles

def scrape_philstar_news():
    """Main function to scrape Philstar business news"""
    print("🔍 Starting Philstar Business News Scraping...")
    
    # Scrape articles with improved method
    news_data = scrape_philstar_with_scroll()
    
    if not news_data:
        print("⚠️ No articles found matching the criteria")
        return
    
    print(f"✅ Successfully scraped {len(news_data)} articles from Philstar Business")
    
    # Sample articles found
    print("Sample articles found:")
    for i, article in enumerate(news_data[:3], 1):
        print(f"  {i}. {article['title'][:60]}...")
    
    # Create DataFrame
    df = pd.DataFrame(news_data)
    
    # Save to Excel with table
    filename = "philstar_news.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Philstar News', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Philstar News']
        
        # Create a table
        from openpyxl.worksheet.table import Table, TableStyleInfo
        table = Table(displayName="NewsTable2", ref=worksheet.dimensions)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                             showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        worksheet.add_table(table)
    
    print(f"📊 Saved {len(df)} news items to {filename} (with table 'NewsTable2')")
    
    # Upload to Azure Blob Storage
    try:
        print(f"\n☁️ Uploading to Azure Blob Storage...")
        
        # Azure connection setup
        connection_string = os.getenv('AZURE_CONNECTION_STRING')
        container_name = os.getenv('AZURE_CONTAINER_NAME')
        blob_path = "Data/NSI/data/Azure Databricks/Automation Scripts/News/philstar_news.xlsx"
        
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
    
    print(f"✅ Complete! Philstar news file uploaded to Azure successfully.")

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
    scrape_philstar_news()
