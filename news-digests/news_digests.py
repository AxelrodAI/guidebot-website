#!/usr/bin/env python3
"""
Financial News Alert Digests
Aggregate watchlist news, summarize material events.
Built by PM3 (Backend/Data Builder)
"""

import argparse
import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.parse
import html

DATA_DIR = Path(__file__).parent / "data"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
NEWS_FILE = DATA_DIR / "news_cache.json"
ALERTS_FILE = DATA_DIR / "alerts.json"
DIGESTS_FILE = DATA_DIR / "digests.json"
CONFIG_FILE = DATA_DIR / "config.json"


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(filepath: Path, default=None):
    """Load JSON file or return default."""
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(filepath: Path, data):
    """Save data to JSON file."""
    ensure_data_dir()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


def get_config() -> Dict:
    """Get configuration with defaults."""
    config = load_json(CONFIG_FILE, {})
    defaults = {
        "alert_on_high_priority": True,
        "digest_frequency": "daily",  # daily, weekly
        "news_retention_days": 30,
        "min_priority_for_alert": 4,
        "sources": ["general", "sec", "press_releases"],
        "categories_enabled": ["earnings", "merger", "fda", "legal", "management", "guidance", "dividend", "buyback"]
    }
    for k, v in defaults.items():
        if k not in config:
            config[k] = v
    return config


# Material Event Categories and Keywords
EVENT_CATEGORIES = {
    "earnings": {
        "keywords": ["earnings", "revenue", "eps", "beat", "miss", "quarterly results", "q1", "q2", "q3", "q4", "annual report", "profit", "net income", "guidance"],
        "priority": 5,
        "icon": "[EARN]"
    },
    "merger": {
        "keywords": ["merger", "acquisition", "acquire", "buyout", "takeover", "deal", "m&a", "purchase agreement", "tender offer", "combine"],
        "priority": 5,
        "icon": "[M&A]"
    },
    "fda": {
        "keywords": ["fda", "approval", "clinical trial", "phase 3", "phase 2", "drug", "therapy", "pdufa", "nda", "breakthrough therapy", "fast track"],
        "priority": 5,
        "icon": "[FDA]"
    },
    "legal": {
        "keywords": ["lawsuit", "litigation", "settlement", "sec investigation", "doj", "subpoena", "class action", "probe", "regulatory", "antitrust"],
        "priority": 4,
        "icon": "[LEGAL]"
    },
    "management": {
        "keywords": ["ceo", "cfo", "cto", "executive", "resign", "appoint", "hire", "departure", "leadership", "board member", "director"],
        "priority": 4,
        "icon": "[MGMT]"
    },
    "guidance": {
        "keywords": ["guidance", "outlook", "forecast", "raise", "lower", "reaffirm", "expect", "project", "full year", "upgrade", "downgrade"],
        "priority": 4,
        "icon": "[GUIDE]"
    },
    "dividend": {
        "keywords": ["dividend", "payout", "distribution", "yield", "special dividend", "ex-dividend", "declared"],
        "priority": 3,
        "icon": "[DIV]"
    },
    "buyback": {
        "keywords": ["buyback", "repurchase", "share repurchase", "stock buyback", "authorization", "repurchase program"],
        "priority": 3,
        "icon": "[BUY]"
    },
    "analyst": {
        "keywords": ["upgrade", "downgrade", "price target", "analyst", "rating", "overweight", "underweight", "buy rating", "sell rating", "hold"],
        "priority": 3,
        "icon": "[ANLY]"
    },
    "filing": {
        "keywords": ["13f", "10-k", "10-q", "8-k", "s-1", "ipo", "prospectus", "form 4", "insider", "sec filing"],
        "priority": 3,
        "icon": "[FILE]"
    },
    "product": {
        "keywords": ["launch", "new product", "release", "unveil", "announcement", "partnership", "contract", "deal"],
        "priority": 2,
        "icon": "[PROD]"
    }
}


