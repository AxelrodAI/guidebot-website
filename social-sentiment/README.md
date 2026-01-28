# Social Sentiment Aggregator

Track retail sentiment across Reddit (r/wallstreetbets, r/stocks) and StockTwits. Monitor mention velocity, sentiment polarity, and detect unusual activity.

## Features

- **Multi-Source Aggregation**: Reddit + StockTwits data
- **Ticker Mention Tracking**: Velocity, trending detection
- **Sentiment Scoring**: Custom lexicon for stock-specific terms (YOLO, diamond hands, etc.)
- **Engagement Weighting**: Upvotes and comments affect sentiment weight
- **Alert System**: Spike detection, sentiment reversals, extreme readings
- **Momentum Tracking**: Sentiment changes vs prior period
- **Historical Correlation**: Compare sentiment to price moves

## Installation

```bash
cd social-sentiment
pip install -r requirements.txt  # No external deps needed for core
```

## CLI Commands

### Analyze a Ticker
```bash
python cli.py analyze GME
python cli.py analyze TSLA
```

### Trending Tickers
```bash
python cli.py trending
python cli.py trending --hours 12 --limit 5
```

### Most Bullish
```bash
python cli.py bullish
python cli.py bullish --min-mentions 10 --limit 5
```

### Most Bearish
```bash
python cli.py bearish
python cli.py bearish --hours 48 --limit 5
```

### Sentiment Alerts
```bash
python cli.py alerts
python cli.py alerts GME AMC TSLA
```

### Scan Watchlist
```bash
python cli.py scan AAPL MSFT GOOGL NVDA AMD
```

### Sentiment Momentum
```bash
python cli.py momentum
python cli.py momentum --limit 5
```

### Voice Summary
```bash
python cli.py summary
```

### Run Tests
```bash
python cli.py test
```

## Sentiment Lexicon

### Bullish Terms
- moon, rocket, calls, yolo, diamond hands, hodl, tendies
- bullish, buy, long, breakout, squeeze, undervalued
- pump, rally, soar, surge, to the moon, gains

### Bearish Terms
- puts, short, sell, bearish, crash, dump, tank
- overvalued, bubble, scam, fraud, bagholding
- dead, rug pull, worthless, falling knife, trap

## Alert Types

| Alert | Trigger | Severity |
|-------|---------|----------|
| `mention_spike` | Volume >3x normal | high/medium |
| `sentiment_reversal` | Momentum shift >0.4 | high/medium |
| `extreme_bullish` | Weighted sentiment >0.7 | high |
| `extreme_bearish` | Weighted sentiment <-0.7 | high |

## Output Example

```
============================================================
  SOCIAL SENTIMENT: GME
============================================================
  Sentiment: +0.42 [BULLISH]
  Mentions:  156 (6.5/hr)
  Momentum:  +0.15

  Breakdown:
    Bullish:  58.3%
    Bearish:  19.2%
    Neutral:  22.5%

  Sources: {'reddit': 98, 'stocktwits': 58}

  ALERTS:
    [HIGH] GME: Mention volume 4.2x normal (26/hr vs 6.2/hr avg)
============================================================
```

## Data Sources

Currently uses sample data generator for testing. To connect real APIs:

1. **Reddit**: Use PRAW library with Reddit API credentials
2. **StockTwits**: Use StockTwits API (rate limited)
3. **Alternative**: Scrape RSS feeds or use third-party aggregators

## API Integration Points

```python
from sentiment_aggregator import SocialSentimentAggregator, SocialPost

agg = SocialSentimentAggregator()

# Add real posts from your data source
post = SocialPost(
    id="unique_id",
    source="reddit",
    ticker="GME",
    text="GME to the moon! Diamond hands!",
    timestamp=datetime.now(),
    author="user123",
    upvotes=500,
    comments=50
)
agg.add_post(post)

# Get summary
summary = agg.get_ticker_summary("GME")
```

## Accuracy Notes

Social sentiment is a contrarian indicator at extremes:
- Extreme bullish often precedes corrections
- Extreme bearish can signal bottoms
- Use alongside fundamental and technical analysis

## Files

- `sentiment_aggregator.py` - Core aggregation engine
- `cli.py` - Command-line interface
- `README.md` - This file

## Tests

6 test scenarios covering:
1. Sentiment analysis (bullish/bearish detection)
2. Ticker extraction ($AAPL style and plain)
3. Aggregation metrics
4. Trending detection
5. Alert generation
6. Bullish/bearish rankings
