# Philippine Business News Scrapers - Complete Azure Integration System

## **Project Overview**
Advanced automated web scraping system that extracts news from major Philippine business news sources, performs AI-powered sentiment analysis, intelligent categorization, and seamlessly uploads to Azure Blob Storage for data processing and analytics.

## **Supported News Sources**

### 1. **Inquirer Business** (`scrape_inquirer.py`)
- **Primary URL**: https://business.inquirer.net/
- **Additional Sources**: 
  - Property: https://business.inquirer.net/category/latest-stories/property
  - Industries: https://business.inquirer.net/category/latest-stories/industries  
  - Consumer Retail: https://business.inquirer.net/category/latest-stories/consumer-retail
  - Tourism & Transportation: https://business.inquirer.net/category/latest-stories/tourism-and-transportation
  - Economy: https://business.inquirer.net/category/latest-stories/economy
  - Communications: https://business.inquirer.net/category/latest-stories/communications
  - Movements: https://business.inquirer.net/category/latest-stories/movements
- **Output**: `inquirer_news.xlsx`
- **Coverage**: Comprehensive business coverage across 9 specialized sections

### 2. **Philstar Business** (`scrape_philstar_improved.py`)
- **Primary URL**: https://www.philstar.com/business
- **Additional Sources**:
  - Technology: https://www.philstar.com/business/technology
  - Real Estate: https://www.philstar.com/business/real-estate
  - Telecoms: https://www.philstar.com/business/telecoms
- **Output**: `philstar_news.xlsx`
- **Coverage**: Multi-section business news with specialized industry focus

### 3. **Business Mirror** (`scrape_businessmirror_fixed.py`)
- **Targeted URLs**: 
  - General Business: https://businessmirror.com.ph/business/
  - Companies: https://businessmirror.com.ph/business/companies/
  - Economy: https://businessmirror.com.ph/news/economy/
  - Export Trade: https://businessmirror.com.ph/business/export-unlimited/
- **Output**: `businessmirror_news.xlsx`
- **Coverage**: Focused business and economic coverage from 4 key sections

### 4. **Universal Orchestrator** (`universal_news_scraper.py`)
- **Function**: Coordinates all three scrapers in sequence
- **Error Handling**: Robust individual scraper management
- **Reporting**: Comprehensive execution summary and statistics


### **Intelligent Web Scraping**
- **Smart Date Filtering**: Dynamic filtering for today's and yesterday's articles only
- **Anti-Detection**: Advanced user-agent headers and request throttling
- **Multi-Selector Support**: Adaptive CSS selectors for different site structures
- **URL Validation**: Intelligent filtering and absolute URL conversion
- **Duplicate Prevention**: Cross-source duplicate detection and removal

### **AI-Powered Content Analysis**
- **Hybrid Sentiment Analysis**: Combined TextBlob + VADER scoring system
- **Smart Categorization**: 14+ business categories with keyword-based classification
- **Emotion Detection**: 5-level emotion classification (Optimistic, Positive, Neutral, Negative, Concerning)
- **Content Quality**: Automatic filtering of low-quality and irrelevant content

### **Azure Cloud Integration**
- **Storage**: Azure Blob Storage with organized folder structure
- **Container**: `nsi-and-sales-forecasting`
- **Path**: `Data/NSI/data/Azure Databricks/Automation Scripts/News/`
- **Format**: Excel (.xlsx) with structured tables and automatic timestamps
- **Reliability**: Automatic retry logic and connection validation

### **Data Processing & Export**
- **Excel Tables**: Structured data with professional table formatting
- **Timestamp Tracking**: Scraping time and article publication dates
- **Statistical Analysis**: Automatic sentiment distribution and category summaries
- **Data Validation**: Content quality checks and data integrity verification

