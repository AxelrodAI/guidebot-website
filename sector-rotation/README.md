# Sector Rotation Dashboard

Visualize where money is flowing across market sectors.

## Features

- **Relative Strength Ranking** - Sectors ranked by performance
- **Momentum Heatmap** - Color-coded returns (1W/1M/3M/6M/YTD)
- **Economic Cycle Position** - Current cycle phase indicator
- **Pair Trade Ideas** - Long/short sector pairs with spreads
- **Performance Chart** - Rebased sector performance comparison

## Sectors Tracked

| Ticker | Sector |
|--------|--------|
| XLK | Technology |
| XLY | Consumer Discretionary |
| XLF | Financials |
| XLE | Energy |
| XLV | Healthcare |
| XLI | Industrials |
| XLP | Consumer Staples |
| XLU | Utilities |
| XLRE | Real Estate |
| XLB | Materials |
| XLC | Communication Services |

## Economic Cycle Phases

### 🚀 Expansion
- **Sectors**: Tech, Consumer Disc, Industrials
- **Characteristics**: Rising GDP, low unemployment

### ⚡ Peak/Late Cycle
- **Sectors**: Energy, Materials, Financials
- **Characteristics**: Full employment, rising inflation

### 📉 Contraction
- **Sectors**: Healthcare, Utilities, Staples
- **Characteristics**: Defensive positioning, falling yields

### 🔄 Recovery
- **Sectors**: Financials, Real Estate, Small Caps
- **Characteristics**: Steepening yield curve, credit improvement

## Momentum Heatmap Colors

| Color | Return Range |
|-------|--------------|
| 🟢 Strong Green | ≥ +5% |
| 🟢 Light Green | +1% to +5% |
| ⚪ Neutral | -1% to +1% |
| 🔴 Light Red | -5% to -1% |
| 🔴 Strong Red | ≤ -5% |

## Pair Trade Signals

Pairs are selected based on:
- **Spread divergence** - Performance gap between sectors
- **Z-Score** - Standard deviations from mean spread
- **Fundamental rationale** - Economic thesis supporting the trade

## Files

| File | Description |
|------|-------------|
| `index.html` | Dashboard UI |

## Data Sources

- Sector ETF prices via Yahoo Finance
- Economic cycle indicators via Fed data

## Integration

Part of the Guide Bot Research Suite:
- Stock Screener
- Short Interest Tracker
- Peer Comparison Tool
- Earnings Calendar

---

Built by PM2 🎨 | Guide Bot Research Suite