def generate_news_id(article: Dict) -> str:
    """Generate unique ID for news article."""
    content = f"{article.get('title', '')}{article.get('source', '')}{article.get('published', '')}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def categorize_article(article: Dict, config: Dict) -> Tuple[List[str], int]:
    """Categorize article and determine priority."""
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    combined = f"{title} {summary}"
    
    categories = []
    max_priority = 1
    enabled = config.get('categories_enabled', list(EVENT_CATEGORIES.keys()))
    
    for cat_name, cat_info in EVENT_CATEGORIES.items():
        if cat_name not in enabled:
            continue
        for keyword in cat_info['keywords']:
            if keyword in combined:
                if cat_name not in categories:
                    categories.append(cat_name)
                    max_priority = max(max_priority, cat_info['priority'])
                break
    
    if not categories:
        categories = ['general']
    
    return categories, max_priority


def get_watchlist() -> Dict:
    """Get watchlist with metadata."""
    watchlist = load_json(WATCHLIST_FILE, {"tickers": {}})
    return watchlist


def add_to_watchlist(ticker: str, name: str = None, notes: str = None) -> Dict:
    """Add ticker to watchlist."""
    watchlist = get_watchlist()
    ticker = ticker.upper()
    
    if ticker not in watchlist['tickers']:
        watchlist['tickers'][ticker] = {
            "name": name or ticker,
            "added": datetime.now().isoformat(),
            "notes": notes or "",
            "last_news": None,
            "news_count": 0
        }
        save_json(WATCHLIST_FILE, watchlist)
    return watchlist['tickers'][ticker]


def remove_from_watchlist(ticker: str) -> bool:
    """Remove ticker from watchlist."""
    watchlist = get_watchlist()
    ticker = ticker.upper()
    
    if ticker in watchlist['tickers']:
        del watchlist['tickers'][ticker]
        save_json(WATCHLIST_FILE, watchlist)
        return True
    return False


def fetch_news_for_ticker(ticker: str, days: int = 7) -> List[Dict]:
    """
    Fetch news for a ticker. 
    In production, integrate with news APIs (NewsAPI, Alpha Vantage, Polygon, etc.)
    This version generates simulated news for demonstration.
    """
    # Simulated news data - in production, replace with actual API calls
    simulated_templates = [
        {"title": f"{ticker} Reports Strong Q4 Earnings, Beats Estimates", "category": "earnings"},
        {"title": f"Analysts Raise Price Target on {ticker} Following Results", "category": "analyst"},
        {"title": f"{ticker} Announces $500M Share Repurchase Program", "category": "buyback"},
        {"title": f"{ticker} CEO to Step Down, CFO Named Interim Chief", "category": "management"},
        {"title": f"{ticker} Receives FDA Approval for New Treatment", "category": "fda"},
        {"title": f"{ticker} in Talks for Potential Acquisition", "category": "merger"},
        {"title": f"{ticker} Raises Full-Year Guidance on Strong Demand", "category": "guidance"},
        {"title": f"{ticker} Declares Special Dividend of $2.00 Per Share", "category": "dividend"},
        {"title": f"{ticker} Faces Class Action Lawsuit Over Securities Fraud", "category": "legal"},
        {"title": f"{ticker} Files 10-K Annual Report with SEC", "category": "filing"},
        {"title": f"{ticker} Launches New Product Line for 2026", "category": "product"},
    ]
    
    # Generate deterministic "random" news based on ticker
    import random
    random.seed(hash(ticker + datetime.now().strftime("%Y-%m-%d")))
    
    news_items = []
    num_items = random.randint(2, 6)
    
    for i in range(num_items):
        template = random.choice(simulated_templates)
        pub_date = datetime.now() - timedelta(hours=random.randint(1, days * 24))
        
        article = {
            "id": generate_news_id({"title": template["title"], "source": "NewsWire", "published": pub_date.isoformat()}),
            "ticker": ticker,
            "title": template["title"],
            "summary": f"Full article about {ticker}'s recent {template['category']} developments...",
            "source": random.choice(["Reuters", "Bloomberg", "CNBC", "WSJ", "MarketWatch", "Seeking Alpha"]),
            "url": f"https://news.example.com/{ticker.lower()}/{i+1}",
            "published": pub_date.isoformat(),
            "fetched": datetime.now().isoformat()
        }
        news_items.append(article)
    
    return news_items


