# Portfolio Risk Monitor

Monitor portfolio risk through concentration, correlation, and volatility analysis. Identify overconcentration, correlation clustering, and volatility spikes before they become problems.

## Features

- **Concentration Analysis**: Position weights, sector exposure, HHI index
- **Correlation Analysis**: Pairwise correlations, high-correlation detection
- **Volatility Analysis**: Portfolio vol, beta, Value at Risk (VaR)
- **Risk Scoring**: 0-100 composite risk score
- **Position Management**: Add/remove/update positions
- **Alert System**: Set thresholds for risk metrics
- **Recommendations**: Actionable risk mitigation suggestions

## Installation

```bash
# No external dependencies - uses Python standard library
python risk_monitor.py --help
```

## Usage

### Full Risk Report
```bash
python risk_monitor.py report
python risk_monitor.py report --json
```

### Concentration Analysis
```bash
# HHI index, position weights, sector breakdown
python risk_monitor.py concentration
```

### Correlation Analysis
```bash
# Pairwise correlations, diversification opportunities
python risk_monitor.py correlation
```

### Volatility Analysis
```bash
# Portfolio vol, beta, VaR
python risk_monitor.py volatility
```

### Position Management
```bash
# List positions
python risk_monitor.py positions

# Add position (or average into existing)
python risk_monitor.py add AAPL 100 175.50
python risk_monitor.py add NVDA 50 900.00

# Remove position
python risk_monitor.py remove TSLA
```

### Risk Alerts
```bash
# Alert if risk score exceeds 70
python risk_monitor.py alert risk_score 70

# Alert if beta exceeds 1.5
python risk_monitor.py alert beta 1.5

# Alert if volatility exceeds 30%
python risk_monitor.py alert volatility 30

# Check alerts
python risk_monitor.py check-alerts
```

## Risk Metrics

### Concentration (HHI)
- **< 1500**: Diversified
- **> 1500**: Concentrated

### Thresholds
| Metric | Warning Threshold |
|--------|-------------------|
| Single Position | > 25% |
| Sector Exposure | > 40% |
| Correlation | > 0.70 |
| Portfolio Beta | > 1.5 |

### Risk Score
Composite 0-100 score based on:
- Concentration (HHI)
- Average correlation
- Portfolio volatility
- Portfolio beta

## Output Example

```
🟡 PORTFOLIO RISK REPORT
   Sample Portfolio | 2026-01-27 21:30

📊 Summary
   Total Value: $125,432.00
   Positions: 8
   Risk Score: 52/100 (Moderate)

📦 Concentration
   HHI: 1,423 (Diversified)
   Top 5: 78.2% of portfolio

   Top Positions:
   ⚠️ NVDA: 28.1% ($35,280)
      MSFT: 18.2% ($22,840)
      AAPL: 14.4% ($18,050)

🔗 Correlation
   Average: 0.45 (Moderate risk)
   High-Correlation Pairs: 3

📈 Volatility
   Annual: 24.5% (Moderate)
   Beta: 1.22 (Moderate)
   VaR (95%, Daily): $1,845

⚠️ WARNINGS (2)
   • NVDA is 28.1% (max 25%)
   • Technology sector is 62.3% (max 40%)

💡 RECOMMENDATIONS
   🔴 [Position Size] Reduce NVDA from 28.1% to under 25%
   🟡 [Sector Exposure] Reduce Technology exposure from 62.3% to under 40%
```

## Data Storage

Portfolio and alerts stored in `./data/`:
- `portfolio.json` - Positions and holdings
- `alerts.json` - Active alert configurations

## Supported Tickers

40+ common US stocks with sector classification:
- Technology: AAPL, MSFT, GOOGL, META, NVDA, AMD
- Financials: JPM, BAC, GS, MS, C
- Healthcare: JNJ, UNH, PFE, MRK, ABBV
- Energy: XOM, CVX, COP, SLB
- Consumer: AMZN, TSLA, PG, KO, WMT
- And more...

## Integration Ideas

- **Morning Report**: Run `report` in daily cron job
- **Alert Webhook**: Pipe `check-alerts --json` to Slack/Discord
- **Dashboard**: Use `--json` output for web visualization
- **Rebalance Trigger**: Alert when concentration thresholds breached

## Built By

PM3 - Backend/CLI Pipeline  
Part of the Guidebot Pipeline

---

*Note: Currently uses simulated price/volatility data. In production, integrate with Yahoo Finance, Alpha Vantage, or broker APIs.*
