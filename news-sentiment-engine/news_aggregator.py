"""
News Aggregator - Multi-source news fetching
Supports: NewsAPI, Finnhub, Alpha Vantage, RSS feeds, Polygon.io
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# Optional: requests for better HTTP handling
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class RawNewsItem:
    """Raw news item from any source"""
    ticker: str
    title: str
    description: str
    source: str
    source_api: str  # Which API it came from
    url: str
    published_at: datetime
    raw_data: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            'ticker': self.ticker,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'source_api': self.source_api,
            'url': self.url,
            'published_at': self.published_at.isoformat()
        }


class NewsAggregator:
    """Aggregate news from multiple sources"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # API keys from config or environment
        self.newsapi_key = self.config.get('newsapi_key') or os.environ.get('NEWSAPI_KEY')
        self.finnhub_key = self.config.get('finnhub_key') or os.environ.get('FINNHUB_API_KEY')
        self.alphavantage_key = self.config.get('alphavantage_key') or os.environ.get('ALPHA_VANTAGE_KEY')
        self.polygon_key = self.config.get('polygon_key') or os.environ.get('POLYGON_API_KEY')
        
        # Rate limiting
        self.last_request_time = {}
        self.rate_limits = {
            'newsapi': 1.0,      # 1 second between requests
            'finnhub': 0.5,     # 500ms
            'alphavantage': 12.0,  # 5 requests/minute
            'polygon': 0.1,     # 10 requests/second
            'rss': 0.5
        }
        
        # Cache
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _rate_limit(self, source: str):
        """Enforce rate limiting"""
        if source in self.last_request_time:
            elapsed = time.time() - self.last_request_time[source]
            wait_time = self.rate_limits.get(source, 1.0) - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
        self.last_request_time[source] = time.time()
    
    def _http_get(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP GET request"""
        try:
            if REQUESTS_AVAILABLE:
                resp = requests.get(url, headers=headers or {}, timeout=10)
                resp.raise_for_status()
                return resp.json()
            else:
                req = urllib.request.Request(url, headers=headers or {})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode())
        except Exception as e:
            print(f"HTTP error for {url}: {e}")
            return None
    
    def _get_cached(self, key: str) -> Optional[List[RawNewsItem]]:
        """Get cached results if still valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: List[RawNewsItem]):
        """Cache results"""
        self.cache[key] = (data, time.time())
    
    def fetch_newsapi(self, ticker: str, days_back: int = 3) -> List[RawNewsItem]:
        """
        Fetch from NewsAPI.org
        https://newsapi.org/docs/endpoints/everything
        """
        if not self.newsapi_key:
            return []
        
        cache_key = f"newsapi:{ticker}:{days_back}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        self._rate_limit('newsapi')
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        # Search for company news
        query = f"{ticker} stock OR {ticker} shares OR {ticker} earnings"
        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={urllib.parse.quote(query)}&"
            f"from={from_date}&"
            f"language=en&"
            f"sortBy=publishedAt&"
            f"pageSize=50&"
            f"apiKey={self.newsapi_key}"
        )
        
        data = self._http_get(url)
        if not data or data.get('status') != 'ok':
            return []
        
        items = []
        for article in data.get('articles', []):
            try:
                published = datetime.fromisoformat(
                    article['publishedAt'].replace('Z', '+00:00')
                )
                items.append(RawNewsItem(
                    ticker=ticker.upper(),
                    title=article.get('title', ''),
                    description=article.get('description', ''),
                    source=article.get('source', {}).get('name', 'Unknown'),
                    source_api='newsapi',
                    url=article.get('url', ''),
                    published_at=published,
                    raw_data=article
                ))
            except Exception as e:
                continue
        
        self._set_cache(cache_key, items)
        return items
    
    def fetch_finnhub(self, ticker: str, days_back: int = 3) -> List[RawNewsItem]:
        """
        Fetch from Finnhub
        https://finnhub.io/docs/api/company-news
        """
        if not self.finnhub_key:
            return []
        
        cache_key = f"finnhub:{ticker}:{days_back}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        self._rate_limit('finnhub')
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        url = (
            f"https://finnhub.io/api/v1/company-news?"
            f"symbol={ticker.upper()}&"
            f"from={from_date}&"
            f"to={to_date}&"
            f"token={self.finnhub_key}"
        )
        
        data = self._http_get(url)
        if not data:
            return []
        
        items = []
        for article in data:
            try:
                # Finnhub uses Unix timestamp
                published = datetime.fromtimestamp(article.get('datetime', 0))
                items.append(RawNewsItem(
                    ticker=ticker.upper(),
                    title=article.get('headline', ''),
                    description=article.get('summary', ''),
                    source=article.get('source', 'Finnhub'),
                    source_api='finnhub',
                    url=article.get('url', ''),
                    published_at=published,
                    raw_data=article
                ))
            except Exception:
                continue
        
        self._set_cache(cache_key, items)
        return items
    
    def fetch_alphavantage(self, ticker: str) -> List[RawNewsItem]:
        """
        Fetch from Alpha Vantage News Sentiment API
        https://www.alphavantage.co/documentation/#news-sentiment
        """
        if not self.alphavantage_key:
            return []
        
        cache_key = f"alphavantage:{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        self._rate_limit('alphavantage')
        
        url = (
            f"https://www.alphavantage.co/query?"
            f"function=NEWS_SENTIMENT&"
            f"tickers={ticker.upper()}&"
            f"limit=50&"
            f"apikey={self.alphavantage_key}"
        )
        
        data = self._http_get(url)
        if not data or 'feed' not in data:
            return []
        
        items = []
        for article in data.get('feed', []):
            try:
                # Format: 20231115T143000
                time_str = article.get('time_published', '')
                published = datetime.strptime(time_str[:15], '%Y%m%dT%H%M%S')
                
                items.append(RawNewsItem(
                    ticker=ticker.upper(),
                    title=article.get('title', ''),
                    description=article.get('summary', ''),
                    source=article.get('source', 'Alpha Vantage'),
                    source_api='alphavantage',
                    url=article.get('url', ''),
                    published_at=published,
                    raw_data=article
                ))
            except Exception:
                continue
        
        self._set_cache(cache_key, items)
        return items
    
    def fetch_polygon(self, ticker: str, days_back: int = 3) -> List[RawNewsItem]:
        """
        Fetch from Polygon.io
        https://polygon.io/docs/stocks/get_v2_reference_news
        """
        if not self.polygon_key:
            return []
        
        cache_key = f"polygon:{ticker}:{days_back}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        self._rate_limit('polygon')
        
        url = (
            f"https://api.polygon.io/v2/reference/news?"
            f"ticker={ticker.upper()}&"
            f"limit=50&"
            f"apiKey={self.polygon_key}"
        )
        
        data = self._http_get(url)
        if not data or 'results' not in data:
            return []
        
        items = []
        for article in data.get('results', []):
            try:
                published = datetime.fromisoformat(
                    article['published_utc'].replace('Z', '+00:00')
                )
                items.append(RawNewsItem(
                    ticker=ticker.upper(),
                    title=article.get('title', ''),
                    description=article.get('description', ''),
                    source=article.get('publisher', {}).get('name', 'Polygon'),
                    source_api='polygon',
                    url=article.get('article_url', ''),
                    published_at=published,
                    raw_data=article
                ))
            except Exception:
                continue
        
        self._set_cache(cache_key, items)
        return items
    
    def fetch_rss(self, ticker: str, rss_feeds: Optional[List[str]] = None) -> List[RawNewsItem]:
        """
        Fetch from RSS feeds
        Default financial RSS feeds
        """
        default_feeds = [
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
            f"https://www.nasdaq.com/feed/rssoutbound?symbol={ticker}",
        ]
        
        feeds = rss_feeds or default_feeds
        
        cache_key = f"rss:{ticker}:{hash(tuple(feeds))}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        items = []
        for feed_url in feeds:
            self._rate_limit('rss')
            try:
                if REQUESTS_AVAILABLE:
                    resp = requests.get(feed_url, timeout=10)
                    content = resp.content
                else:
                    with urllib.request.urlopen(feed_url, timeout=10) as resp:
                        content = resp.read()
                
                root = ET.fromstring(content)
                
                # Handle RSS 2.0
                for item in root.findall('.//item'):
                    title = item.find('title')
                    desc = item.find('description')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    
                    if title is not None:
                        try:
                            # Parse RSS date format
                            date_str = pub_date.text if pub_date is not None else ''
                            # Try common formats
                            for fmt in ['%a, %d %b %Y %H:%M:%S %z', 
                                       '%a, %d %b %Y %H:%M:%S GMT']:
                                try:
                                    published = datetime.strptime(date_str, fmt)
                                    break
                                except:
                                    published = datetime.now()
                            
                            items.append(RawNewsItem(
                                ticker=ticker.upper(),
                                title=title.text or '',
                                description=(desc.text or '')[:500],
                                source=feed_url.split('/')[2],  # Domain as source
                                source_api='rss',
                                url=link.text if link is not None else '',
                                published_at=published
                            ))
                        except Exception:
                            continue
                
            except Exception as e:
                print(f"RSS error for {feed_url}: {e}")
                continue
        
        self._set_cache(cache_key, items)
        return items
    
    def fetch_all_sources(self, ticker: str, days_back: int = 3) -> List[RawNewsItem]:
        """
        Aggregate news from all available sources
        Deduplicates by title similarity
        """
        all_items = []
        
        # Fetch from all sources
        if self.newsapi_key:
            all_items.extend(self.fetch_newsapi(ticker, days_back))
        
        if self.finnhub_key:
            all_items.extend(self.fetch_finnhub(ticker, days_back))
        
        if self.alphavantage_key:
            all_items.extend(self.fetch_alphavantage(ticker))
        
        if self.polygon_key:
            all_items.extend(self.fetch_polygon(ticker, days_back))
        
        # Always try RSS
        all_items.extend(self.fetch_rss(ticker))
        
        # Deduplicate by title hash
        seen_titles = set()
        unique_items = []
        
        for item in all_items:
            # Normalize title for comparison
            title_key = hashlib.md5(
                item.title.lower().strip()[:50].encode()
            ).hexdigest()
            
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)
        
        # Sort by publish date (newest first)
        unique_items.sort(key=lambda x: x.published_at, reverse=True)
        
        return unique_items
    
    def get_api_status(self) -> Dict[str, str]:
        """Check which APIs are configured"""
        return {
            'newsapi': 'configured' if self.newsapi_key else 'not configured',
            'finnhub': 'configured' if self.finnhub_key else 'not configured',
            'alphavantage': 'configured' if self.alphavantage_key else 'not configured',
            'polygon': 'configured' if self.polygon_key else 'not configured',
            'rss': 'always available'
        }


