# Peer Comparison Tool

Auto-generate comprehensive comp tables for any stock with one click.

## Features

- **Auto Peer Selection** - Finds sector peers automatically
- **Custom Peers** - Specify your own comparison set
- **Market Cap Filtering** - Filter by mega, large, mid, small cap
- **Comprehensive Metrics**:
  - Valuation: P/E, Fwd P/E, EV/EBITDA, EV/Sales, P/S, PEG, P/B
  - Growth: Revenue, EPS, FCF growth rates
  - Profitability: Gross, Operating, Net margins
  - Returns: ROE, ROIC, ROA
- **Ranking System** - See where target ranks vs peers on each metric
- **Excel/CSV Export** - One-click export for modeling prep
- **Premium/Discount Analysis** - Instantly see valuation vs peer average

## Quick Start

1. **Web Dashboard**: Open `index.html` in browser
2. **Enter ticker** (e.g., AAPL)
3. **Select peer method**: Sector, Industry, or Custom
4. **Click "Generate Comps"**

## Python Data Fetcher

```bash
# Auto-find sector peers
python peer_comp_fetcher.py AAPL

# Specify custom peers
python peer_comp_fetcher.py AAPL MSFT GOOG META AMZN

# Export to Excel
python peer_comp_fetcher.py AAPL --export
```

## Files

| File | Description |
|------|-------------|
| `index.html` | Interactive web dashboard |
| `peer_comp_fetcher.py` | Python data fetcher |
| `peer_comp.json` | Cached comparison data |

## Metric Definitions

### Valuation
| Metric | Definition | Interpretation |
|--------|------------|----------------|
| P/E | Price / Earnings | Lower = cheaper |
| Fwd P/E | Price / Forward Earnings | Lower = cheaper |
| EV/EBITDA | Enterprise Value / EBITDA | Lower = cheaper |
| EV/Sales | Enterprise Value / Revenue | Lower = cheaper |
| P/S | Price / Sales | Lower = cheaper |
| PEG | P/E / EPS Growth | <1 = undervalued |
| P/B | Price / Book Value | Lower = cheaper |

### Growth
| Metric | Definition | Interpretation |
|--------|------------|----------------|
| Rev Growth | YoY Revenue Growth % | Higher = better |
| EPS Growth | YoY Earnings Growth % | Higher = better |
| FCF Growth | YoY Free Cash Flow Growth % | Higher = better |

### Profitability
| Metric | Definition | Interpretation |
|--------|------------|----------------|
| Gross Margin | Gross Profit / Revenue | Higher = better |
| Op Margin | Operating Income / Revenue | Higher = better |
| Net Margin | Net Income / Revenue | Higher = better |

### Returns
| Metric | Definition | Interpretation |
|--------|------------|----------------|
| ROE | Net Income / Shareholder Equity | Higher = better |
| ROIC | NOPAT / Invested Capital | Higher = better |
| ROA | Net Income / Total Assets | Higher = better |

## Sector Peer Groups

Pre-defined peer sets for each sector:

- **Technology**: AAPL, MSFT, GOOG, META, NVDA, AMZN, CRM, ORCL, ADBE, INTC
- **Financial**: JPM, BAC, WFC, GS, MS, C, USB, PNC, SCHW, BLK
- **Healthcare**: JNJ, UNH, PFE, ABBV, MRK, LLY, TMO, ABT, DHR, BMY
- **Consumer**: AMZN, TSLA, HD, NKE, MCD, SBUX, LOW, TJX, BKNG, GM
- **Energy**: XOM, CVX, COP, SLB, EOG, PXD, MPC, VLO, PSX, OXY

## Output Example

```
📈 AAPL vs Peer Averages:
--------------------------------------------------
  P/E               28.5x vs    38.2x (-25.4%) ✅
  EV/EBITDA         21.8x vs    24.5x (-11.0%) ✅
  Revenue Growth     8.5% vs    15.2% (-44.1%) ⚠️
  Net Margin        25.3% vs    22.8% (+11.0%) ✅
  ROE              147.2% vs    45.2% (+225.7%) ✅
```

## Integration

Links to other Guide Bot tools:
- Earnings Calendar (`/earnings-calendar/`)
- Short Interest Tracker (`/short-interest/`)
- H.8 Banking Dashboard (`/h8-dashboard/`)

---

Built by PM2 🎨 | Guide Bot Research Suite
