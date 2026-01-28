#!/usr/bin/env python3
"""
CLI for Insider Trading (Form 4) Monitor

Commands:
  scan      - Scan recent Form 4 filings
  ticker    - Get insider activity for a specific ticker
  alerts    - Get alerts for significant activity
  sentiment - Calculate insider sentiment score
  export    - Export data to JSON
"""

import argparse
import sys
import os
from datetime import datetime
from form4_tracker import Form4Tracker, InsiderTransaction

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    os.environ['PYTHONIOENCODING'] = 'utf-8'


def format_currency(value: float) -> str:
    """Format currency value"""
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    else:
        return f"${value:.0f}"


def format_sentiment_bar(score: float, width: int = 20) -> str:
    """Create a visual sentiment bar"""
    normalized = (score + 100) / 200  # 0 to 1
    filled = int(normalized * width)
    
    if score >= 30:
        color = "🟢"
    elif score >= 0:
        color = "🟡"
    elif score >= -30:
        color = "🟠"
    else:
        color = "🔴"
    
    bar = "█" * filled + "░" * (width - filled)
    return f"{color} [{bar}] {score:+.1f}"


def cmd_scan(args):
    """Scan recent Form 4 filings"""
    tracker = Form4Tracker()
    
    print(f"\n📊 Scanning recent Form 4 filings...")
    print("=" * 60)
    
    filings = tracker.get_recent_filings(args.count)
    
    if not filings:
        print("No filings found.")
        return
    
    for i, f in enumerate(filings[:args.count], 1):
        ticker = f.get('ticker', '???')
        title = f['title'][:50]
        date = f.get('date', 'N/A')
        print(f"{i:3}. [{ticker:6}] {date} - {title}")
    
    print(f"\n✅ Found {len(filings)} recent Form 4 filings")


def cmd_ticker(args):
    """Get insider activity for a specific ticker"""
    tracker = Form4Tracker()
    ticker = args.ticker.upper()
    
    print(f"\n📊 Insider Activity for {ticker}")
    print("=" * 60)
    
    sentiment = tracker.get_sentiment(ticker, args.days)
    
    if not sentiment.transactions:
        print(f"No Form 4 filings found for {ticker} in the last {args.days} days.")
        return
    
    print(f"Company: {sentiment.company_name}")
    print(f"Period: Last {args.days} days")
    print()
    
    # Summary
    print("📈 SUMMARY")
    print("-" * 40)
    print(f"  Sentiment Score: {format_sentiment_bar(sentiment.sentiment_score)}")
    print(f"  Total Transactions: {len(sentiment.transactions)}")
    print(f"  Purchases: {sentiment.total_purchases} ({format_currency(sentiment.purchase_value)})")
    print(f"  Sales: {sentiment.total_sales} ({format_currency(sentiment.sale_value)})")
    print(f"  Net Activity: {format_currency(sentiment.net_value)}")
    print(f"  Cluster Buying: {'✅ YES' if sentiment.has_cluster_buying() else '❌ No'}")
    print()
    
    # Transactions list
    print("📋 RECENT TRANSACTIONS")
    print("-" * 40)
    
    # Sort by date descending
    sorted_trans = sorted(sentiment.transactions, key=lambda x: x.filing_date, reverse=True)
    
    for t in sorted_trans[:args.limit]:
        tx_type = "🟢 BUY " if t.is_purchase else "🔴 SELL"
        csuite = "⭐" if t.is_csuite else "  "
        large = "💰" if t.is_large_purchase else "  "
        
        print(f"  {t.filing_date} {tx_type} {csuite}{large}")
        print(f"    {t.insider_name} ({t.insider_title or 'N/A'})")
        print(f"    {t.shares:,.0f} shares @ ${t.price:.2f} = {format_currency(t.value)}")
        print()