def fetch_all_watchlist_news(days: int = 7) -> Dict[str, List[Dict]]:
    """Fetch news for all tickers in watchlist."""
    watchlist = get_watchlist()
    config = get_config()
    all_news = {}
    
    for ticker in watchlist.get('tickers', {}):
        news = fetch_news_for_ticker(ticker, days)
        # Categorize each article
        for article in news:
            categories, priority = categorize_article(article, config)
            article['categories'] = categories
            article['priority'] = priority
            article['icons'] = [EVENT_CATEGORIES.get(c, {}).get('icon', '') for c in categories if c != 'general']
        all_news[ticker] = news
    
    return all_news


def cache_news(news: Dict[str, List[Dict]]):
    """Cache fetched news."""
    cache = load_json(NEWS_FILE, {"articles": [], "last_fetch": None})
    existing_ids = {a.get('id') for a in cache.get('articles', [])}
    
    new_count = 0
    for ticker, articles in news.items():
        for article in articles:
            if article.get('id') not in existing_ids:
                cache['articles'].append(article)
                existing_ids.add(article.get('id'))
                new_count += 1
    
    cache['last_fetch'] = datetime.now().isoformat()
    
    # Prune old articles
    config = get_config()
    retention_days = config.get('news_retention_days', 30)
    cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
    cache['articles'] = [a for a in cache['articles'] if a.get('fetched', '') > cutoff]
    
    save_json(NEWS_FILE, cache)
    return new_count


def get_cached_news(ticker: str = None, days: int = 7, category: str = None, min_priority: int = 1) -> List[Dict]:
    """Get news from cache with filters."""
    cache = load_json(NEWS_FILE, {"articles": []})
    articles = cache.get('articles', [])
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    filtered = []
    for article in articles:
        if article.get('published', '') < cutoff:
            continue
        if ticker and article.get('ticker', '').upper() != ticker.upper():
            continue
        if category and category not in article.get('categories', []):
            continue
        if article.get('priority', 1) < min_priority:
            continue
        filtered.append(article)
    
    # Sort by date, newest first
    filtered.sort(key=lambda x: x.get('published', ''), reverse=True)
    return filtered


def generate_digest(days: int = 1, format_type: str = "text") -> Dict:
    """Generate a news digest."""
    config = get_config()
    watchlist = get_watchlist()
    
    # Fetch fresh news
    all_news = fetch_all_watchlist_news(days)
    cache_news(all_news)
    
    # Get high-priority news
    high_priority_news = get_cached_news(days=days, min_priority=4)
    all_recent_news = get_cached_news(days=days)
    
    # Group by category
    by_category = defaultdict(list)
    for article in all_recent_news:
        for cat in article.get('categories', ['general']):
            by_category[cat].append(article)
    
    # Group by ticker
    by_ticker = defaultdict(list)
    for article in all_recent_news:
        by_ticker[article.get('ticker', 'UNKNOWN')].append(article)
    
    digest = {
        "id": f"digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "generated": datetime.now().isoformat(),
        "period_days": days,
        "watchlist_count": len(watchlist.get('tickers', {})),
        "total_articles": len(all_recent_news),
        "high_priority_count": len(high_priority_news),
        "high_priority": high_priority_news[:10],  # Top 10
        "by_category": {k: len(v) for k, v in by_category.items()},
        "by_ticker": {k: len(v) for k, v in by_ticker.items()},
        "material_events": [a for a in high_priority_news if a.get('priority', 1) >= 5][:5]
    }
    
    # Save digest
    digests = load_json(DIGESTS_FILE, {"digests": []})
    digests['digests'].append(digest)
    digests['digests'] = digests['digests'][-100:]  # Keep last 100
    save_json(DIGESTS_FILE, digests)
    
    return digest


