"""
Social Sentiment Aggregator
Track retail sentiment across Reddit and StockTwits
"""

import json
import os
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import random
import math

# Sentiment lexicon for stock-specific terms
BULLISH_TERMS = {
    'moon', 'rocket', 'calls', 'yolo', 'diamond hands', 'hodl', 'tendies',
    'bullish', 'buy', 'long', 'breakout', 'squeeze', 'undervalued', 'dip',
    'pump', 'rally', 'soar', 'surge', 'explode', 'to the moon', 'ath',
    'all time high', 'green', 'rip', 'flying', 'mooning', 'gains', 'winner',
    'printing', 'lambo', 'beast', 'alpha', 'strong', 'oversold', 'accumulate'
}

BEARISH_TERMS = {
    'puts', 'short', 'sell', 'bearish', 'crash', 'dump', 'tank', 'drill',
    'overvalued', 'bubble', 'scam', 'fraud', 'bagholding', 'bagholder', 'rip',
    'dead', 'rug pull', 'ponzi', 'worthless', 'avoid', 'red', 'plunge',
    'collapse', 'fail', 'bankruptcy', 'dilution', 'falling knife', 'trap',
    'overbought', 'weak', 'exit', 'sell off', 'panic', 'fear', 'loss'
}

@dataclass
class SocialPost:
    """Represents a single social media post"""
    id: str
    source: str  # reddit, stocktwits
    ticker: str
    text: str
    timestamp: datetime
    author: str
    upvotes: int = 0
    comments: int = 0
    sentiment_score: float = 0.0
    bullish_terms: List[str] = field(default_factory=list)
    bearish_terms: List[str] = field(default_factory=list)

@dataclass
class TickerSentiment:
    """Aggregated sentiment for a ticker"""
    ticker: str
    mention_count: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    avg_sentiment: float = 0.0
    sentiment_momentum: float = 0.0  # Change vs prior period
    mention_velocity: float = 0.0  # Mentions per hour
    weighted_sentiment: float = 0.0  # Engagement-weighted
    top_posts: List[Dict] = field(default_factory=list)
    sources: Dict[str, int] = field(default_factory=dict)
    hourly_mentions: List[int] = field(default_factory=list)

@dataclass
class SentimentAlert:
    """Alert for significant sentiment events"""
    ticker: str
    alert_type: str  # spike, reversal, divergence, extreme
    severity: str  # high, medium, low
    message: str
    timestamp: datetime
    data: Dict = field(default_factory=dict)

