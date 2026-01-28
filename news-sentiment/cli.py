#!/usr/bin/env python3
"""
News Sentiment Engine - CLI
Command-line interface for real-time sentiment analysis.
"""

import sys
import argparse
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from news_sentiment import (
    NewsSentimentEngine, 
    print_snapshot, 
    print_alerts,
    SCRIPT_DIR,
    ALERTS_FILE,
    SENTIMENT_HISTORY_FILE
)


def cmd_analyze(args):
    """Analyze sentiment for one or more tickers."""
    engine = NewsSentimentEngine()
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    if len(tickers) == 1:
        result = engine.analyze_ticker(tickers[0], force_refresh=args.refresh)
        print_snapshot(result["snapshot"])
        print_alerts(result["alerts"])
        
        if args.export:
            output_path = SCRIPT_DIR / f"sentiment_{tickers[0]}_{result['snapshot']['timestamp'][:10]}.json"
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\n[OK] Exported to {output_path}")
    else:
        result = engine.analyze_multiple(tickers, force_refresh=args.refresh)
        
        for ticker, snapshot in result["results"].items():
            print_snapshot(snapshot)
        
        print_alerts(result["alerts"])
        
        # Print summary
        summary = result["summary"]
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"  Tickers Analyzed: {summary['ticker_count']}")
        print(f"  Average Sentiment: {summary['avg_sentiment']:.3f}")
        print(f"  Bullish: {summary['bullish_count']} | Neutral: {summary['neutral_count']} | Bearish: {summary['bearish_count']}")
        
        if summary.get("most_bullish"):
            print(f"\n  Most Bullish: {summary['most_bullish']['ticker']} ({summary['most_bullish']['sentiment']:.3f})")
        if summary.get("most_bearish"):
            print(f"  Most Bearish: {summary['most_bearish']['ticker']} ({summary['most_bearish']['sentiment']:.3f})")
        
        if args.export:
            output_path = SCRIPT_DIR / f"sentiment_batch_{len(tickers)}stocks.json"
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\n[OK] Exported to {output_path}")


def cmd_history(args):
    """Show sentiment history for a ticker."""
    engine = NewsSentimentEngine()
    ticker = args.ticker.upper()
    history = engine.get_history(ticker, days=args.days)
    
    if not history:
        print(f"No history found for {ticker}")
        return
    
    print(f"\n{'='*60}")
    print(f"SENTIMENT HISTORY: {ticker} (Last {args.days} days)")
    print(f"{'='*60}")
    print(f"{'Date':<20} {'Sentiment':>10} {'Label':>10} {'Momentum':>10} {'Articles':>10}")
    print("-" * 60)
    
    for entry in history[-20:]:  # Last 20 entries
        date = entry["timestamp"][:16].replace("T", " ")
        print(f"{date:<20} {entry['avg_sentiment']:>10.3f} {entry['sentiment_label']:>10} {entry['momentum']:>+10.3f} {entry['article_count']:>10}")
    
    # Calculate trend
    if len(history) >= 2:
        first = history[0]["avg_sentiment"]
        last = history[-1]["avg_sentiment"]
        trend = last - first
        trend_label = "IMPROVING" if trend > 0.05 else "DECLINING" if trend < -0.05 else "STABLE"
        print(f"\nOverall Trend: {trend:+.3f} ({trend_label})")


def cmd_momentum(args):
    """Show momentum leaders across tickers."""
    engine = NewsSentimentEngine()
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    # First, analyze all to get fresh data
    if args.refresh:
        print("Refreshing data for all tickers...")
        engine.analyze_multiple(tickers, force_refresh=True)
    
    leaders = engine.get_momentum_leaders(tickers)
    
    print(f"\n{'='*60}")
    print("SENTIMENT MOMENTUM LEADERS")
    print(f"{'='*60}")
    
    print("\n[+] IMPROVING SENTIMENT:")
    if leaders["improving"]:
        for item in leaders["improving"]:
            print(f"  {item['ticker']:<6} Momentum: {item['momentum']:+.3f} | Now: {item['current']:.3f} ({item['label']})")
    else:
        print("  No improving tickers found")
    
    print("\n[-] DECLINING SENTIMENT:")
    if leaders["declining"]:
        for item in leaders["declining"]:
            print(f"  {item['ticker']:<6} Momentum: {item['momentum']:+.3f} | Now: {item['current']:.3f} ({item['label']})")
    else:
        print("  No declining tickers found")


def cmd_alerts(args):
    """Show recent alerts."""
    if not ALERTS_FILE.exists():
        print("No alerts found.")
        return
    
    with open(ALERTS_FILE, "r") as f:
        alerts = json.load(f)
    
    if args.ticker:
        alerts = [a for a in alerts if a["ticker"] == args.ticker.upper()]
    
    if not alerts:
        print("No alerts found.")
        return
    
    print(f"\n{'='*60}")
    print(f"RECENT ALERTS ({len(alerts)} total)")
    print(f"{'='*60}")
    
    for alert in alerts[-20:]:  # Last 20
        severity_icon = "[!!!]" if alert["severity"] == "high" else "[!!]" if alert["severity"] == "medium" else "[!]"
        date = alert["timestamp"][:16].replace("T", " ")
        print(f"\n{severity_icon} [{alert['type']}] {alert['ticker']} - {date}")
        print(f"   {alert['message']}")


