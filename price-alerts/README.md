# Price Alert System

Multi-asset price alerts with complex conditions. Monitor stocks, crypto, forex, and commodities with customizable thresholds.

## Features

- **Multi-Asset Support**: Stocks, crypto, forex, commodities
- **Flexible Conditions**: Price thresholds, percent changes, volume spikes
- **Repeating Alerts**: Trigger multiple times or once
- **Alert Expiry**: Auto-expire alerts after set time
- **Trigger History**: Track all triggered alerts
- **Watchlist View**: Quick quotes for watched symbols

## Installation

```bash
# No external dependencies - uses Python standard library
python price_alerts.py --help
```

## Usage

### Get Quotes
```bash
# Stock quote
python price_alerts.py quote AAPL
python price_alerts.py quote NVDA

# Crypto quote
python price_alerts.py quote BTC
python price_alerts.py quote ETH

# Forex quote
python price_alerts.py quote EUR/USD

# JSON output
python price_alerts.py quote AAPL --json
```

### Create Alerts
```bash
# Price threshold alerts
python price_alerts.py set AAPL price_above 200
python price_alerts.py set TSLA price_below 200

# Percent change alerts
python price_alerts.py set NVDA pct_change_down 10  # 10% drop
python price_alerts.py set BTC pct_change_up 20     # 20% gain

# Volume spike alerts
python price_alerts.py set MSFT volume_spike 2      # 2x average volume

# With options
python price_alerts.py set AAPL price_above 200 -n "Earnings play" -r -e 24
#   -n, --note      Add a note
#   -r, --repeat    Alert can trigger multiple times
#   -e, --expires   Expire after N hours
```

### Manage Alerts
```bash
# List all alerts
python price_alerts.py list

# List only active alerts
python price_alerts.py list --active

# Filter by symbol
python price_alerts.py list -s AAPL

# Delete an alert
python price_alerts.py delete abc123
```

### Check Alerts
```bash
# Check all alerts and trigger matching ones
python price_alerts.py check

# JSON output (for webhooks)
python price_alerts.py check --json
```

### View History
```bash
# Recent trigger history
python price_alerts.py history

# Filter by symbol
python price_alerts.py history -s NVDA

# Limit results
python price_alerts.py history -l 50
```

### Watchlist
```bash
# View all watched symbols with current prices
python price_alerts.py watchlist
```

## Alert Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `price_above` | Price exceeds threshold | AAPL > $200 |
| `price_below` | Price drops below threshold | TSLA < $200 |
| `pct_change_up` | % gain from alert creation | +10% from $150 |
| `pct_change_down` | % drop from alert creation | -10% from $150 |
| `volume_spike` | Volume exceeds X times average | 2x avg volume |
| `moving_avg_cross` | Price crosses above threshold | Cross above $180 |

## Supported Assets

**Stocks**: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, JPM, BAC, XOM

**Crypto**: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, LINK

**Forex**: EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD

**Commodities**: GOLD, SILVER, OIL, NATGAS, COPPER

## Output Examples

### Quote
```
📊 NVDA (STOCK)
   Price: $892.45
   📈 Change: +15.32 (+1.75%)
   24h Range: $874.20 - $910.10
   Volume: 42.3M (1.4x avg)
```

### Triggered Alert
```
🚨 TRIGGERED ALERTS (1)

🔔 NVDA [a1b2c3d4]
   Price $892.45 crossed above $850.00
   Current: $892.45 (+1.75%)
   Note: Breakout watch
```

## Data Storage

Alerts and history stored in `./data/alerts.json`:
- Active, triggered, and expired alerts
- Last 1000 trigger events in history

## Integration Ideas

- **Cron Job**: Run `check --json` every minute
- **Webhook**: Pipe output to Discord/Slack/Telegram
- **Dashboard**: Feed watchlist data to web UI
- **Trading Bot**: Trigger orders on alert conditions

## Built By

PM3 - Backend/CLI Pipeline  
Part of the Guidebot Pipeline

---

*Note: Currently uses simulated price data. In production, integrate with Yahoo Finance, Alpha Vantage, or exchange APIs.*