def check_alerts() -> List[Dict]:
    """Check for alert conditions."""
    config = get_config()
    min_priority = config.get('min_priority_for_alert', 4)
    
    alerts = load_json(ALERTS_FILE, {"alerts": [], "notified": []})
    notified_ids = set(alerts.get('notified', []))
    
    # Get recent high-priority news
    recent = get_cached_news(days=1, min_priority=min_priority)
    
    new_alerts = []
    for article in recent:
        if article.get('id') not in notified_ids:
            alert = {
                "id": f"alert_{article.get('id')}",
                "article_id": article.get('id'),
                "ticker": article.get('ticker'),
                "title": article.get('title'),
                "priority": article.get('priority'),
                "categories": article.get('categories'),
                "created": datetime.now().isoformat()
            }
            new_alerts.append(alert)
            notified_ids.add(article.get('id'))
    
    if new_alerts:
        alerts['alerts'].extend(new_alerts)
        alerts['notified'] = list(notified_ids)[-1000:]  # Keep last 1000
        save_json(ALERTS_FILE, alerts)
    
    return new_alerts


# ============ CLI Commands ============

def cmd_watchlist(args):
    """Manage watchlist."""
    if args.action == 'add':
        ticker = add_to_watchlist(args.ticker, args.name, args.notes)
        print(f"Added {args.ticker.upper()} to watchlist")
        
    elif args.action == 'remove':
        if remove_from_watchlist(args.ticker):
            print(f"Removed {args.ticker.upper()} from watchlist")
        else:
            print(f"Ticker {args.ticker.upper()} not in watchlist")
            
    elif args.action == 'list':
        watchlist = get_watchlist()
        tickers = watchlist.get('tickers', {})
        
        if args.json:
            print(json.dumps(tickers, indent=2))
        else:
            if not tickers:
                print("Watchlist is empty. Add tickers with: watchlist add TICKER")
                return
            print("\nWatchlist")
            print("=" * 50)
            for ticker, info in tickers.items():
                print(f"{ticker}: {info.get('name', '')} (added: {info.get('added', 'N/A')[:10]})")
                if info.get('notes'):
                    print(f"   Notes: {info.get('notes')}")


def cmd_fetch(args):
    """Fetch news for watchlist."""
    print("Fetching news...")
    all_news = fetch_all_watchlist_news(args.days)
    new_count = cache_news(all_news)
    
    total = sum(len(articles) for articles in all_news.values())
    print(f"Fetched {total} articles for {len(all_news)} tickers")
    print(f"New articles cached: {new_count}")


def cmd_news(args):
    """View news."""
    news = get_cached_news(
        ticker=args.ticker,
        days=args.days,
        category=args.category,
        min_priority=args.min_priority or 1
    )
    
    if args.limit:
        news = news[:args.limit]
    
    if args.json:
        print(json.dumps(news, indent=2))
    else:
        if not news:
            print("No news found. Try fetching first: fetch --days 7")
            return
        
        print(f"\nNews ({len(news)} articles)")
        print("=" * 70)
        for article in news:
            icons = ' '.join(article.get('icons', []))
            priority_stars = '*' * article.get('priority', 1)
            print(f"\n{article.get('ticker', 'N/A')} | {icons} {priority_stars}")
            print(f"  {article.get('title', 'No title')}")
            print(f"  Source: {article.get('source', 'Unknown')} | {article.get('published', 'N/A')[:16]}")


