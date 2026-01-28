# Short Interest Tracker

Real-time short interest monitoring dashboard for L/S equity analysts.

## Features

- **SI % of Float** - Visual bar + percentage for each holding
- **Days to Cover** - Shares short / avg daily volume
- **WoW Change** - Week-over-week SI change tracking
- **Threshold List** - Flags stocks on exchange threshold lists
- **Squeeze Score** - Proprietary algorithm (0-100) combining SI%, DTC, and trends
- **Alerts** - Automatic alerts for:
  - SI jumps >20% week-over-week
  - Days to cover >5
  - High SI (>20% of float)
  - Threshold list entries

## Quick Start

1. **View Dashboard**: Open `index.html` in browser
2. **Update Data**: Run `python short_interest_fetcher.py`

## Files

| File | Description |
|------|-------------|
| `index.html` | Main dashboard UI |
| `short_interest_fetcher.py` | Python data fetcher (Yahoo Finance) |
| `short_interest.json` | Cached data (auto-generated) |

## Data Fetcher Usage

```bash
# Fetch default watchlist (20 stocks)
python short_interest_fetcher.py

# Fetch specific tickers
python short_interest_fetcher.py AAPL TSLA NVDA

# Add to cron for daily updates
0 6 * * * cd /path/to/short-interest && python short_interest_fetcher.py
```

## Squeeze Score Algorithm

The squeeze potential score (0-100) is calculated as:

| Factor | Score |
|--------|-------|
| SI >= 30% | +40 |
| SI 20-30% | +30 |
| SI 15-20% | +20 |
| SI 10-15% | +10 |
| DTC >= 7 days | +30 |
| DTC 5-7 days | +20 |
| DTC 3-5 days | +10 |
| SI change >= 5% WoW | +20 |
| SI change 2-5% WoW | +10 |
| On threshold list | +10 |

**Score Interpretation:**
- **70+**: High squeeze potential 🔥
- **50-70**: Moderate squeeze potential
- **<50**: Low squeeze potential

## Alert Triggers

| Alert | Trigger |
|-------|---------|
| 🚀 Squeeze | Score >= 60 |
| ⚠️ High SI | SI >= 20% of float |
| 📋 Threshold | On exchange threshold list |
| 📈 Increasing | SI change >= 5% WoW |

## Data Sources

- **Short Interest**: Yahoo Finance API (via yfinance)
- **Threshold List**: Manually maintained (FINRA/NYSE/NASDAQ)

## Adding Tickers

1. Edit `DEFAULT_WATCHLIST` in `short_interest_fetcher.py`
2. Or use the "Add Ticker" button in UI
3. Re-run the fetcher

## Tech Stack

- HTML5 + CSS3 (dark theme)
- Chart.js (distribution donut chart)
- Vanilla JavaScript (no framework)
- Python 3.8+ (data fetcher)
- yfinance library

## Integration

This dashboard integrates with the Guide Bot research suite:
- Earnings Calendar (`/earnings-calendar/`)
- Estimate Monitor (`/long-short-bot/estimate_monitor.py`)
- 13F Holdings Tracker (coming soon)

---

Built by PM2 🎨 | Guide Bot Research Suite
