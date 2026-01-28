"""
Configuration for 13F Holdings Change Tracker
Superinvestor CIK numbers and tracking settings
"""

# Major hedge funds/superinvestors to track
# CIK numbers from SEC EDGAR
SUPERINVESTORS = {
    "Berkshire Hathaway": "0001067983",
    "Appaloosa Management": "0001656456",
    "Baupost Group": "0001061768",
    "Pershing Square": "0001336528",
    "Bridgewater Associates": "0001350694",
    "Renaissance Technologies": "0001037389",
    "Two Sigma": "0001179392",
    "Citadel Advisors": "0001423053",
    "Point72": "0001603466",
    "Tiger Global": "0001167483",
    "Third Point": "0001040273",
    "Greenlight Capital": "0001079114",
    "Soros Fund Management": "0001029160",
    "Icahn Enterprises": "0000810958",
    "ValueAct Capital": "0001345471",
    "Elliott Management": "0001048445",
    "Lone Pine Capital": "0001061165",
    "Viking Global": "0001103804",
    "Coatue Management": "0001535392",
    "D.E. Shaw": "0001009207",
}

# Change detection thresholds
CHANGE_THRESHOLDS = {
    "significant_change_pct": 20,  # Flag changes >= 20%
    "new_position_flag": True,
    "exit_position_flag": True,
}

# SEC EDGAR API settings
SEC_EDGAR_BASE_URL = "https://data.sec.gov"
SEC_EDGAR_FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

# Required User-Agent for SEC EDGAR API
USER_AGENT = "13F-Tracker research@example.com"

# Output settings
OUTPUT_DIR = "output"
CACHE_DIR = "cache"