def cmd_digest(args):
    """Generate news digest."""
    digest = generate_digest(args.days, args.format)
    
    if args.json:
        print(json.dumps(digest, indent=2))
    else:
        print(f"\nNews Digest - {digest['period_days']} Day(s)")
        print("=" * 60)
        print(f"Generated: {digest['generated'][:16]}")
        print(f"Watching: {digest['watchlist_count']} tickers")
        print(f"Total Articles: {digest['total_articles']}")
        print(f"High Priority: {digest['high_priority_count']}")
        
        print("\n--- MATERIAL EVENTS ---")
        if digest['material_events']:
            for article in digest['material_events']:
                icons = ' '.join(article.get('icons', []))
                print(f"\n{article.get('ticker')} {icons}")
                print(f"  {article.get('title')}")
        else:
            print("No material events in this period.")
        
        print("\n--- By Category ---")
        for cat, count in sorted(digest['by_category'].items(), key=lambda x: -x[1]):
            icon = EVENT_CATEGORIES.get(cat, {}).get('icon', '')
            print(f"  {icon} {cat}: {count}")
        
        print("\n--- By Ticker ---")
        for ticker, count in sorted(digest['by_ticker'].items(), key=lambda x: -x[1])[:10]:
            print(f"  {ticker}: {count} articles")


def cmd_alerts(args):
    """Check and view alerts."""
    if args.check:
        new_alerts = check_alerts()
        if new_alerts:
            print(f"New alerts: {len(new_alerts)}")
            for alert in new_alerts:
                print(f"\n  [{alert['ticker']}] Priority {alert['priority']}")
                print(f"  {alert['title']}")
        else:
            print("No new alerts")
        return
    
    # List existing alerts
    alerts_data = load_json(ALERTS_FILE, {"alerts": []})
    alerts = alerts_data.get('alerts', [])
    
    if args.days:
        cutoff = (datetime.now() - timedelta(days=args.days)).isoformat()
        alerts = [a for a in alerts if a.get('created', '') > cutoff]
    
    if args.json:
        print(json.dumps(alerts, indent=2))
    else:
        if not alerts:
            print("No alerts. Run: alerts --check")
            return
        
        print(f"\nAlerts ({len(alerts)})")
        print("=" * 60)
        for alert in alerts[:20]:
            cats = ', '.join(alert.get('categories', []))
            print(f"\n[{alert['ticker']}] P{alert['priority']} | {cats}")
            print(f"  {alert['title']}")
            print(f"  Created: {alert['created'][:16]}")


def cmd_categories(args):
    """List event categories."""
    if args.json:
        print(json.dumps(EVENT_CATEGORIES, indent=2))
    else:
        print("\nEvent Categories")
        print("=" * 60)
        for name, info in sorted(EVENT_CATEGORIES.items(), key=lambda x: -x[1]['priority']):
            print(f"\n{info['icon']} {name.upper()} (Priority: {info['priority']})")
            print(f"   Keywords: {', '.join(info['keywords'][:5])}...")


def cmd_config(args):
    """View or update config."""
    config = get_config()
    
    if args.key and args.value:
        try:
            value = json.loads(args.value)
        except:
            value = args.value
        config[args.key] = value
        save_json(CONFIG_FILE, config)
        print(f"Set {args.key} = {value}")
        return
    
    if args.json:
        print(json.dumps(config, indent=2))
    else:
        print("\nConfiguration")
        print("=" * 50)
        for k, v in config.items():
            if isinstance(v, list):
                print(f"{k}: [{', '.join(str(x) for x in v[:3])}...]")
            else:
                print(f"{k}: {v}")