class SocialSentimentAggregator:
    """Aggregate and analyze social media sentiment for stocks"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.posts: List[SocialPost] = []
        self.ticker_data: Dict[str, TickerSentiment] = {}
        self.historical_sentiment: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.price_data: Dict[str, List[Tuple[datetime, float]]] = {}  # For correlation
        
    def analyze_sentiment(self, text: str) -> Tuple[float, List[str], List[str]]:
        """Analyze sentiment of text, return score and matched terms"""
        text_lower = text.lower()
        
        bullish_found = []
        bearish_found = []
        
        for term in BULLISH_TERMS:
            if term in text_lower:
                bullish_found.append(term)
                
        for term in BEARISH_TERMS:
            if term in text_lower:
                bearish_found.append(term)
        
        # Calculate score (-1 to 1)
        total = len(bullish_found) + len(bearish_found)
        if total == 0:
            return 0.0, [], []
            
        score = (len(bullish_found) - len(bearish_found)) / total
        return score, bullish_found, bearish_found
    
    def extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text"""
        # Match $TICKER or standalone uppercase tickers
        patterns = [
            r'\$([A-Z]{1,5})\b',  # $AAPL style
            r'\b([A-Z]{2,5})\b'   # Plain uppercase (2-5 chars)
        ]
        
        tickers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Filter out common words
                if match not in {'I', 'A', 'THE', 'AND', 'FOR', 'TO', 'IS', 'IT', 'OR', 
                                'BE', 'AS', 'AT', 'BY', 'IF', 'IN', 'OF', 'ON', 'SO',
                                'DD', 'EPS', 'CEO', 'CFO', 'IPO', 'ATH', 'WSB', 'YOLO',
                                'IMO', 'FOMO', 'FUD', 'LOL', 'WTF', 'API', 'USD', 'ETF'}:
                    tickers.add(match)
        
        return list(tickers)
    
    def add_post(self, post: SocialPost) -> None:
        """Add a post and update sentiment data"""
        # Analyze sentiment if not already done
        if post.sentiment_score == 0.0:
            score, bullish, bearish = self.analyze_sentiment(post.text)
            post.sentiment_score = score
            post.bullish_terms = bullish
            post.bearish_terms = bearish
        
        self.posts.append(post)
        
        # Update ticker aggregation
        ticker = post.ticker
        if ticker not in self.ticker_data:
            self.ticker_data[ticker] = TickerSentiment(ticker=ticker)
        
        ts = self.ticker_data[ticker]
        ts.mention_count += 1
        
        if post.sentiment_score > 0.1:
            ts.bullish_count += 1
        elif post.sentiment_score < -0.1:
            ts.bearish_count += 1
        else:
            ts.neutral_count += 1
        
        # Track source
        ts.sources[post.source] = ts.sources.get(post.source, 0) + 1
        
        # Add to historical
        self.historical_sentiment[ticker].append((post.timestamp, post.sentiment_score))
    
    def calculate_aggregates(self, ticker: str, hours: int = 24) -> TickerSentiment:
        """Calculate aggregate sentiment metrics for a ticker"""
        if ticker not in self.ticker_data:
            return TickerSentiment(ticker=ticker)
        
        ts = self.ticker_data[ticker]
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # Get recent posts
        recent_posts = [p for p in self.posts 
                       if p.ticker == ticker and p.timestamp >= cutoff]
        
        if not recent_posts:
            return ts
        
        # Average sentiment
        scores = [p.sentiment_score for p in recent_posts]
        ts.avg_sentiment = sum(scores) / len(scores) if scores else 0
        
        # Weighted by engagement
        total_engagement = sum(p.upvotes + p.comments + 1 for p in recent_posts)
        weighted_sum = sum(p.sentiment_score * (p.upvotes + p.comments + 1) for p in recent_posts)
        ts.weighted_sentiment = weighted_sum / total_engagement if total_engagement > 0 else 0
        
        # Velocity (mentions per hour)
        ts.mention_velocity = len(recent_posts) / hours
        
        # Top posts by engagement
        sorted_posts = sorted(recent_posts, key=lambda p: p.upvotes + p.comments, reverse=True)
        ts.top_posts = [
            {
                'text': p.text[:200],
                'source': p.source,
                'sentiment': p.sentiment_score,
                'upvotes': p.upvotes,
                'author': p.author
            }
            for p in sorted_posts[:5]
        ]
        
        # Hourly breakdown
        hourly = defaultdict(int)
        for p in recent_posts:
            hour_key = p.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly[hour_key] += 1
        ts.hourly_mentions = list(hourly.values())[-24:] if hourly else []
        
        # Sentiment momentum (compare to prior period)
        prior_cutoff = cutoff - timedelta(hours=hours)
        prior_posts = [p for p in self.posts 
                      if p.ticker == ticker and prior_cutoff <= p.timestamp < cutoff]
        if prior_posts:
            prior_avg = sum(p.sentiment_score for p in prior_posts) / len(prior_posts)
            ts.sentiment_momentum = ts.avg_sentiment - prior_avg
        
        return ts
    
    def detect_spike(self, ticker: str, threshold: float = 3.0) -> Optional[SentimentAlert]:
        """Detect unusual mention spikes"""
        ts = self.calculate_aggregates(ticker, hours=24)
        
        if len(ts.hourly_mentions) < 6:
            return None
        
        # Calculate baseline (exclude last 2 hours)
        baseline = ts.hourly_mentions[:-2] if len(ts.hourly_mentions) > 2 else ts.hourly_mentions
        if not baseline:
            return None
            
        avg = sum(baseline) / len(baseline)
        if avg == 0:
            return None
            
        # Check recent hours
        recent = ts.hourly_mentions[-2:] if len(ts.hourly_mentions) >= 2 else ts.hourly_mentions
        recent_avg = sum(recent) / len(recent) if recent else 0
        
        ratio = recent_avg / avg
        
        if ratio >= threshold:
            return SentimentAlert(
                ticker=ticker,
                alert_type='mention_spike',
                severity='high' if ratio > 5 else 'medium',
                message=f"{ticker}: Mention volume {ratio:.1f}x normal ({int(recent_avg)}/hr vs {avg:.1f}/hr avg)",
                timestamp=datetime.now(),
                data={'ratio': ratio, 'recent_velocity': recent_avg, 'baseline': avg}
            )
        return None
    
    def detect_sentiment_reversal(self, ticker: str, threshold: float = 0.4) -> Optional[SentimentAlert]:
        """Detect significant sentiment reversals"""
        ts = self.calculate_aggregates(ticker, hours=24)
        
        if abs(ts.sentiment_momentum) >= threshold:
            direction = 'bullish' if ts.sentiment_momentum > 0 else 'bearish'
            severity = 'high' if abs(ts.sentiment_momentum) > 0.6 else 'medium'
            
            return SentimentAlert(
                ticker=ticker,
                alert_type='sentiment_reversal',
                severity=severity,
                message=f"{ticker}: Sentiment turned {direction} (momentum: {ts.sentiment_momentum:+.2f})",
                timestamp=datetime.now(),
                data={'momentum': ts.sentiment_momentum, 'current': ts.avg_sentiment}
            )
        return None
    
    def detect_extreme_sentiment(self, ticker: str) -> Optional[SentimentAlert]:
        """Detect extremely bullish or bearish sentiment"""
        ts = self.calculate_aggregates(ticker, hours=24)
        
        if ts.mention_count < 10:  # Need enough data
            return None
        
        # Check for extreme readings
        if ts.weighted_sentiment > 0.7:
            return SentimentAlert(
                ticker=ticker,
                alert_type='extreme_bullish',
                severity='high',
                message=f"{ticker}: EXTREME BULLISH sentiment ({ts.weighted_sentiment:.2f}) - {ts.bullish_count}/{ts.mention_count} posts bullish",
                timestamp=datetime.now(),
                data={'sentiment': ts.weighted_sentiment, 'bullish_pct': ts.bullish_count/ts.mention_count}
            )
        elif ts.weighted_sentiment < -0.7:
            return SentimentAlert(
                ticker=ticker,
                alert_type='extreme_bearish',
                severity='high',
                message=f"{ticker}: EXTREME BEARISH sentiment ({ts.weighted_sentiment:.2f}) - {ts.bearish_count}/{ts.mention_count} posts bearish",
                timestamp=datetime.now(),
                data={'sentiment': ts.weighted_sentiment, 'bearish_pct': ts.bearish_count/ts.mention_count}
            )
        return None
    
    def get_all_alerts(self, tickers: List[str] = None) -> List[SentimentAlert]:
        """Get all alerts for given tickers"""
        if tickers is None:
            tickers = list(self.ticker_data.keys())
        
        alerts = []
        for ticker in tickers:
            spike = self.detect_spike(ticker)
            if spike:
                alerts.append(spike)
                
            reversal = self.detect_sentiment_reversal(ticker)
            if reversal:
                alerts.append(reversal)
                
            extreme = self.detect_extreme_sentiment(ticker)
            if extreme:
                alerts.append(extreme)
        
        # Sort by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 2))
        
        return alerts
    
    def get_trending(self, hours: int = 24, limit: int = 10) -> List[Dict]:
        """Get trending tickers by mention velocity"""
        trending = []
        
        for ticker in self.ticker_data:
            ts = self.calculate_aggregates(ticker, hours=hours)
            if ts.mention_count >= 5:  # Minimum threshold
                trending.append({
                    'ticker': ticker,
                    'mentions': ts.mention_count,
                    'velocity': ts.mention_velocity,
                    'sentiment': ts.weighted_sentiment,
                    'momentum': ts.sentiment_momentum,
                    'bullish_pct': ts.bullish_count / ts.mention_count if ts.mention_count > 0 else 0,
                    'sources': ts.sources
                })
        
        # Sort by velocity
        trending.sort(key=lambda x: x['velocity'], reverse=True)
        return trending[:limit]
    
    def get_most_bullish(self, hours: int = 24, min_mentions: int = 5, limit: int = 10) -> List[Dict]:
        """Get most bullish tickers"""
        results = []
        
        for ticker in self.ticker_data:
            ts = self.calculate_aggregates(ticker, hours=hours)
            if ts.mention_count >= min_mentions:
                results.append({
                    'ticker': ticker,
                    'sentiment': ts.weighted_sentiment,
                    'mentions': ts.mention_count,
                    'bullish_pct': ts.bullish_count / ts.mention_count,
                    'momentum': ts.sentiment_momentum
                })
        
        results.sort(key=lambda x: x['sentiment'], reverse=True)
        return results[:limit]
    
    def get_most_bearish(self, hours: int = 24, min_mentions: int = 5, limit: int = 10) -> List[Dict]:
        """Get most bearish tickers"""
        results = []
        
        for ticker in self.ticker_data:
            ts = self.calculate_aggregates(ticker, hours=hours)
            if ts.mention_count >= min_mentions:
                results.append({
                    'ticker': ticker,
                    'sentiment': ts.weighted_sentiment,
                    'mentions': ts.mention_count,
                    'bearish_pct': ts.bearish_count / ts.mention_count,
                    'momentum': ts.sentiment_momentum
                })
        
        results.sort(key=lambda x: x['sentiment'])
        return results[:limit]
    
    def calculate_correlation(self, ticker: str, price_changes: List[float], 
                            sentiment_changes: List[float]) -> float:
        """Calculate correlation between sentiment and price changes"""
        if len(price_changes) != len(sentiment_changes) or len(price_changes) < 5:
            return 0.0
        
        n = len(price_changes)
        
        # Calculate means
        price_mean = sum(price_changes) / n
        sent_mean = sum(sentiment_changes) / n
        
        # Calculate correlation
        numerator = sum((p - price_mean) * (s - sent_mean) 
                       for p, s in zip(price_changes, sentiment_changes))
        
        price_var = sum((p - price_mean) ** 2 for p in price_changes)
        sent_var = sum((s - sent_mean) ** 2 for s in sentiment_changes)
        
        denominator = math.sqrt(price_var * sent_var)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def generate_sample_data(self, tickers: List[str] = None, num_posts: int = 500) -> None:
        """Generate sample social media data for testing"""
        if tickers is None:
            tickers = ['GME', 'AMC', 'TSLA', 'NVDA', 'AAPL', 'SPY', 'AMD', 'PLTR', 'BB', 'NOK']
        
        sources = ['reddit', 'stocktwits']
        subreddits = ['wallstreetbets', 'stocks', 'investing', 'options']
        
        bullish_templates = [
            "{ticker} to the moon! Diamond hands! 💎🙌",
            "Just bought more {ticker}. This thing is ready to squeeze.",
            "{ticker} is so undervalued. Buying calls at open.",
            "YOLO'd my entire account into {ticker}. Let's go!",
            "{ticker} breakout incoming. Bullish AF.",
            "Loading up on {ticker} before earnings. This is going to rip.",
            "{ticker} shorts are gonna get crushed. $200 EOW.",
            "Finally in the green on {ticker}! Told you to hodl!",
        ]
        
        bearish_templates = [
            "{ticker} is a dead cat bounce. Buying puts.",
            "Sold all my {ticker}. This thing is tanking.",
            "{ticker} overvalued trash. Short it.",
            "Getting out of {ticker} before it crashes more.",
            "{ticker} is going to zero. Complete scam.",
            "Bagholding {ticker} was a mistake. Should have sold.",
            "The {ticker} pump is over. Time to dump.",
            "{ticker} earnings will be disaster. Loading puts.",
        ]
        
        neutral_templates = [
            "What's everyone's PT on {ticker}?",
            "Thinking about {ticker}. Anyone have DD?",
            "Just watching {ticker} today. Interesting action.",
            "{ticker} moving sideways. Waiting for a signal.",
        ]
        
        # Generate posts with varying timestamps over 48 hours
        base_time = datetime.now()
        
        # Give some tickers more mentions (trending)
        ticker_weights = {
            'GME': 3.0, 'TSLA': 2.5, 'NVDA': 2.0, 'SPY': 1.5
        }
        
        for i in range(num_posts):
            # Weighted ticker selection
            weights = [ticker_weights.get(t, 1.0) for t in tickers]
            total_weight = sum(weights)
            r = random.random() * total_weight
            cumulative = 0
            ticker = tickers[0]
            for t, w in zip(tickers, weights):
                cumulative += w
                if r <= cumulative:
                    ticker = t
                    break
            
            # Determine sentiment (with some ticker bias)
            ticker_bias = {
                'GME': 0.4, 'AMC': 0.3, 'TSLA': 0.2, 'NVDA': 0.3,
                'PLTR': 0.1, 'SPY': 0.0, 'AAPL': 0.1
            }
            bias = ticker_bias.get(ticker, 0.0)
            sentiment_roll = random.random() + bias
            
            if sentiment_roll > 0.7:
                template = random.choice(bullish_templates)
            elif sentiment_roll < 0.3:
                template = random.choice(bearish_templates)
            else:
                template = random.choice(neutral_templates)
            
            text = template.format(ticker=ticker)
            
            # Random timestamp within 48 hours
            hours_ago = random.random() * 48
            timestamp = base_time - timedelta(hours=hours_ago)
            
            # Create post
            source = random.choice(sources)
            post = SocialPost(
                id=f"post_{i}",
                source=source,
                ticker=ticker,
                text=text,
                timestamp=timestamp,
                author=f"user_{random.randint(1000, 9999)}",
                upvotes=random.randint(1, 500) if random.random() > 0.7 else random.randint(1, 50),
                comments=random.randint(0, 100)
            )
            
            self.add_post(post)
    
    def get_ticker_summary(self, ticker: str) -> Dict:
        """Get comprehensive summary for a ticker"""
        ts = self.calculate_aggregates(ticker, hours=24)
        
        # Determine sentiment label
        if ts.weighted_sentiment > 0.3:
            sentiment_label = 'BULLISH'
        elif ts.weighted_sentiment < -0.3:
            sentiment_label = 'BEARISH'
        else:
            sentiment_label = 'NEUTRAL'
        
        # Check for alerts
        alerts = self.get_all_alerts([ticker])
        
        return {
            'ticker': ticker,
            'sentiment_label': sentiment_label,
            'sentiment_score': round(ts.weighted_sentiment, 3),
            'mention_count': ts.mention_count,
            'mention_velocity': round(ts.mention_velocity, 2),
            'bullish_pct': round(ts.bullish_count / ts.mention_count * 100, 1) if ts.mention_count > 0 else 0,
            'bearish_pct': round(ts.bearish_count / ts.mention_count * 100, 1) if ts.mention_count > 0 else 0,
            'neutral_pct': round(ts.neutral_count / ts.mention_count * 100, 1) if ts.mention_count > 0 else 0,
            'momentum': round(ts.sentiment_momentum, 3),
            'sources': ts.sources,
            'top_posts': ts.top_posts[:3],
            'alerts': [{'type': a.alert_type, 'severity': a.severity, 'message': a.message} 
                      for a in alerts],
            'hourly_trend': ts.hourly_mentions[-12:] if ts.hourly_mentions else []
        }
    
    def save_data(self, filename: str = "sentiment_data.json") -> None:
        """Save sentiment data to file"""
        filepath = os.path.join(self.data_dir, filename)
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'post_count': len(self.posts),
            'tickers_tracked': list(self.ticker_data.keys()),
            'summaries': {ticker: self.get_ticker_summary(ticker) 
                         for ticker in self.ticker_data}
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def load_data(self, filename: str = "sentiment_data.json") -> Dict:
        """Load saved sentiment data"""
        filepath = os.path.join(self.data_dir, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}


