# SEC 8-K Filing Scanner

Real-time SEC 8-K filing monitor for material corporate events. Tracks all 30+ 8-K item types, categorizes by impact level, and alerts on critical filings.

## What is an 8-K?

Form 8-K is the "current report" companies file with the SEC to announce major events that shareholders should know about. Unlike 10-K (annual) and 10-Q (quarterly) reports, 8-Ks are filed within 4 business days of the event.

## Why Track 8-Ks?

8-K filings often contain market-moving information:
- **Executive departures** (Item 5.02) - often precede bad news
- **Material agreements** (Item 1.01) - M&A, partnerships, contracts
- **Financial restatements** (Item 4.02) - non-reliance on prior financials (RED FLAG)
- **Auditor changes** (Item 4.01) - another red flag
- **Bankruptcy** (Item 1.03) - critical event
- **Change of control** (Item 5.01) - acquisition or takeover

## Features

- **Real-time monitoring** of SEC EDGAR for 8-K filings
- **Impact categorization** (CRITICAL, HIGH, MEDIUM, LOW)
- **30+ item types** tracked with descriptions
- **Smart alerts** for critical filings, after-hours, Friday night dumps
- **Ticker history** with filing statistics
- **Watchlist** for your portfolio holdings
- **After-hours detection** - filings outside market hours often signal problems
- **Friday night dump detection** - companies bury bad news on Friday evenings

## Installation

```bash
cd 8k-scanner
pip install -r requirements.txt  # No external deps needed for basic use
```

## Usage

### Show Recent Filings
```bash
python cli.py recent                     # Last 30 days of filings
python cli.py recent --days 7            # Last 7 days
python cli.py recent --impact HIGH       # Only high-impact filings
python cli.py recent --item 5.02         # Executive changes only
python cli.py recent --ticker AAPL       # AAPL filings only
```

### View Alerts
```bash
python cli.py alerts                     # All alerts
python cli.py alerts --priority 2        # P1-P2 (critical/high) only
```

### Ticker Analysis
```bash
python cli.py ticker AAPL                # AAPL filing history & stats
python cli.py ticker TSLA --verbose      # Detailed view
```

### Summary Statistics
```bash
python cli.py summary                    # Weekly filing summary
```

### Critical Filings Only
```bash
python cli.py critical                   # Bankruptcy, restatements, delistings
```

### Item Type Reference
```bash
python cli.py item --list                # List all 8-K item types
python cli.py item 5.02                  # Info about Item 5.02
```

### Watchlist Management
```bash
python cli.py watchlist                  # Show current watchlist
python cli.py watchlist --add AAPL       # Add ticker
python cli.py watchlist --add MSFT
python cli.py watchlist --scan           # Scan watchlist for filings
python cli.py watchlist --remove AAPL    # Remove ticker
```

### Refresh Data
```bash
python cli.py refresh                    # Force data refresh
```

### Run Tests
```bash
python cli.py test                       # Run test suite
```

## 8-K Item Types

### Critical Items (Immediate Attention)
| Item | Description |
|------|-------------|
| 1.03 | Bankruptcy or Receivership |
| 3.01 | Delisting/Transfer Notice |
| 4.02 | Non-Reliance on Financial Statements |
| 5.01 | Changes in Control |
| 5.04 | Trading Suspension |

### High-Impact Items
| Item | Description |
|------|-------------|
| 1.01 | Entry into Material Agreement |
| 1.02 | Termination of Material Agreement |
| 2.01 | Acquisition/Disposition of Assets |
| 2.02 | Results of Operations (Non-Reliance) |
| 2.04 | Triggering Events (Acceleration) |
| 2.06 | Material Impairments |
| 3.03 | Material Modification to Shareholder Rights |
| 4.01 | Auditor Changes |
| 5.02 | Executive Departure/Appointment |

### Medium-Impact Items
| Item | Description |
|------|-------------|
| 2.03 | Creation of Direct Financial Obligation |
| 2.05 | Costs for Exit/Disposal Activities |
| 3.02 | Unregistered Equity Sales |
| 5.03 | Amendments to Articles/Bylaws |
| 5.07 | Shareholder Vote Results |
| 7.01 | Regulation FD Disclosure |

### Other Items
| Item | Description |
|------|-------------|
| 5.05 | Amendment to Code of Ethics |
| 5.06 | Change in Shell Company Status |
| 5.08 | Shareholder Director Nominations |
| 8.01 | Other Events |
| 9.01 | Financial Statements and Exhibits |

## Alert Types

- **CRITICAL** - Bankruptcy, restatements, delisting (P1)
- **HIGH_IMPACT** - Material agreements, impairments, exec changes (P2)
- **AFTER_HOURS** - Material filings outside market hours (P2)
- **FRIDAY_DUMP** - Friday evening filings (used to bury bad news) (P3)
- **EXECUTIVE_CHANGE** - Leadership changes (P3)
- **AUDITOR_CHANGE** - Auditor switches (red flag) (P2)

## Trading Signals

### Bearish Signals
1. **Item 4.02** - Non-reliance on financials (accounting problems)
2. **Item 4.01** - Auditor change (especially mid-year)
3. **Friday night filings** - Companies hiding bad news
4. **Multiple Item 5.02s** - Executive exodus
5. **Item 2.06** - Material impairments (writedowns coming)

### Bullish Signals
1. **Item 1.01** - Material agreement (new contracts, partnerships)
2. **Item 2.01** - Strategic acquisition
3. **Item 5.02 + insider buying** - New CEO with skin in game

## Output Format

```
[!!] AAPL - Apple Inc. [AFTER HRS]
    Date: 2026-01-28 18:30:00
    Items: 5.02
    Impact: HIGH | Category: governance
    Summary: AAPL announced executive leadership change [AFTER HOURS]
```

Impact icons:
- `[!!!]` = CRITICAL
- `[!!]` = HIGH
- `[!]` = MEDIUM
- `[.]` = LOW

## Data Sources

Currently uses simulated data for testing. In production, integrates with:
- **SEC EDGAR** - Official SEC filing database
- **SEC RSS Feeds** - Real-time filing notifications
- **EDGAR Full-Text Search** - Historical filing search

## Integration

### As a Module
```python
from sec_8k_scanner import SEC8KScanner

scanner = SEC8KScanner()

# Get recent filings
filings = scanner.get_filings(ticker="AAPL", days=30)

# Get alerts
alerts = scanner.get_alerts(priority=2)

# Ticker history
history = scanner.get_ticker_history("TSLA")

# Summary stats
summary = scanner.get_summary()
```

### REST API (FastAPI)
```python
from fastapi import FastAPI
from sec_8k_scanner import SEC8KScanner

app = FastAPI()
scanner = SEC8KScanner()

@app.get("/filings")
def get_filings(ticker: str = None, days: int = 30):
    return scanner.get_filings(ticker=ticker, days=days)

@app.get("/alerts")
def get_alerts(priority: int = None):
    return scanner.get_alerts(priority=priority)
```

## Files

- `sec_8k_scanner.py` - Core scanner module
- `cli.py` - Command-line interface
- `README.md` - This file
- `.cache/` - Local cache directory (auto-created)
  - `8k_filings.json` - Cached filings
  - `8k_alerts.json` - Generated alerts
  - `8k_watchlist.json` - Your watchlist

## License

MIT