def cmd_stats(args):
    """Show statistics."""
    watchlist = get_watchlist()
    cache = load_json(NEWS_FILE, {"articles": []})
    digests = load_json(DIGESTS_FILE, {"digests": []})
    alerts = load_json(ALERTS_FILE, {"alerts": []})
    
    print("\nNews Digest Statistics")
    print("=" * 50)
    print(f"Watchlist tickers: {len(watchlist.get('tickers', {}))}")
    print(f"Cached articles: {len(cache.get('articles', []))}")
    print(f"Digests generated: {len(digests.get('digests', []))}")
    print(f"Total alerts: {len(alerts.get('alerts', []))}")
    
    if cache.get('last_fetch'):
        print(f"Last fetch: {cache['last_fetch'][:16]}")
    
    # Category breakdown of cached news
    by_cat = defaultdict(int)
    for article in cache.get('articles', []):
        for cat in article.get('categories', ['general']):
            by_cat[cat] += 1
    
    if by_cat:
        print("\nCached news by category:")
        for cat, count in sorted(by_cat.items(), key=lambda x: -x[1])[:5]:
            icon = EVENT_CATEGORIES.get(cat, {}).get('icon', '')
            print(f"  {icon} {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description="Financial News Alert Digests - Aggregate and summarize watchlist news",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s watchlist add AAPL --name "Apple Inc"
  %(prog)s watchlist list
  %(prog)s fetch --days 7
  %(prog)s news --ticker AAPL --days 3
  %(prog)s news --category earnings --min-priority 4
  %(prog)s digest --days 1
  %(prog)s alerts --check
  %(prog)s categories
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # watchlist
    p_watch = subparsers.add_parser('watchlist', help='Manage watchlist')
    p_watch.add_argument('action', choices=['add', 'remove', 'list'])
    p_watch.add_argument('ticker', nargs='?', help='Ticker symbol')
    p_watch.add_argument('--name', help='Company name')
    p_watch.add_argument('--notes', help='Notes about position')
    p_watch.add_argument('--json', action='store_true', help='JSON output')
    
    # fetch
    p_fetch = subparsers.add_parser('fetch', help='Fetch news for watchlist')
    p_fetch.add_argument('--days', type=int, default=7, help='Days of news to fetch')
    
    # news
    p_news = subparsers.add_parser('news', help='View cached news')
    p_news.add_argument('--ticker', '-t', help='Filter by ticker')
    p_news.add_argument('--days', '-d', type=int, default=7, help='Days back')
    p_news.add_argument('--category', '-c', help='Filter by category')
    p_news.add_argument('--min-priority', '-p', type=int, help='Minimum priority (1-5)')
    p_news.add_argument('--limit', '-l', type=int, help='Limit results')
    p_news.add_argument('--json', action='store_true', help='JSON output')
    
    # digest
    p_digest = subparsers.add_parser('digest', help='Generate news digest')
    p_digest.add_argument('--days', '-d', type=int, default=1, help='Days to include')
    p_digest.add_argument('--format', '-f', choices=['text', 'html', 'json'], default='text')
    p_digest.add_argument('--json', action='store_true', help='JSON output')
    
    # alerts
    p_alerts = subparsers.add_parser('alerts', help='View/check alerts')
    p_alerts.add_argument('--check', action='store_true', help='Check for new alerts')
    p_alerts.add_argument('--days', type=int, help='Filter by days')
    p_alerts.add_argument('--json', action='store_true', help='JSON output')
    
    # categories
    p_cat = subparsers.add_parser('categories', help='List event categories')
    p_cat.add_argument('--json', action='store_true', help='JSON output')
    
    # config
    p_config = subparsers.add_parser('config', help='View/update config')
    p_config.add_argument('--key', help='Config key')
    p_config.add_argument('--value', help='Config value')
    p_config.add_argument('--json', action='store_true', help='JSON output')
    
    # stats
    p_stats = subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        'watchlist': cmd_watchlist,
        'fetch': cmd_fetch,
        'news': cmd_news,
        'digest': cmd_digest,
        'alerts': cmd_alerts,
        'categories': cmd_categories,
        'config': cmd_config,
        'stats': cmd_stats
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