# Test functions
def test_sentiment_analysis():
    """Test sentiment analysis"""
    agg = SocialSentimentAggregator()
    
    test_cases = [
        ("GME to the moon! Diamond hands! Buying more calls!", 1.0),
        ("This stock is crashing. Dump it. Complete scam.", -1.0),
        ("What's everyone thinking about this ticker?", 0.0),
    ]
    
    for text, expected_sign in test_cases:
        score, bullish, bearish = agg.analyze_sentiment(text)
        if expected_sign > 0:
            assert score > 0 or len(bullish) > 0, f"Expected bullish: {text}"
        elif expected_sign < 0:
            assert score < 0 or len(bearish) > 0, f"Expected bearish: {text}"
    
    print("[PASS] Sentiment analysis tests")

def test_ticker_extraction():
    """Test ticker extraction"""
    agg = SocialSentimentAggregator()
    
    text1 = "Buying $AAPL and $MSFT today"
    tickers1 = agg.extract_tickers(text1)
    assert 'AAPL' in tickers1, "Should find AAPL"
    assert 'MSFT' in tickers1, "Should find MSFT"
    
    text2 = "TSLA is going to moon"
    tickers2 = agg.extract_tickers(text2)
    assert 'TSLA' in tickers2, "Should find TSLA"
    
    print("[PASS] Ticker extraction tests")