def cmd_alerts(args):
    """Get alerts for significant insider activity"""
    tracker = Form4Tracker()
    
    print(f"\n🚨 Insider Trading Alerts")
    print("=" * 60)
    
    if args.ticker:
        alerts = tracker.get_alerts(args.ticker, args.days)
    else:
        alerts = tracker.get_alerts(days=args.days)
    
    if not alerts:
        print("No significant alerts found.")
        return
    
    priority_icons = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}
    
    for alert in alerts:
        icon = priority_icons.get(alert.get('priority', 'LOW'), '⚪')
        alert_type = alert.get('type', 'UNKNOWN')
        ticker = alert.get('ticker', '???')
        company = alert.get('company', 'Unknown')
        
        print(f"\n{icon} [{alert['priority']}] {alert_type}")
        print(f"   Ticker: {ticker} - {company}")
        
        if alert_type == 'CSUITE_LARGE_PURCHASE':
            print(f"   Insider: {alert['insider']} ({alert['title']})")
            print(f"   Value: {format_currency(alert['value'])} ({alert['shares']:,.0f} shares)")
            print(f"   Date: {alert['date']}")
            
        elif alert_type == 'CLUSTER_BUYING':
            print(f"   Insiders: {', '.join(alert['insiders'][:3])}...")
            print(f"   Total Value: {format_currency(alert['total_value'])}")
            
        elif alert_type in ('BULLISH_SENTIMENT', 'BEARISH_SENTIMENT'):
            print(f"   Sentiment Score: {alert['sentiment_score']:+.1f}")
            print(f"   Buys/Sells: {alert['purchases']}/{alert['sales']}")
            print(f"   Net Value: {format_currency(alert['net_value'])}")
    
    print(f"\n✅ Found {len(alerts)} alerts")


def cmd_sentiment(args):
    """Calculate insider sentiment scores"""
    tracker = Form4Tracker()
    tickers = [t.strip().upper() for t in args.tickers.split(',')]
    
    print(f"\n📊 Insider Sentiment Analysis")
    print("=" * 60)
    
    results = []
    
    for ticker in tickers:
        print(f"\nAnalyzing {ticker}...", end=' ')
        sentiment = tracker.get_sentiment(ticker, args.days)
        
        if sentiment.transactions:
            results.append({
                'ticker': ticker,
                'company': sentiment.company_name,
                'score': sentiment.sentiment_score,
                'purchases': sentiment.total_purchases,
                'sales': sentiment.total_sales,
                'cluster': sentiment.has_cluster_buying()
            })
            print("✅")
        else:
            print("❌ No data")
    
    if not results:
        print("\nNo data found for any tickers.")
        return
    
    # Sort by sentiment score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "=" * 60)
    print(f"{'Ticker':<8} {'Score':<25} {'Buy/Sell':<12} {'Cluster'}")
    print("-" * 60)
    
    for r in results:
        score_bar = format_sentiment_bar(r['score'], 15)
        buy_sell = f"{r['purchases']}/{r['sales']}"
        cluster = "✅" if r['cluster'] else "-"
        print(f"{r['ticker']:<8} {score_bar} {buy_sell:<12} {cluster}")


def cmd_export(args):
    """Export insider data to JSON"""
    tracker = Form4Tracker()
    ticker = args.ticker.upper()
    
    print(f"\n📤 Exporting insider data for {ticker}...")
    
    filename = tracker.export_to_json(ticker, args.days)
    
    print(f"✅ Exported to: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Insider Trading (Form 4) Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py scan                     # Scan recent filings
  python cli.py ticker AAPL              # Get Apple insider activity
  python cli.py alerts                   # Get all alerts
  python cli.py alerts --ticker MSFT     # Get MSFT alerts
  python cli.py sentiment AAPL,GOOGL,MSFT  # Compare sentiment
  python cli.py export AAPL              # Export to JSON
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan recent Form 4 filings')
    scan_parser.add_argument('--count', '-c', type=int, default=20, help='Number of filings to show')
    
    # Ticker command
    ticker_parser = subparsers.add_parser('ticker', help='Get insider activity for a ticker')
    ticker_parser.add_argument('ticker', help='Stock ticker symbol')
    ticker_parser.add_argument('--days', '-d', type=int, default=90, help='Days to look back')
    ticker_parser.add_argument('--limit', '-l', type=int, default=10, help='Max transactions to show')
    
    # Alerts command
    alerts_parser = subparsers.add_parser('alerts', help='Get alerts for significant activity')
    alerts_parser.add_argument('--ticker', '-t', help='Filter by ticker')
    alerts_parser.add_argument('--days', '-d', type=int, default=30, help='Days to look back')
    
    # Sentiment command
    sentiment_parser = subparsers.add_parser('sentiment', help='Calculate sentiment scores')
    sentiment_parser.add_argument('tickers', help='Comma-separated list of tickers')
    sentiment_parser.add_argument('--days', '-d', type=int, default=90, help='Days to look back')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data to JSON')
    export_parser.add_argument('ticker', help='Stock ticker symbol')
    export_parser.add_argument('--days', '-d', type=int, default=90, help='Days to look back')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        'scan': cmd_scan,
        'ticker': cmd_ticker,
        'alerts': cmd_alerts,
        'sentiment': cmd_sentiment,
        'export': cmd_export
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
