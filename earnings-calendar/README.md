# 📅 Earnings Calendar Dashboard

Interactive earnings calendar showing when companies report, with historical beat/miss rates.

## Features

- **Calendar View** - Month/week/list view toggle using FullCalendar.js
- **Filters** - Filter by sector, time (BMO/AMC), ticker search, and watchlist
- **Click to View** - Click any date to see all companies reporting
- **Detailed Modal** - View historical earnings performance (last 8 quarters)
- **Beat/Miss Rates** - Color-coded indicators for high (>70%) and low (<50%) beat rates
- **Pre/Post Market** - BMO (purple) and AMC (blue) time indicators
- **Pre-Earnings Checklist** - Reminder list for earnings prep
- **Mobile Responsive** - Works on all screen sizes

## Data

### earnings_calendar.json

Cached earnings data with structure:
```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "date": "2026-01-31",
  "time": "AMC",
  "expectedEPS": 2.42,
  "beatRate": 88,
  "history": [
    {
      "date": "2025-10-31",
      "estimate": 1.60,
      "actual": 1.64,
      "result": "BEAT",
      "priceMove": -1.8
    }
  ]
}
```

### earnings_data_fetcher.py

Python script to fetch fresh data from Yahoo Finance:

```bash
# Install yfinance if needed
pip install yfinance

# Run the fetcher
python earnings_data_fetcher.py
```

The script:
- Fetches earnings dates for 60+ major companies
- Calculates historical beat rates
- Caches data for 6 hours
- Outputs to `earnings_calendar.json`

## Sectors Covered

- Technology (AAPL, MSFT, NVDA, AMD, etc.)
- Financials (JPM, GS, BAC, MS, etc.)
- Healthcare (JNJ, UNH, PFE, LLY, etc.)
- Consumer (AMZN, WMT, HD, COST, etc.)
- Communication (GOOGL, META, NFLX, DIS, etc.)
- Industrials (CAT, BA, HON, UPS, etc.)
- Energy (XOM, CVX, COP, SLB)
- Materials (LIN, APD, FCX)
- Utilities (NEE, DUK, SO)
- Real Estate (AMT, PLD, EQIX)

## Watchlist

The default watchlist is stored in localStorage and includes major tech/financial names:
- AAPL, MSFT, NVDA, GOOGL, META, AMZN, JPM, BAC, GS

Toggle "My Watchlist Only" to filter to just these stocks.

## Tech Stack

- **FullCalendar.js** - Calendar component
- **Vanilla JavaScript** - No framework dependencies
- **CSS Variables** - Dark theme matching Guide Bot
- **LocalStorage** - Watchlist persistence
- **yfinance** - Python library for Yahoo Finance data

## Usage

1. Open `index.html` in a browser
2. Use filters to narrow down earnings
3. Click dates to see who's reporting
4. Click individual stocks for detailed history
5. Run `python earnings_data_fetcher.py` to refresh data

## Integration

Added to Guide Bot main navigation:
- Desktop nav: "📅 Earnings" link
- Mobile menu: "📅 Earnings Calendar" link