class MarketNewsScanner:
    """
    Scan for market-wide news across multiple tickers
    """
    
    def __init__(self, aggregator: Optional[NewsAggregator] = None):
        self.aggregator = aggregator or NewsAggregator()
    
    def scan_watchlist(self, tickers: List[str], 
                       days_back: int = 1) -> Dict[str, List[RawNewsItem]]:
        """
        Scan all tickers in watchlist for news
        Returns dict of ticker -> news items
        """
        results = {}
        
        for ticker in tickers:
            items = self.aggregator.fetch_all_sources(ticker, days_back)
            if items:
                results[ticker] = items
        
        return results
    
    def get_breaking_news(self, tickers: List[str],
                          hours_back: int = 1) -> List[RawNewsItem]:
        """Get very recent news (potential market movers)"""
        cutoff = datetime.now() - timedelta(hours=hours_back)
        
        all_breaking = []
        for ticker in tickers:
            items = self.aggregator.fetch_all_sources(ticker, days_back=1)
            breaking = [item for item in items if item.published_at >= cutoff]
            all_breaking.extend(breaking)
        
        # Sort by recency
        all_breaking.sort(key=lambda x: x.published_at, reverse=True)
        return all_breaking
    
    def get_sector_news(self, sector_tickers: Dict[str, List[str]],
                        days_back: int = 1) -> Dict[str, List[RawNewsItem]]:
        """
        Get news organized by sector
        sector_tickers: {'Technology': ['AAPL', 'MSFT'], 'Healthcare': ['JNJ', 'PFE']}
        """
        sector_news = {}
        
        for sector, tickers in sector_tickers.items():
            sector_items = []
            for ticker in tickers:
                items = self.aggregator.fetch_all_sources(ticker, days_back)
                sector_items.extend(items)
            
            # Deduplicate across sector
            seen = set()
            unique = []
            for item in sector_items:
                key = item.title[:50]
                if key not in seen:
                    seen.add(key)
                    unique.append(item)
            
            sector_news[sector] = sorted(unique, key=lambda x: x.published_at, reverse=True)
        
        return sector_news


# Utility functions

def create_aggregator(config: Optional[Dict] = None) -> NewsAggregator:
    """Create configured aggregator"""
    return NewsAggregator(config)


def create_scanner(config: Optional[Dict] = None) -> MarketNewsScanner:
    """Create market scanner"""
    return MarketNewsScanner(NewsAggregator(config))


if __name__ == "__main__":
    # Demo
    aggregator = NewsAggregator()
    
    print("API Status:")
    for api, status in aggregator.get_api_status().items():
        print(f"  {api}: {status}")
    
    print("\nFetching news for AAPL...")
    items = aggregator.fetch_all_sources('AAPL', days_back=1)
    
    print(f"Found {len(items)} articles:")
    for item in items[:5]:
        print(f"  [{item.source}] {item.title[:60]}...")
