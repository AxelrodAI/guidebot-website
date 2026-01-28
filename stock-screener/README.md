# Stock Screener

Build custom stock screens with flexible filters and AND/OR logic.

## Features

- **Custom Filters** - Choose from 15+ metrics
- **AND/OR Logic** - Combine filters flexibly
- **Quick Templates** - Pre-built screens for common strategies
- **Save Screens** - Store your favorite screens locally
- **Scoring** - See how well each stock matches your criteria
- **CSV Export** - Export results for further analysis

## Quick Start

1. Open `index.html` in browser
2. Use a **Quick Template** or **Add Filters** manually
3. Click **Run Screen** to find matching stocks
4. **Save** your screen for future use

## Available Filters

### Valuation
| Filter | Description |
|--------|-------------|
| P/E Ratio | Price to Earnings |
| Forward P/E | Forward Price to Earnings |

### Growth
| Filter | Description |
|--------|-------------|
| Revenue Growth % | YoY revenue growth |
| EPS Growth % | YoY earnings growth |

### Profitability
| Filter | Description |
|--------|-------------|
| Net Margin % | Net Income / Revenue |
| Gross Margin % | Gross Profit / Revenue |

### Returns
| Filter | Description |
|--------|-------------|
| ROE % | Return on Equity |
| ROIC % | Return on Invested Capital |

### Income
| Filter | Description |
|--------|-------------|
| Dividend Yield % | Annual dividend / Price |

### Size
| Filter | Description |
|--------|-------------|
| Market Cap ($B) | Market capitalization in billions |

### Technical
| Filter | Description |
|--------|-------------|
| RSI (14) | Relative Strength Index |

### Balance Sheet
| Filter | Description |
|--------|-------------|
| Debt/Equity | Total Debt / Shareholder Equity |
| Current Ratio | Current Assets / Current Liabilities |

## Quick Templates

| Template | Filters |
|----------|---------|
| 💎 Value Stocks | P/E < 15, Div Yield > 2%, ROE > 10% |
| 🚀 High Growth | Rev Growth > 15%, EPS Growth > 20%, Gross Margin > 40% |
| 💰 Dividend Payers | Div Yield > 2.5%, P/E < 25, Net Margin > 10% |
| 📈 Momentum | RSI > 50, Rev Growth > 10%, EPS Growth > 15% |
| ⭐ Quality | ROE > 15%, Net Margin > 15%, Debt/Equity < 1 |
| 🔬 Small Cap Value | Market Cap < $10B, P/E < 15, Rev Growth > 10% |

## Python Data Fetcher

```bash
# Fetch default universe (~100 stocks)
python screener_fetcher.py

# Fetch specific tickers
python screener_fetcher.py AAPL MSFT GOOG META

# Output: stock_universe.json
```

## Files

| File | Description |
|------|-------------|
| `index.html` | Interactive screener UI |
| `screener_fetcher.py` | Python data fetcher |
| `stock_universe.json` | Cached stock data |

## Scoring System

Each stock gets a score (0-100) based on how many filters it passes:
- **80-100** (Green): Strong match
- **50-79** (Yellow): Partial match  
- **0-49** (Red): Weak match

## Saved Screens

Screens are saved to browser localStorage. Export/import coming soon.

## Logic Modes

- **AND**: Stock must pass ALL filters
- **OR**: Stock must pass ANY filter

## Integration

Part of the Guide Bot Research Suite:
- Earnings Calendar
- Short Interest Tracker
- Peer Comparison Tool
- 13F Holdings Tracker

---

Built by PM2 🎨 | Guide Bot Research Suite