def cmd_scan(args):
    """Scan watchlist and show sentiment overview."""
    engine = NewsSentimentEngine()
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    result = engine.analyze_multiple(tickers, force_refresh=args.refresh)
    
    # Sort by sentiment
    sorted_results = sorted(
        result["results"].items(),
        key=lambda x: x[1]["avg_sentiment"],
        reverse=True
    )
    
    print(f"\n{'='*60}")
    print("SENTIMENT SCAN RESULTS")
    print(f"{'='*60}")
    print(f"{'Ticker':<8} {'Sentiment':>10} {'Label':>10} {'Bull%':>8} {'Bear%':>8} {'Articles':>10}")
    print("-" * 60)
    
    for ticker, snapshot in sorted_results:
        label_marker = "[+]" if snapshot["sentiment_label"] == "bullish" else "[-]" if snapshot["sentiment_label"] == "bearish" else "[=]"
        print(f"{ticker:<8} {snapshot['avg_sentiment']:>10.3f} {label_marker}{snapshot['sentiment_label']:>9} {snapshot['bullish_pct']:>7.1f}% {snapshot['bearish_pct']:>7.1f}% {snapshot['article_count']:>10}")
    
    # Alert summary
    if result["alerts"]:
        print(f"\n[!] {len(result['alerts'])} alerts triggered!")
        print_alerts(result["alerts"])


def cmd_compare(args):
    """Compare sentiment between two tickers."""
    engine = NewsSentimentEngine()
    ticker1 = args.ticker1.upper()
    ticker2 = args.ticker2.upper()
    
    r1 = engine.analyze_ticker(ticker1, force_refresh=args.refresh)
    r2 = engine.analyze_ticker(ticker2, force_refresh=args.refresh)
    
    s1 = r1["snapshot"]
    s2 = r2["snapshot"]
    
    print(f"\n{'='*60}")
    print(f"SENTIMENT COMPARISON: {ticker1} vs {ticker2}")
    print(f"{'='*60}")
    
    print(f"\n{'Metric':<25} {ticker1:>15} {ticker2:>15}")
    print("-" * 55)
    print(f"{'Avg Sentiment':<25} {s1['avg_sentiment']:>15.3f} {s2['avg_sentiment']:>15.3f}")
    print(f"{'Label':<25} {s1['sentiment_label']:>15} {s2['sentiment_label']:>15}")
    print(f"{'Bullish %':<25} {s1['bullish_pct']:>14.1f}% {s2['bullish_pct']:>14.1f}%")
    print(f"{'Bearish %':<25} {s1['bearish_pct']:>14.1f}% {s2['bearish_pct']:>14.1f}%")
    print(f"{'Momentum':<25} {s1['momentum']:>+15.3f} {s2['momentum']:>+15.3f}")
    print(f"{'Article Count':<25} {s1['article_count']:>15} {s2['article_count']:>15}")
    
    diff = s1["avg_sentiment"] - s2["avg_sentiment"]
    if abs(diff) > 0.1:
        winner = ticker1 if diff > 0 else ticker2
        print(f"\n[*] {winner} has more positive sentiment ({abs(diff):.3f} higher)")


def cmd_test(args):
    """Test sentiment analysis on custom text."""
    engine = NewsSentimentEngine()
    text = args.text
    
    score, label = engine.analyze_sentiment(text)
    
    print(f"\nText: {text}")
    print(f"Score: {score:.3f}")
    print(f"Label: {label}")
    
    indicator = "[+]" if label == "bullish" else "[-]" if label == "bearish" else "[=]"
    print(f"\nResult: {indicator} {label.upper()}")


def main():
    parser = argparse.ArgumentParser(
        description="News Sentiment Engine - Real-time NLP sentiment analysis"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Analyze command
    p_analyze = subparsers.add_parser("analyze", help="Analyze sentiment for ticker(s)")
    p_analyze.add_argument("tickers", help="Ticker symbol(s), comma-separated")
    p_analyze.add_argument("--refresh", "-r", action="store_true", help="Force refresh (ignore cache)")
    p_analyze.add_argument("--export", "-e", action="store_true", help="Export results to JSON")
    p_analyze.set_defaults(func=cmd_analyze)
    
    # History command
    p_history = subparsers.add_parser("history", help="Show sentiment history")
    p_history.add_argument("ticker", help="Ticker symbol")
    p_history.add_argument("--days", "-d", type=int, default=7, help="Number of days (default: 7)")
    p_history.set_defaults(func=cmd_history)
    
    # Momentum command
    p_momentum = subparsers.add_parser("momentum", help="Show momentum leaders")
    p_momentum.add_argument("tickers", help="Ticker symbols, comma-separated")
    p_momentum.add_argument("--refresh", "-r", action="store_true", help="Force refresh")
    p_momentum.set_defaults(func=cmd_momentum)
    
    # Alerts command
    p_alerts = subparsers.add_parser("alerts", help="Show recent alerts")
    p_alerts.add_argument("--ticker", "-t", help="Filter by ticker")
    p_alerts.set_defaults(func=cmd_alerts)
    
    # Scan command
    p_scan = subparsers.add_parser("scan", help="Scan watchlist for sentiment")
    p_scan.add_argument("tickers", help="Ticker symbols, comma-separated")
    p_scan.add_argument("--refresh", "-r", action="store_true", help="Force refresh")
    p_scan.set_defaults(func=cmd_scan)
    
    # Compare command
    p_compare = subparsers.add_parser("compare", help="Compare sentiment between two tickers")
    p_compare.add_argument("ticker1", help="First ticker")
    p_compare.add_argument("ticker2", help="Second ticker")
    p_compare.add_argument("--refresh", "-r", action="store_true", help="Force refresh")
    p_compare.set_defaults(func=cmd_compare)
    
    # Test command
    p_test = subparsers.add_parser("test", help="Test sentiment on custom text")
    p_test.add_argument("text", help="Text to analyze")
    p_test.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
