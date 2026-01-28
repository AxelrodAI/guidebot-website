#!/usr/bin/env python3
"""
News Sentiment Engine
Real-time NLP sentiment scoring with momentum tracking.
Aggregates news from multiple sources, tracks sentiment shifts, alerts on significant changes.

Uses free news sources and NLTK/TextBlob for sentiment analysis.
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'requests', 'beautifulsoup4'])
    import requests
    from bs4 import BeautifulSoup

try:
    from textblob import TextBlob
except ImportError:
    print("Installing TextBlob...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'textblob'])
    from textblob import TextBlob

# Paths
SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / "news_cache.json"
SENTIMENT_HISTORY_FILE = SCRIPT_DIR / "sentiment_history.json"
ALERTS_FILE = SCRIPT_DIR / "sentiment_alerts.json"


@dataclass
class NewsArticle:
    """Represents a news article with sentiment."""
    title: str
    url: str
    source: str
    published: str
    ticker: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str    # bearish/neutral/bullish
    summary: str = ""
    keywords: List[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SentimentSnapshot:
    """Point-in-time sentiment snapshot for a ticker."""
    ticker: str
    timestamp: str
    article_count: int
    avg_sentiment: float
    sentiment_label: str
    bullish_pct: float
    bearish_pct: float
    neutral_pct: float
    momentum: float  # Change from previous period
    articles: List[dict]


class NewsSentimentEngine:
    """Main sentiment engine class."""
    
    # Sentiment thresholds
    BULLISH_THRESHOLD = 0.1
    BEARISH_THRESHOLD = -0.1
    
    # Alert thresholds
    MOMENTUM_ALERT_THRESHOLD = 0.3  # 30% shift triggers alert
    EXTREME_SENTIMENT_THRESHOLD = 0.5  # Very bullish/bearish
    
    # News sources (free/public)
    NEWS_SOURCES = {
        "finviz": "https://finviz.com/quote.ashx?t={ticker}",
        "yahoo": "https://finance.yahoo.com/quote/{ticker}/news",
        "marketwatch": "https://www.marketwatch.com/investing/stock/{ticker}",
    }
    
    def __init__(self):
        self.cache = self._load_cache()
        self.history = self._load_history()
        self.alerts = []
    
    def _load_cache(self) -> dict:
        """Load cached news data."""
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"articles": {}, "lastUpdated": {}}
    
    def _save_cache(self):
        """Save news cache."""
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def _load_history(self) -> dict:
        """Load sentiment history."""
        if SENTIMENT_HISTORY_FILE.exists():
            with open(SENTIMENT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _save_history(self):
        """Save sentiment history."""
        with open(SENTIMENT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def _save_alerts(self, alerts: List[dict]):
        """Save alerts to file."""
        existing = []
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        existing.extend(alerts)
        # Keep last 100 alerts
        existing = existing[-100:]
        
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    
    def _article_hash(self, title: str, url: str) -> str:
        """Generate unique hash for article deduplication."""
        return hashlib.md5(f"{title}:{url}".encode()).hexdigest()[:12]
    
    def analyze_sentiment(self, text: str) -> tuple[float, str]:
        """
        Analyze sentiment of text using TextBlob.
        Returns (score, label) where score is -1 to 1.
        """
        if not text:
            return 0.0, "neutral"
        
        # Clean text
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        try:
            blob = TextBlob(text)
            score = blob.sentiment.polarity
            
            # Apply financial context adjustments
            score = self._apply_financial_context(text, score)
            
            # Classify
            if score >= self.BULLISH_THRESHOLD:
                label = "bullish"
            elif score <= self.BEARISH_THRESHOLD:
                label = "bearish"
            else:
                label = "neutral"
            
            return round(score, 3), label
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return 0.0, "neutral"
    
    def _apply_financial_context(self, text: str, base_score: float) -> float:
        """Adjust sentiment based on financial keywords."""
        text_lower = text.lower()
        
        # Bullish keywords
        bullish_words = [
            "beat", "beats", "exceeded", "outperform", "upgrade", "upgraded",
            "bullish", "surge", "surging", "soar", "soaring", "rally", "rallies",
            "breakout", "all-time high", "record high", "strong growth",
            "beat estimates", "raised guidance", "raised outlook",
            "buy rating", "strong buy", "overweight", "momentum"
        ]
        
        # Bearish keywords
        bearish_words = [
            "miss", "missed", "disappoints", "downgrade", "downgraded",
            "bearish", "plunge", "plunging", "crash", "crashes", "tumble",
            "breakdown", "all-time low", "record low", "weak", "weakness",
            "missed estimates", "lowered guidance", "cut outlook",
            "sell rating", "underperform", "underweight", "concern"
        ]
        
        # Count matches
        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)
        
        # Adjust score
        adjustment = (bullish_count - bearish_count) * 0.1
        adjusted = base_score + adjustment
        
        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, adjusted))
    
    def fetch_finviz_news(self, ticker: str) -> List[NewsArticle]:
        """Fetch news from Finviz."""
        articles = []
        url = self.NEWS_SOURCES["finviz"].format(ticker=ticker.upper())
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            news_table = soup.find('table', {'id': 'news-table'})
            
            if not news_table:
                return articles
            
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            for row in news_table.find_all('tr')[:20]:  # Limit to 20 recent articles
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_cell = cells[0].text.strip()
                    news_cell = cells[1]
                    
                    link = news_cell.find('a')
                    if link:
                        title = link.text.strip()
                        article_url = link.get('href', '')
                        source = news_cell.find('span')
                        source_name = source.text.strip() if source else "Unknown"
                        
                        # Parse date
                        if 'Today' in date_cell or len(date_cell.split()) == 1:
                            pub_date = current_date
                        else:
                            try:
                                pub_date = datetime.strptime(date_cell.split()[0], "%b-%d-%y").strftime("%Y-%m-%d")
                            except:
                                pub_date = current_date
                        
                        # Analyze sentiment
                        score, label = self.analyze_sentiment(title)
                        
                        articles.append(NewsArticle(
                            title=title,
                            url=article_url,
                            source=source_name,
                            published=pub_date,
                            ticker=ticker.upper(),
                            sentiment_score=score,
                            sentiment_label=label
                        ))
            
            print(f"  [FINVIZ] Fetched {len(articles)} articles for {ticker}")
            
        except Exception as e:
            print(f"  [FINVIZ] Error fetching {ticker}: {e}")
        
        return articles
    
    def fetch_rss_news(self, ticker: str) -> List[NewsArticle]:
        """Fetch news from Yahoo Finance RSS."""
        articles = []
        
        try:
            # Yahoo Finance RSS feed
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker.upper()}&region=US&lang=en-US"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item')
                
                for item in items[:15]:
                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    description = item.find('description')
                    
                    if title and link:
                        title_text = title.text.strip()
                        
                        # Combine title and description for better sentiment
                        full_text = title_text
                        if description:
                            full_text += " " + description.text.strip()
                        
                        score, label = self.analyze_sentiment(full_text)
                        
                        # Parse date
                        try:
                            parsed_date = datetime.strptime(
                                pub_date.text.strip()[:25], 
                                "%a, %d %b %Y %H:%M:%S"
                            ).strftime("%Y-%m-%d")
                        except:
                            parsed_date = datetime.now().strftime("%Y-%m-%d")
                        
                        articles.append(NewsArticle(
                            title=title_text,
                            url=link.text.strip(),
                            source="Yahoo Finance",
                            published=parsed_date,
                            ticker=ticker.upper(),
                            sentiment_score=score,
                            sentiment_label=label,
                            summary=description.text.strip()[:200] if description else ""
                        ))
                
                print(f"  [YAHOO] Fetched {len(articles)} articles for {ticker}")
        
        except Exception as e:
            print(f"  [YAHOO] Error fetching {ticker}: {e}")
        
        return articles
    
    def fetch_news(self, ticker: str, force_refresh: bool = False) -> List[NewsArticle]:
        """Fetch news from all sources for a ticker."""
        ticker = ticker.upper()
        cache_key = ticker
        
        # Check cache (valid for 30 minutes)
        if not force_refresh and cache_key in self.cache.get("lastUpdated", {}):
            last_update = datetime.fromisoformat(self.cache["lastUpdated"][cache_key])
            if (datetime.now() - last_update).total_seconds() < 1800:  # 30 min
                cached_articles = self.cache.get("articles", {}).get(cache_key, [])
                if cached_articles:
                    print(f"  [CACHE] Using cached data for {ticker}")
                    return [NewsArticle(**a) for a in cached_articles]
        
        print(f"\nFetching news for {ticker}...")
        all_articles = []
        seen_hashes = set()
        
        # Fetch from multiple sources
        sources = [
            self.fetch_finviz_news,
            self.fetch_rss_news,
        ]
        
        for fetch_func in sources:
            try:
                articles = fetch_func(ticker)
                for article in articles:
                    h = self._article_hash(article.title, article.url)
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        all_articles.append(article)
            except Exception as e:
                print(f"  Error in {fetch_func.__name__}: {e}")
        
        # Cache results
        if "articles" not in self.cache:
            self.cache["articles"] = {}
        if "lastUpdated" not in self.cache:
            self.cache["lastUpdated"] = {}
        
        self.cache["articles"][cache_key] = [a.to_dict() for a in all_articles]
        self.cache["lastUpdated"][cache_key] = datetime.now().isoformat()
        self._save_cache()
        
        return all_articles
    
    def calculate_snapshot(self, ticker: str, articles: List[NewsArticle]) -> SentimentSnapshot:
        """Calculate sentiment snapshot from articles."""
        ticker = ticker.upper()
        
        if not articles:
            return SentimentSnapshot(
                ticker=ticker,
                timestamp=datetime.now().isoformat(),
                article_count=0,
                avg_sentiment=0.0,
                sentiment_label="neutral",
                bullish_pct=0.0,
                bearish_pct=0.0,
                neutral_pct=100.0,
                momentum=0.0,
                articles=[]
            )
        
        # Calculate stats
        scores = [a.sentiment_score for a in articles]
        avg_sentiment = sum(scores) / len(scores)
        
        bullish_count = sum(1 for a in articles if a.sentiment_label == "bullish")
        bearish_count = sum(1 for a in articles if a.sentiment_label == "bearish")
        neutral_count = sum(1 for a in articles if a.sentiment_label == "neutral")
        total = len(articles)
        
        bullish_pct = (bullish_count / total) * 100
        bearish_pct = (bearish_count / total) * 100
        neutral_pct = (neutral_count / total) * 100
        
        # Overall label
        if avg_sentiment >= self.BULLISH_THRESHOLD:
            label = "bullish"
        elif avg_sentiment <= self.BEARISH_THRESHOLD:
            label = "bearish"
        else:
            label = "neutral"
        
        # Calculate momentum (change from previous snapshot)
        momentum = 0.0
        if ticker in self.history and self.history[ticker]:
            prev_snapshots = self.history[ticker]
            if prev_snapshots:
                prev_sentiment = prev_snapshots[-1].get("avg_sentiment", 0)
                momentum = avg_sentiment - prev_sentiment
        
        return SentimentSnapshot(
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            article_count=len(articles),
            avg_sentiment=round(avg_sentiment, 3),
            sentiment_label=label,
            bullish_pct=round(bullish_pct, 1),
            bearish_pct=round(bearish_pct, 1),
            neutral_pct=round(neutral_pct, 1),
            momentum=round(momentum, 3),
            articles=[a.to_dict() for a in articles[:10]]  # Keep top 10
        )
    
    def check_alerts(self, snapshot: SentimentSnapshot) -> List[dict]:
        """Check for alert conditions."""
        alerts = []
        ticker = snapshot.ticker
        
        # Momentum alert
        if abs(snapshot.momentum) >= self.MOMENTUM_ALERT_THRESHOLD:
            direction = "bullish" if snapshot.momentum > 0 else "bearish"
            alerts.append({
                "type": "MOMENTUM_SHIFT",
                "ticker": ticker,
                "severity": "high",
                "message": f"Significant {direction} sentiment shift: {snapshot.momentum:+.1%}",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "momentum": snapshot.momentum,
                    "current_sentiment": snapshot.avg_sentiment,
                    "direction": direction
                }
            })
        
        # Extreme sentiment alert
        if abs(snapshot.avg_sentiment) >= self.EXTREME_SENTIMENT_THRESHOLD:
            label = snapshot.sentiment_label
            alerts.append({
                "type": "EXTREME_SENTIMENT",
                "ticker": ticker,
                "severity": "medium",
                "message": f"Extreme {label} sentiment detected: {snapshot.avg_sentiment:.2f}",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "sentiment": snapshot.avg_sentiment,
                    "bullish_pct": snapshot.bullish_pct,
                    "bearish_pct": snapshot.bearish_pct
                }
            })
        
        # High bearish consensus alert
        if snapshot.bearish_pct >= 70:
            alerts.append({
                "type": "BEARISH_CONSENSUS",
                "ticker": ticker,
                "severity": "high",
                "message": f"High bearish consensus: {snapshot.bearish_pct:.0f}% negative articles",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "bearish_pct": snapshot.bearish_pct,
                    "article_count": snapshot.article_count
                }
            })
        
        # High bullish consensus alert
        if snapshot.bullish_pct >= 70:
            alerts.append({
                "type": "BULLISH_CONSENSUS",
                "ticker": ticker,
                "severity": "medium",
                "message": f"High bullish consensus: {snapshot.bullish_pct:.0f}% positive articles",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "bullish_pct": snapshot.bullish_pct,
                    "article_count": snapshot.article_count
                }
            })
        
        if alerts:
            self._save_alerts(alerts)
        
        return alerts
    
    def update_history(self, snapshot: SentimentSnapshot):
        """Add snapshot to history."""
        ticker = snapshot.ticker
        
        if ticker not in self.history:
            self.history[ticker] = []
        
        # Store snapshot (without full article list for space)
        history_entry = {
            "timestamp": snapshot.timestamp,
            "article_count": snapshot.article_count,
            "avg_sentiment": snapshot.avg_sentiment,
            "sentiment_label": snapshot.sentiment_label,
            "bullish_pct": snapshot.bullish_pct,
            "bearish_pct": snapshot.bearish_pct,
            "neutral_pct": snapshot.neutral_pct,
            "momentum": snapshot.momentum
        }
        
        self.history[ticker].append(history_entry)
        
        # Keep last 30 days of history (assuming ~4 updates per day)
        self.history[ticker] = self.history[ticker][-120:]
        
        self._save_history()
    
    def analyze_ticker(self, ticker: str, force_refresh: bool = False) -> dict:
        """Full analysis pipeline for a ticker."""
        ticker = ticker.upper()
        
        # Fetch news
        articles = self.fetch_news(ticker, force_refresh)
        
        # Calculate snapshot
        snapshot = self.calculate_snapshot(ticker, articles)
        
        # Check for alerts
        alerts = self.check_alerts(snapshot)
        
        # Update history
        self.update_history(snapshot)
        
        return {
            "snapshot": asdict(snapshot) if hasattr(snapshot, '__dataclass_fields__') else snapshot.__dict__,
            "alerts": alerts,
            "article_count": len(articles)
        }
    
    def analyze_multiple(self, tickers: List[str], force_refresh: bool = False) -> dict:
        """Analyze multiple tickers."""
        results = {}
        all_alerts = []
        
        for ticker in tickers:
            print(f"\n{'='*50}")
            result = self.analyze_ticker(ticker, force_refresh)
            results[ticker.upper()] = result["snapshot"]
            all_alerts.extend(result["alerts"])
        
        return {
            "results": results,
            "alerts": all_alerts,
            "summary": self._generate_summary(results)
        }
    
    def _generate_summary(self, results: dict) -> dict:
        """Generate summary across multiple tickers."""
        if not results:
            return {}
        
        sentiments = [r["avg_sentiment"] for r in results.values()]
        
        # Sort by sentiment
        sorted_tickers = sorted(
            results.items(),
            key=lambda x: x[1]["avg_sentiment"],
            reverse=True
        )
        
        most_bullish = sorted_tickers[0] if sorted_tickers else None
        most_bearish = sorted_tickers[-1] if sorted_tickers else None
        
        return {
            "ticker_count": len(results),
            "avg_sentiment": round(sum(sentiments) / len(sentiments), 3),
            "most_bullish": {
                "ticker": most_bullish[0],
                "sentiment": most_bullish[1]["avg_sentiment"]
            } if most_bullish else None,
            "most_bearish": {
                "ticker": most_bearish[0],
                "sentiment": most_bearish[1]["avg_sentiment"]
            } if most_bearish else None,
            "bullish_count": sum(1 for r in results.values() if r["sentiment_label"] == "bullish"),
            "bearish_count": sum(1 for r in results.values() if r["sentiment_label"] == "bearish"),
            "neutral_count": sum(1 for r in results.values() if r["sentiment_label"] == "neutral"),
        }
    
    def get_history(self, ticker: str, days: int = 7) -> List[dict]:
        """Get sentiment history for a ticker."""
        ticker = ticker.upper()
        if ticker not in self.history:
            return []
        
        cutoff = datetime.now() - timedelta(days=days)
        
        return [
            h for h in self.history[ticker]
            if datetime.fromisoformat(h["timestamp"]) > cutoff
        ]
    
    def get_momentum_leaders(self, tickers: List[str]) -> dict:
        """Find tickers with biggest sentiment momentum."""
        results = {}
        
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker in self.history and len(self.history[ticker]) >= 2:
                recent = self.history[ticker][-1]
                prev = self.history[ticker][-2]
                momentum = recent["avg_sentiment"] - prev["avg_sentiment"]
                results[ticker] = {
                    "momentum": momentum,
                    "current": recent["avg_sentiment"],
                    "previous": prev["avg_sentiment"],
                    "label": recent["sentiment_label"]
                }
        
        # Sort by absolute momentum
        sorted_results = sorted(
            results.items(),
            key=lambda x: abs(x[1]["momentum"]),
            reverse=True
        )
        
        return {
            "improving": [
                {"ticker": t, **d} 
                for t, d in sorted_results if d["momentum"] > 0
            ][:5],
            "declining": [
                {"ticker": t, **d}
                for t, d in sorted_results if d["momentum"] < 0
            ][:5]
        }


def print_snapshot(snapshot: dict):
    """Pretty print a sentiment snapshot."""
    print(f"\n{'='*60}")
    print(f"SENTIMENT: {snapshot['ticker']}")
    print(f"{'='*60}")
    print(f"  Articles Analyzed: {snapshot['article_count']}")
    print(f"  Average Sentiment: {snapshot['avg_sentiment']:.3f} ({snapshot['sentiment_label'].upper()})")
    print(f"  Momentum: {snapshot['momentum']:+.3f}")
    print(f"\n  Distribution:")
    print(f"    Bullish:  {snapshot['bullish_pct']:5.1f}% {'#' * int(snapshot['bullish_pct'] / 5)}")
    print(f"    Neutral:  {snapshot['neutral_pct']:5.1f}% {'#' * int(snapshot['neutral_pct'] / 5)}")
    print(f"    Bearish:  {snapshot['bearish_pct']:5.1f}% {'#' * int(snapshot['bearish_pct'] / 5)}")
    
    if snapshot.get("articles"):
        print(f"\n  Recent Headlines:")
        for i, article in enumerate(snapshot["articles"][:5], 1):
            marker = "[+]" if article["sentiment_label"] == "bullish" else "[-]" if article["sentiment_label"] == "bearish" else "[=]"
            print(f"    {marker} {article['title'][:70]}...")
            print(f"       Score: {article['sentiment_score']:.2f} | {article['source']} | {article['published']}")


def print_alerts(alerts: List[dict]):
    """Pretty print alerts."""
    if not alerts:
        return
    
    print(f"\n{'!'*60}")
    print("ALERTS")
    print(f"{'!'*60}")
    
    for alert in alerts:
        severity_icon = "[!!!]" if alert["severity"] == "high" else "[!!]"
        print(f"  {severity_icon} [{alert['type']}] {alert['ticker']}")
        print(f"     {alert['message']}")


# Example usage
if __name__ == "__main__":
    engine = NewsSentimentEngine()
    
    # Analyze a single ticker
    result = engine.analyze_ticker("NVDA")
    print_snapshot(result["snapshot"])
    print_alerts(result["alerts"])
