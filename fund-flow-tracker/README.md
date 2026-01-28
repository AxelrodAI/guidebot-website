# Fund Flow Tracker

Track ETF and Mutual Fund flows to identify market sentiment, positioning shifts, and sector rotation signals.

## Features

- **Real-time Flow Tracking**: Monitor daily inflows/outflows for 30+ major ETFs
- **Category Analysis**: Aggregate flows by asset class and sector  
- **Rotation Signals**: Identify risk-on/risk-off shifts from flow patterns
- **Significant Flow Scanner**: Detect unusual flow activity
- **Alert System**: Set threshold alerts for specific ETFs
- **Flow Streaks**: Track consecutive inflow/outflow days

## Installation

```bash
# No external dependencies required - uses Python standard library
python fund_flow_tracker.py --help
```

## Usage

### Get ETF Flows
```bash
# Get 30-day flows for SPY
python fund_flow_tracker.py flows SPY

# Get 60-day flows for QQQ
python fund_flow_tracker.py flows QQQ -d 60

# Force refresh (bypass cache)
python fund_flow_tracker.py flows SPY -r

# JSON output
python fund_flow_tracker.py flows SPY --json
```

### Category Analysis
```bash
# View flows by category
python fund_flow_tracker.py categories

# 60-day category flows
python fund_flow_tracker.py categories -d 60
```

### Sector Rotation Signals
```bash
# Get rotation signals
python fund_flow_tracker.py rotation

# Identifies:
# - RISK-ON: Money flowing to growth/risk assets
# - RISK-OFF: Money flowing to safe havens
# - MIXED: No clear preference
```

### Scan for Significant Flows
```bash
# Find flows > 1% of AUM (default)
python fund_flow_tracker.py scan

# Find flows > 1.5% of AUM
python fund_flow_tracker.py scan -t 1.5

# Scan last 14 days
python fund_flow_tracker.py scan -d 14
```

### Alerts
```bash
# Alert when SPY sees $500M+ flow (either direction)
python fund_flow_tracker.py alert SPY 500

# Alert on QQQ inflows only
python fund_flow_tracker.py alert QQQ 300 -dir inflow

# Alert on TLT outflows only
python fund_flow_tracker.py alert TLT 200 -dir outflow

# Check triggered alerts
python fund_flow_tracker.py check-alerts
```

### List Tracked ETFs
```bash
# List all tracked ETFs
python fund_flow_tracker.py list

# Filter by category
python fund_flow_tracker.py list -c tech
python fund_flow_tracker.py list -c treasury
```

## Tracked Universe

**Equity - US**
- SPY, QQQ, IWM, DIA, VTI

**Equity - International**  
- EFA, EEM, VWO, FXI

**Fixed Income**
- TLT, IEF, SHY, LQD, HYG, AGG

**Sectors**
- XLF, XLE, XLK, XLV, XLI, XLU, XLRE

**Commodities**
- GLD, SLV, USO

**Thematic/Factor**
- ARKK, MTUM, USMV, VIG

## Output Example

```
📊 SPY - SPDR S&P 500 ETF
   Category: US Large Cap
   Current AUM: $502.3B

Date       │ Flow ($M)   │ Flow %  │ AUM ($B)
───────────┼─────────────┼─────────┼──────────
2025-01-20 │      +1,234 │  +0.25% │    501.2
2025-01-21 │        -567 │  -0.11% │    500.6
2025-01-22 │      +2,891 │  +0.58% │    503.5

Summary (30 days):
  📈 Total Flow: +$5,432M (INFLOW)
  📅 Positive Days: 18 | Negative: 12
  🔥 Current Streak: 3 days INFLOW
```

## Rotation Signal Interpretation

| Signal | Meaning | Typical Conditions |
|--------|---------|-------------------|
| RISK-ON | Investors seeking growth | Bull market, low VIX, strong earnings |
| RISK-OFF | Flight to safety | Market stress, rising VIX, uncertainty |
| MIXED | No clear preference | Transitional periods, sector rotation |

## Data Storage

Flow data is cached in `./data/` directory:
- `{TICKER}_flows.json` - Cached flow data (1-hour TTL)
- `alerts.json` - Active alert configurations

## Integration Ideas

- **Daily Digest**: Run `rotation` command in morning cron job
- **Alert Webhook**: Pipe `check-alerts --json` to notification service
- **Dashboard Feed**: Use `--json` output for web dashboard
- **Research Workflow**: Combine with SEC 13F data for institutional tracking

## Built By

PM3 - Backend/CLI Pipeline  
Part of the Guidebot Pipeline

---

*Note: Currently uses simulated data. In production, integrate with ETF.com, Bloomberg, or similar data providers.*
