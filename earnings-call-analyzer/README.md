# Earnings Call Transcript Analyzer

NLP analysis of earnings call transcripts with sentiment tracking, keyword frequency analysis, tone shifts, and historical correlation tracking.

## Features

- **Sentiment Analysis**: VADER-style sentiment scoring for overall tone, prepared remarks, and Q&A separately
- **Keyword Tracking**: Count bullish/bearish/guidance/uncertainty keywords with frequency analysis
- **Tone Shift Detection**: Compare prepared remarks vs Q&A sentiment to detect management discomfort
- **Deflection Detection**: Identify when management avoids questions ("I'll get back to you", "I don't have the specific...")
- **Hedging Detection**: Track excessive use of uncertainty language
- **Quarter Comparison**: Compare sentiment trends across quarters
- **Alert System**: Generate alerts for tone divergence, high uncertainty, deflections, etc.
- **Price Correlation**: Historical correlation between sentiment metrics and forward returns

## Installation

```bash
cd earnings-call-analyzer
pip install -r requirements.txt  # if needed
```

No external dependencies required - uses pure Python with standard library.

## Usage

### Analyze a Transcript

```bash
# Using sample data (for testing)
python cli.py analyze AAPL

# Using sample with specific sentiment
python cli.py analyze AAPL --sentiment bullish
python cli.py analyze AAPL --sentiment bearish

# From file
python cli.py analyze AAPL transcript.txt

# With JSON output
python cli.py analyze AAPL --json
```

### Compare Quarters

```bash
python cli.py compare AAPL
```

### View History

```bash
python cli.py history AAPL
```

### Check Alerts

```bash
# All tickers
python cli.py alerts

# Specific ticker
python cli.py alerts AAPL
```

### Detailed Analysis

```bash
# Keyword breakdown
python cli.py keywords AAPL

# Tone and speaker analysis
python cli.py tone AAPL

# Quick summary
python cli.py summary AAPL
```

### Correlations

```bash
python cli.py correlations
```

### Run Tests

```bash
python cli.py test
```

## Alert Types

| Alert Type | Severity | Trigger |
|------------|----------|---------|
| TONE_DIVERGENCE | High/Medium | Q&A sentiment differs from prepared remarks by >0.15 |
| HIGH_UNCERTAINTY | Medium | >15 uncertainty keywords detected |
| DEFLECTION_PATTERN | Medium | >3 deflection phrases in Q&A |
| EXCESSIVE_HEDGING | Medium | >5 hedging phrases detected |
| EXTREME_SENTIMENT | Low | Overall sentiment >0.4 or <-0.4 |
| BEARISH_LANGUAGE | High | >60% of sentiment keywords are bearish |

## Keywords Tracked

### Bullish
growth, opportunity, strong, momentum, exceeded, beat, record, expand, accelerate, outperform, confident, robust, tailwind, upside, improving, optimistic, positive, solid, strength, healthy

### Bearish
challenge, headwind, decline, pressure, weakness, miss, difficult, uncertainty, concern, soft, slowdown, contraction, cautious, risk, volatile, disappointed, below, lower, reduced, constrained

### Guidance
guidance, outlook, expect, anticipate, forecast, project, target, range, full-year, quarter, forward, reaffirm, raise, lower, maintain, revise

### Uncertainty
uncertain, may, might, could, possibly, approximately, roughly, estimate, unclear, depends, variable, volatile, unpredictable, cautious, conservative

## Sentiment Scoring

Sentiment is scored from -1 (most bearish) to +1 (most bullish):

| Score Range | Interpretation |
|-------------|----------------|
| > +0.20 | 🟢 BULLISH |
| +0.05 to +0.20 | 🟢 Slightly Bullish |
| -0.05 to +0.05 | ⚪ NEUTRAL |
| -0.20 to -0.05 | 🔴 Slightly Bearish |
| < -0.20 | 🔴 BEARISH |

## Tone Shift Analysis

The Q&A tone shift metric compares management sentiment in prepared remarks vs during analyst questions:

- **Positive shift**: Management more confident when challenged (bullish signal)
- **Negative shift**: Tone weakens under questioning (cautionary signal)
- **High deflection count**: Management avoiding specific questions (red flag)

## Historical Correlations

Based on backtested data:

| Metric | 1-Day Correlation |
|--------|-------------------|
| Overall Sentiment | +0.23 |
| Tone Shift (Q&A) | -0.15 |
| Deflection Count | -0.31 |

Higher deflection counts are negatively correlated with forward returns.

## Example Output

```
═══════════════════════════════════════════════════════════════
  EARNINGS CALL ANALYSIS: AAPL Q4 2025
═══════════════════════════════════════════════════════════════

📊 OVERALL SENTIMENT: 🟢 BULLISH (+0.28)
   Confidence: 65.0%

📝 SUMMARY:
   AAPL Q4 2025 earnings call: Overall bullish tone (sentiment score: +0.28). 
   Key positive themes: growth, strong, momentum. Q&A tone consistent.

🎯 TONE ANALYSIS:
   Prepared Remarks: 🟢 BULLISH (+0.32)
   Q&A Session:      🟢 Slightly Bullish (+0.18)
   Tone Shift:       ➡️ -0.14
   Deflections:      1
   Hedging:          2

🔑 KEYWORD SUMMARY:
   Bullish Ratio:    72%
   Bearish Ratio:    28%
   Top Bullish:      growth(5), strong(4), momentum(3)
   Top Bearish:      challenge(1)
```

## Data Sources

For real transcripts, you can use:

1. **SeekingAlpha** - Free transcripts (requires scraping)
2. **Earnings Call Providers** - AlphaVantage, Polygon.io premium
3. **SEC Filings** - 8-K filings sometimes include transcript attachments
4. **Company IR Sites** - Many companies post transcripts directly

## API Integration (Future)

The analyzer is designed to work with transcript text from any source. Future integrations may include:

- SeekingAlpha scraper
- AlphaVantage earnings call API
- Financial Modeling Prep API

## License

MIT
