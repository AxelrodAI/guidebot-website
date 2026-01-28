# Dividend Calendar & Yield Tracker

A comprehensive dividend monitoring dashboard with ex-date calendar, yield tracking, sustainability scoring, and dividend growth analysis.

## Features

### 📅 Calendar View
- Interactive calendar showing ex-dividend dates
- Color-coded by yield (green = high, blue = medium, gray = low)
- Red indicators for at-risk dividends
- Click events to see stock details

### 📊 Table View
- Full data table with all dividend metrics
- Sortable columns
- Payout ratio and sustainability scores
- Quick export to CSV

### 📈 Analytics View
- Portfolio average yield vs S&P 500
- Estimated annual income calculation
- Sector yield comparison chart
- Overall dividend safety score

### 🔍 Filters
- Search by ticker
- Filter by sector
- Yield range (high/medium/low)
- Sustainability (safe/moderate/risky)
- Growth status (aristocrats/growing/stable/declining)

### 📋 Sidebars
- **Top Yields**: Highest yielding stocks
- **Aristocrats**: 25+ years of dividend growth
- **Upcoming Ex-Dates**: Next 30 days
- **Cut Risk Watch**: Stocks with low sustainability scores
- **Recent Increases**: Strong dividend growers

## Metrics Explained

### Dividend Yield
Annual dividend divided by current stock price. Higher isn't always better - check sustainability!

### DGR (5Y)
Dividend Growth Rate over the past 5 years. Measures how fast the dividend is growing.

### Payout Ratio
Percentage of earnings paid out as dividends. Below 60% is generally sustainable.

### Years of Growth
Consecutive years of dividend increases:
- **King** (50+ years): Exceptional track record
- **Aristocrat** (25+ years): Elite dividend payer
- **Achiever** (10+ years): Proven grower

### Sustainability Score (0-100)
Proprietary score based on:
- Payout ratio (lower = better)
- Dividend growth rate
- Consecutive years of growth
- Debt levels

**Score Guide:**
- 70+: Safe - Low risk of cut
- 50-70: Moderate - Monitor closely
- <50: At-Risk - High probability of cut or freeze

## Installation

```bash
# Install dependencies
pip install yfinance

# Optional for Excel export
pip install pandas openpyxl
```

## Usage

### Fetch Data

```bash
# Fetch default 45 dividend stocks
python dividend_fetcher.py

# Fetch specific tickers
python dividend_fetcher.py --tickers AAPL MSFT JNJ O

# Use custom watchlist
echo "AAPL
MSFT
JNJ" > watchlist.txt
python dividend_fetcher.py --watchlist

# Export to Excel
python dividend_fetcher.py --excel
```

### View Dashboard

Open `index.html` in a browser, or serve via:

```bash
# Python 3
python -m http.server 8080

# Then visit http://localhost:8080/dividend-calendar/
```

## Data Sources

- **Price/Yield Data**: Yahoo Finance via yfinance
- **Dividend History**: Yahoo Finance historical dividends
- **Payout Ratio**: Yahoo Finance company info
- **Dividend Streaks**: Curated from public sources

## Automation

Set up a cron job or scheduled task to refresh data daily:

```bash
# Linux/Mac cron (9 AM daily)
0 9 * * * cd /path/to/dividend-calendar && python dividend_fetcher.py

# Windows Task Scheduler
schtasks /create /tn "DividendFetcher" /tr "python C:\path\to\dividend_fetcher.py" /sc daily /st 09:00
```

## Files

```
dividend-calendar/
├── index.html              # Main dashboard
├── dividend_fetcher.py     # Data fetcher script
├── dividend_data.json      # Cached dividend data
├── watchlist.txt           # Optional custom ticker list
└── README.md               # This file
```

## Screenshots

### Calendar View
Shows ex-dividend dates with yield-based coloring.

### Table View
Full data table with all metrics and export functionality.

### Stock Detail Modal
8-quarter dividend history chart and all key metrics.

## Related Tools

- **Earnings Calendar**: See when companies report
- **13F Tracker**: Track hedge fund holdings
- **Short Interest**: Monitor squeeze candidates
- **Insider Trading**: Form 4 filing alerts

---

Built by PM2 🎨 | Part of the Guide Bot Research Suite
