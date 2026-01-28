# Buyback & Share Count Monitor

Track corporate share repurchase programs, execution rates, dilution, and identify companies with strong vs weak buyback track records.

## Features

- **Buyback Program Tracking**: Monitor 10b-18, ASR, and open market programs
- **Execution Analysis**: Track actual buyback amounts vs authorized
- **Share Count Trends**: Quarter-over-quarter dilution/reduction analysis
- **Yield Calculation**: Buyback yield and total shareholder yield
- **Timing Analysis**: Compare avg purchase price vs current price
- **Insider Activity Alerts**: Flag insiders selling during buyback windows
- **Credibility Scoring**: Score companies on execution and timing history
- **Opportunity Screening**: Find high-yield stocks with good execution

## Installation

```bash
cd buyback-monitor
# No external dependencies - uses Python standard library
```

## Usage

### Full Analysis

```bash
python cli.py analyze AAPL
```

### Buyback Programs

```bash
python cli.py program MSFT
```

### Share Count Trends

```bash
python cli.py shares GOOGL
```

### Execution History

```bash
python cli.py execution NVDA
```

### Insider Activity

```bash
python cli.py insiders META
```

### Compare Yields

```bash
python cli.py yields
```

### Scan for Opportunities

```bash
python cli.py scan
python cli.py scan --min-yield 4
```

### Find Worst Executors

```bash
python cli.py worst
```

### Alerts

```bash
python cli.py alerts
python cli.py alerts AAPL
```

### Watchlist

```bash
python cli.py watchlist --add AAPL
python cli.py watchlist --remove MSFT
python cli.py watchlist
```

### Run Tests

```bash
python cli.py test
```

## Alert Types

| Alert | Severity | Description |
|-------|----------|-------------|
| NEW_AUTHORIZATION | Medium | New buyback program announced |
| LOW_EXECUTION | Medium | Execution rate <50% of authorized |
| INSIDER_SELLING_DURING_BUYBACK | High | Insiders selling while company buys back |
| HIGH_BUYBACK_YIELD | Low | Attractive yield >5% |
| NET_DILUTION | High | Share count increasing despite buybacks |
| POOR_TIMING | Medium | Company buys at elevated prices |

## Metrics Explained

### Buyback Yield
Annual buyback amount / Market cap. Higher is better.

### Execution Rate
Total executed / Total authorized. Companies that announce but don't execute have low rates.

### Execution Score (0-100)
Based on execution rate and consistency.

### Timing Score (0-100)
Compares average buyback price to current price. High scores mean they bought when prices were lower.

### Credibility Score
Combined execution + timing score. Trust companies with high credibility.

### Net Share Change
Year-over-year change in shares outstanding. Negative = good (buybacks > dilution).

## Red Flags

1. **High authorized, low execution**: Announces but doesn't follow through
2. **Net dilution**: Share count increases despite buyback announcements
3. **Insider selling during buyback**: Management doesn't believe their own story
4. **Poor timing**: Consistently buys at elevated prices
5. **Buyback to offset SBC**: Buybacks just cover stock compensation, no net return to shareholders

## Example Output

```
═══════════════════════════════════════════════════════════════
  BUYBACK ANALYSIS: AAPL
═══════════════════════════════════════════════════════════════

📊 OVERVIEW
   Company:           AAPL Corp
   Current Price:     $185.50
   Market Cap:        $2.8T
   Shares Outstanding: 15.1B

💰 YIELD METRICS
   Buyback Yield:     3.25%
   Total Yield:       3.75% (dividends + buybacks)

📋 ACTIVE BUYBACK PROGRAMS
   Program: 10b-18
      Announced:    2024-05-01
      Authorized:   $90.0B
      Remaining:    $45.2B (50% left)
      Expires:      2027-05-01

📈 SHARE COUNT TREND (Last 4 Quarters)
   Quarter      Shares           Change         Source
   -------------------------------------------------------
   Q4 2025       15,100M       🔻 -1.25%       buyback
   Q3 2025       15,291M       🔻 -0.95%       buyback
   Q2 2025       15,437M       🔺 +0.32%       dilution
   Q1 2025       15,388M       🔻 -0.88%       buyback

   Net 1-Year Change: -2.76%
   ✓ Share count declining (buybacks > dilution)

📊 BUYBACK SCORECARD
   Execution Score:   ██████████ 85/100
   Timing Score:      ████████░░ 72/100
   Credibility:       █████████░ 78/100
```

## Data Sources (Production)

For real data, integrate with:
- SEC EDGAR (10-Q/10-K for share counts)
- Company press releases (buyback announcements)
- Bloomberg/Refinitiv (execution data)
- SEC Form 4 (insider transactions)

## License

MIT