##  **Business Categories**
1. **Banking & Finance** - Financial institutions, monetary policy, investments
2. **Stock Market** - PSEi, trading, equity analysis, market movements
3. **Energy & Utilities** - Power, fuel, utilities, renewable energy
4. **Real Estate** - Property development, construction, housing
5. **Technology** - Digital innovation, tech companies, AI, platforms
6. **Infrastructure** - Transportation, ports, roads, public works
7. **Retail & Consumer** - Shopping, consumer goods, retail chains
8. **Manufacturing** - Industrial production, factories, exports
9. **Agriculture** - Farming, food production, agricultural policy
10. **Government & Policy** - Regulations, government initiatives, policy changes
11. **International Trade** - Import/export, foreign trade, tariffs
12. **Economic Indicators** - GDP, inflation, economic growth metrics
13. **Companies** - Corporate news, earnings, business developments
14. **Health & Medical** - Healthcare, pharmaceuticals, medical industry

## **Usage Instructions**

### Prerequisites
```bash
pip install -r requirements.txt
```

### Environment Configuration (.env)
```env
AZURE_CONNECTION_STRING=your_azure_blob_connection_string
AZURE_CONTAINER_NAME=xxxx
```

### Individual Scrapers
```bash
# Run Inquirer scraper (9 sources)
python scrape_inquirer.py

# Run Philstar scraper (4 sources) 
python scrape_philstar_improved.py

# Run Business Mirror scraper (4 sources)
python scrape_businessmirror_fixed.py
```

### Universal Execution
```bash
# Run all scrapers in sequence
python universal_news_scraper.py
```

## �️ **File Structure**
```
📁 ASSIGNMENT/
├── 📄 scrape_inquirer.py          # Inquirer multi-source scraper
├── 📄 scrape_philstar_improved.py # Philstar business sections scraper  
├── 📄 scrape_businessmirror_fixed.py # Business Mirror focused scraper
├── 📄 universal_news_scraper.py   # Universal orchestrator
├── 📄 requirements.txt            # Python dependencies
├── 📄 .env                       # Azure configuration
├── 📄 README.md                  # This documentation
└── 📊 Output Files:
    ├── inquirer_news.xlsx         # Inquirer articles
    ├── philstar_news.xlsx         # Philstar articles  
    └── businessmirror_news.xlsx   # Business Mirror articles
```

## **Dependencies**
```
requests>=2.31.0
beautifulsoup4>=4.12.0  
pandas>=2.0.0
openpyxl>=3.1.0
textblob>=0.17.0
vaderSentiment>=3.3.0
python-dotenv>=1.0.0
azure-storage-blob>=12.19.0
```

## **System Requirements**
- **Python**: 3.8+ 
- **Memory**: 512MB+ available RAM
- **Network**: Stable internet connection for web scraping and Azure uploads
- **Storage**: ~50MB for temporary files and outputs
- **Azure**: Valid Blob Storage account with connection string

## **Success Indicators**
- ✅ **Multi-source Coverage**: 17 different news sources across 3 major publications
- ✅ **Intelligent Filtering**: Date-based filtering (today + yesterday only)
- ✅ **AI Analysis**: Hybrid sentiment analysis with emotion detection
- ✅ **Cloud Integration**: Seamless Azure Blob Storage uploads  
- ✅ **Error Resilience**: Robust error handling and recovery
- ✅ **Data Quality**: Professional Excel formatting with tables
- ✅ **Scalability**: Modular design for easy source expansion
- ✅ **Performance**: Fast, efficient processing with respectful request timing

## **Data Output Format**
Each Excel file contains the following columns:
- **title**: Article headline
- **category**: AI-classified business category  
- **description**: Article summary/excerpt
- **link**: Full article URL
- **author**: Article author (when available)
- **published_date**: Publication date
- **sentiment_score**: Numerical sentiment score (-1 to +1)
- **sentiment_label**: Positive/Neutral/Negative classification
- **emotion**: Detailed emotion classification
- **scraped_at**: Processing timestamp

## 🔄 **Automation Ready**
The system is designed for automated execution via:
- **Windows Task Scheduler** for periodic runs
- **Azure Functions** for cloud-based scheduling
- **GitHub Actions** for CI/CD integration
- **Local Cron Jobs** for Linux environments