def test_aggregation():
    """Test sentiment aggregation"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=100)
    
    # Check we have data
    assert len(agg.posts) == 100, "Should have 100 posts"
    assert len(agg.ticker_data) > 0, "Should have ticker data"
    
    # Check aggregation
    for ticker in list(agg.ticker_data.keys())[:3]:
        ts = agg.calculate_aggregates(ticker)
        assert ts.mention_count > 0, f"Should have mentions for {ticker}"
    
    print("[PASS] Aggregation tests")

def test_trending():
    """Test trending detection"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=200)
    
    trending = agg.get_trending(limit=5)
    assert len(trending) <= 5, "Should limit results"
    
    # Check sorted by velocity
    for i in range(len(trending) - 1):
        assert trending[i]['velocity'] >= trending[i+1]['velocity'], "Should be sorted by velocity"
    
    print("[PASS] Trending detection tests")

def test_alerts():
    """Test alert detection"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=300)
    
    alerts = agg.get_all_alerts()
    # Just verify no errors
    assert isinstance(alerts, list), "Should return list of alerts"
    
    print("[PASS] Alert detection tests")

def test_bullish_bearish():
    """Test bullish/bearish rankings"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=200)
    
    bullish = agg.get_most_bullish(min_mentions=3, limit=5)
    bearish = agg.get_most_bearish(min_mentions=3, limit=5)
    
    # Check sorted correctly
    if len(bullish) > 1:
        assert bullish[0]['sentiment'] >= bullish[-1]['sentiment'], "Bullish should be sorted desc"
    
    if len(bearish) > 1:
        assert bearish[0]['sentiment'] <= bearish[-1]['sentiment'], "Bearish should be sorted asc"
    
    print("[PASS] Bullish/bearish ranking tests")

def run_all_tests():
    """Run all tests"""
    print("\n=== Running Social Sentiment Tests ===\n")
    test_sentiment_analysis()
    test_ticker_extraction()
    test_aggregation()
    test_trending()
    test_alerts()
    test_bullish_bearish()
    print("\n=== All 6 tests passed! ===\n")

if __name__ == "__main__":
    run_all_tests()
