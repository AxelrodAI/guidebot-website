# Financial News Alert Digests

Aggregate watchlist news and summarize material events for investors.

## Features

- **Watchlist Management**: Track multiple tickers
- **Material Event Detection**: Earnings, M&A, FDA, Legal, Management changes
- **Priority Scoring**: 1-5 scale based on event materiality
- **News Aggregation**: Fetch and cache news from multiple sources
- **Daily Digests**: Summarized overviews of watchlist activity
- **Alert System**: Real-time alerts for high-priority events
- **Category Filtering**: View news by event type

## Quick Start

```bash
# Add tickers to watchlist
python news_digests.py watchlist add AAPL --name "Apple Inc"
python news_digests.py watchlist add TSLA --name "Tesla Inc"
python news_digests.py watchlist add NVDA --name "NVIDIA Corp"

# Fetch news for all watched tickers
python news_digests.py fetch --days 7

# View recent news
python news_digests.py news --days 3

# Generate daily digest
python news_digests.py digest --days 1

# Check for alerts
python news_digests.py alerts --check
```

## Commands

### watchlist
Manage your watchlist of tickers.
```bash
python news_digests.py watchlist add AAPL --name "Apple Inc" --notes "Core holding"
python news_digests.py watchlist remove AAPL
python news_digests.py watchlist list --json
```

### fetch
Fetch latest news for all watchlist tickers.
```bash
python news_digests.py fetch --days 7
```

### news
View cached news with filters.
```bash
python news_digests.py news --ticker AAPL --days 3
python news_digests.py news --category earnings
python news_digests.py news --min-priority 4 --limit 10
python news_digests.py news --json
```

### digest
Generate a summary digest.
```bash
python news_digests.py digest --days 1
python news_digests.py digest --days 7 --json
```

### alerts
Check for and view alerts.
```bash
python news_digests.py alerts --check    # Check for new alerts
python news_digests.py alerts --days 3   # View recent alerts
```

### categories
List available event categories.
```bash
python news_digests.py categories
```

### config
View or update configuration.
```bash
python news_digests.py config
python news_digests.py config --key min_priority_for_alert --value 4
```

### stats
View statistics.
```bash
python news_digests.py stats
```

## Event Categories

| Category | Icon | Priority | Description |
|----------|------|----------|-------------|
| earnings | [EARN] | 5 | Quarterly/annual results |
| merger | [M&A] | 5 | M&A activity |
| fda | [FDA] | 5 | Drug approvals, trials |
| legal | [LEGAL] | 4 | Lawsuits, investigations |
| management | [MGMT] | 4 | Executive changes |
| guidance | [GUIDE] | 4 | Forward guidance |
| dividend | [DIV] | 3 | Dividend announcements |
| buyback | [BUY] | 3 | Share repurchases |
| analyst | [ANLY] | 3 | Upgrades/downgrades |
| filing | [FILE] | 3 | SEC filings |
| product | [PROD] | 2 | Product launches |

## Priority Levels

- **5 (Critical)**: Earnings, M&A, FDA approvals - immediate attention
- **4 (High)**: Legal issues, management changes, guidance updates
- **3 (Medium)**: Analyst actions, dividends, buybacks
- **2 (Low)**: Product news, minor updates
- **1 (Info)**: General news

## Configuration Options

| Key | Description | Default |
|-----|-------------|---------|
| `alert_on_high_priority` | Enable alerts | true |
| `digest_frequency` | daily/weekly | "daily" |
| `news_retention_days` | Days to keep cached news | 30 |
| `min_priority_for_alert` | Min priority for alerts | 4 |
| `categories_enabled` | Active categories | all |

## Integration Points

### News APIs
Replace the simulated `fetch_news_for_ticker()` function with real API calls:
- **NewsAPI.org**: General news
- **Alpha Vantage**: Market news
- **Polygon.io**: Ticker-specific news
- **Benzinga**: Financial news
- **SEC EDGAR**: Filing alerts

### Notification Integration
Alerts can be routed to:
- Email
- Slack/Discord
- Push notifications
- SMS

### Scheduler Integration
```bash
# Example cron for morning digest
0 7 * * * cd /path/to/news-digests && python news_digests.py digest --days 1

# Hourly alert check
0 * * * * cd /path/to/news-digests && python news_digests.py alerts --check
```

## Data Files

- `data/watchlist.json` - Tracked tickers
- `data/news_cache.json` - Cached articles
- `data/alerts.json` - Alert history
- `data/digests.json` - Generated digests
- `data/config.json` - Configuration

---
Built by PM3 (Backend/Data Builder) | Financial News Alert Digests v1.0
