"""
Configuration for Insider Trading (Form 4) Monitor
"""

# SEC EDGAR API settings
SEC_EDGAR_BASE_URL = "https://data.sec.gov"
SEC_EDGAR_FILINGS_URL = f"{SEC_EDGAR_BASE_URL}/submissions"
# Use the SEC EDGAR full-text search API for recent Form 4s
SEC_FORM4_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22form%204%22&dateRange=custom&startdt=2024-01-01&enddt=2026-12-31&forms=4"
SEC_RECENT_FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=include&count=100&output=atom"

# Required headers for SEC EDGAR API (don't set Host - let requests handle it)
SEC_HEADERS = {
    "User-Agent": "InsiderTracker research@example.com",
    "Accept-Encoding": "gzip, deflate"
}

# C-Suite titles to flag for large purchase alerts
CSUITE_TITLES = [
    "CEO", "Chief Executive Officer",
    "CFO", "Chief Financial Officer",
    "COO", "Chief Operating Officer",
    "CTO", "Chief Technology Officer",
    "CIO", "Chief Information Officer",
    "CMO", "Chief Marketing Officer",
    "President", "Chairman", "Vice Chairman",
    "Director", "Board Member"
]

# Alert thresholds
CSUITE_PURCHASE_ALERT_THRESHOLD = 100000  # $100k
CLUSTER_BUYING_WINDOW_DAYS = 7  # Same week = 7 days
CLUSTER_BUYING_MIN_INSIDERS = 2  # At least 2 insiders buying

# Sentiment score weights
SENTIMENT_WEIGHTS = {
    "purchase": 1.0,
    "sale": -0.5,  # Sales less negative (could be tax/diversification)
    "csuite_purchase": 2.0,  # C-suite buying is stronger signal
    "csuite_sale": -0.3,  # C-suite selling less concerning
    "cluster_buying": 1.5,  # Cluster buying bonus
    "large_purchase": 1.2,  # >$100k bonus
}

# Cache settings
CACHE_DIR = "cache"
CACHE_EXPIRY_HOURS = 1  # Refresh filings every hour

# Output settings
OUTPUT_DIR = "output"
