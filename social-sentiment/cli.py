#!/usr/bin/env python3
"""
Social Sentiment Aggregator CLI
Track retail sentiment across Reddit and StockTwits
"""

import sys
import os

# Handle Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
from datetime import datetime
from sentiment_aggregator import SocialSentimentAggregator, run_all_tests


def format_sentiment(score: float) -> str:
    """Format sentiment score with indicator"""
    if score > 0.5:
        return f"+{score:.2f} [VERY BULLISH]"
    elif score > 0.2:
        return f"+{score:.2f} [BULLISH]"
    elif score < -0.5:
        return f"{score:.2f} [VERY BEARISH]"
    elif score < -0.2:
        return f"{score:.2f} [BEARISH]"
    else:
        return f"{score:.2f} [NEUTRAL]"


def cmd_analyze(args):
    """Analyze sentiment for a ticker"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=500)
    
    ticker = args.ticker.upper()
    summary = agg.get_ticker_summary(ticker)
    
    if summary['mention_count'] == 0:
        print(f"\nNo mentions found for {ticker}")
        return
    
    print(f"\n{'='*60}")
    print(f"  SOCIAL SENTIMENT: {ticker}")
    print(f"{'='*60}")
    print(f"  Sentiment: {format_sentiment(summary['sentiment_score'])}")
    print(f"  Mentions:  {summary['mention_count']} ({summary['mention_velocity']}/hr)")
    print(f"  Momentum:  {summary['momentum']:+.3f}")
    print()
    print(f"  Breakdown:")
    print(f"    Bullish:  {summary['bullish_pct']:.1f}%")
    print(f"    Bearish:  {summary['bearish_pct']:.1f}%")
    print(f"    Neutral:  {summary['neutral_pct']:.1f}%")
    print()
    print(f"  Sources: {summary['sources']}")
    
    if summary['alerts']:
        print(f"\n  ALERTS:")
        for alert in summary['alerts']:
            severity = alert['severity'].upper()
            print(f"    [{severity}] {alert['message']}")
    
    if summary['top_posts']:
        print(f"\n  Top Posts:")
        for i, post in enumerate(summary['top_posts'], 1):
            sent = format_sentiment(post['sentiment'])
            print(f"    {i}. [{post['source']}] {post['text'][:80]}...")
            print(f"       Sentiment: {sent} | Upvotes: {post['upvotes']}")
    
    print(f"{'='*60}\n")


def cmd_trending(args):
    """Show trending tickers by mention velocity"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=500)
    
    trending = agg.get_trending(hours=args.hours, limit=args.limit)
    
    print(f"\n{'='*60}")
    print(f"  TRENDING TICKERS (Last {args.hours}h)")
    print(f"{'='*60}")
    print(f"  {'Rank':<5} {'Ticker':<8} {'Mentions':<10} {'Velocity':<12} {'Sentiment':<12}")
    print(f"  {'-'*5} {'-'*8} {'-'*10} {'-'*12} {'-'*12}")
    
    for i, t in enumerate(trending, 1):
        sent_str = format_sentiment(t['sentiment']).split()[0]
        print(f"  {i:<5} {t['ticker']:<8} {t['mentions']:<10} {t['velocity']:<12.2f} {sent_str:<12}")
    
    print(f"{'='*60}\n")


def cmd_bullish(args):
    """Show most bullish tickers"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=500)
    
    bullish = agg.get_most_bullish(hours=args.hours, min_mentions=args.min_mentions, limit=args.limit)
    
    print(f"\n{'='*60}")
    print(f"  MOST BULLISH TICKERS (Last {args.hours}h)")
    print(f"{'='*60}")
    print(f"  {'Rank':<5} {'Ticker':<8} {'Sentiment':<12} {'Bullish%':<10} {'Mentions':<10} {'Momentum':<10}")
    print(f"  {'-'*5} {'-'*8} {'-'*12} {'-'*10} {'-'*10} {'-'*10}")
    
    for i, t in enumerate(bullish, 1):
        print(f"  {i:<5} {t['ticker']:<8} {t['sentiment']:+.3f}       {t['bullish_pct']*100:<10.1f} {t['mentions']:<10} {t['momentum']:+.3f}")
    
    print(f"{'='*60}\n")


def cmd_bearish(args):
    """Show most bearish tickers"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=500)
    
    bearish = agg.get_most_bearish(hours=args.hours, min_mentions=args.min_mentions, limit=args.limit)
    
    print(f"\n{'='*60}")
    print(f"  MOST BEARISH TICKERS (Last {args.hours}h)")
    print(f"{'='*60}")
    print(f"  {'Rank':<5} {'Ticker':<8} {'Sentiment':<12} {'Bearish%':<10} {'Mentions':<10} {'Momentum':<10}")
    print(f"  {'-'*5} {'-'*8} {'-'*12} {'-'*10} {'-'*10} {'-'*10}")
    
    for i, t in enumerate(bearish, 1):
        print(f"  {i:<5} {t['ticker']:<8} {t['sentiment']:+.3f}       {t['bearish_pct']*100:<10.1f} {t['mentions']:<10} {t['momentum']:+.3f}")
    
    print(f"{'='*60}\n")


def cmd_alerts(args):
    """Show all sentiment alerts"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=500)
    
    tickers = [t.upper() for t in args.tickers] if args.tickers else None
    alerts = agg.get_all_alerts(tickers)
    
    print(f"\n{'='*60}")
    print(f"  SENTIMENT ALERTS")
    print(f"{'='*60}")
    
    if not alerts:
        print("  No alerts triggered")
    else:
        for alert in alerts:
            severity_icon = {'high': '[!!!]', 'medium': '[!!]', 'low': '[!]'}.get(alert.severity, '[?]')
            print(f"  {severity_icon} {alert.ticker}: {alert.alert_type}")
            print(f"      {alert.message}")
            print()
    
    print(f"{'='*60}\n")


def cmd_scan(args):
    """Scan watchlist for sentiment signals"""
    agg = SocialSentimentAggregator()
    
    tickers = [t.upper() for t in args.tickers] if args.tickers else None
    agg.generate_sample_data(tickers=tickers, num_posts=500)
    
    print(f"\n{'='*60}")
    print(f"  WATCHLIST SENTIMENT SCAN")
    print(f"{'='*60}")
    
    for ticker in (tickers or list(agg.ticker_data.keys())[:10]):
        summary = agg.get_ticker_summary(ticker)
        if summary['mention_count'] > 0:
            sent = format_sentiment(summary['sentiment_score'])
            alert_count = len(summary['alerts'])
            alert_str = f" [{alert_count} alerts]" if alert_count > 0 else ""
            print(f"  {ticker:<8} | {summary['mention_count']:>4} mentions | {sent}{alert_str}")
    
    print(f"{'='*60}\n")


def cmd_momentum(args):
    """Show tickers with biggest sentiment momentum changes"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=500)
    
    # Get all tickers with momentum
    results = []
    for ticker in agg.ticker_data:
        ts = agg.calculate_aggregates(ticker, hours=24)
        if ts.mention_count >= args.min_mentions and abs(ts.sentiment_momentum) > 0.05:
            results.append({
                'ticker': ticker,
                'momentum': ts.sentiment_momentum,
                'sentiment': ts.weighted_sentiment,
                'mentions': ts.mention_count
            })
    
    # Sort by absolute momentum
    results.sort(key=lambda x: abs(x['momentum']), reverse=True)
    
    print(f"\n{'='*60}")
    print(f"  SENTIMENT MOMENTUM CHANGES")
    print(f"{'='*60}")
    print(f"  {'Ticker':<8} {'Momentum':<12} {'Current':<12} {'Direction':<12} {'Mentions':<10}")
    print(f"  {'-'*8} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")
    
    for t in results[:args.limit]:
        direction = "TURNING BULLISH" if t['momentum'] > 0 else "TURNING BEARISH"
        print(f"  {t['ticker']:<8} {t['momentum']:+.3f}       {t['sentiment']:+.3f}       {direction:<12} {t['mentions']:<10}")
    
    print(f"{'='*60}\n")


def cmd_test(args):
    """Run all tests"""
    run_all_tests()


def cmd_summary(args):
    """Voice-friendly summary"""
    agg = SocialSentimentAggregator()
    agg.generate_sample_data(num_posts=500)
    
    trending = agg.get_trending(hours=24, limit=3)
    bullish = agg.get_most_bullish(min_mentions=5, limit=3)
    bearish = agg.get_most_bearish(min_mentions=5, limit=3)
    alerts = agg.get_all_alerts()
    
    high_alerts = [a for a in alerts if a.severity == 'high']
    
    print("\n=== SOCIAL SENTIMENT SUMMARY ===\n")
    
    # Trending
    if trending:
        top = trending[0]
        print(f"Most discussed: {top['ticker']} with {top['mentions']} mentions "
              f"({top['velocity']:.1f} per hour)")
    
    # Bullish
    if bullish:
        top_bull = bullish[0]
        print(f"Most bullish: {top_bull['ticker']} with {top_bull['bullish_pct']*100:.0f}% "
              f"bullish posts (sentiment {top_bull['sentiment']:+.2f})")
    
    # Bearish
    if bearish:
        top_bear = bearish[0]
        print(f"Most bearish: {top_bear['ticker']} with {top_bear['bearish_pct']*100:.0f}% "
              f"bearish posts (sentiment {top_bear['sentiment']:+.2f})")
    
    # Alerts
    if high_alerts:
        print(f"\n{len(high_alerts)} high-priority alerts:")
        for alert in high_alerts[:3]:
            print(f"  - {alert.ticker}: {alert.alert_type}")
    else:
        print("\nNo high-priority sentiment alerts.")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Social Sentiment Aggregator - Track Reddit/StockTwits sentiment"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # analyze
    p_analyze = subparsers.add_parser('analyze', help='Analyze sentiment for a ticker')
    p_analyze.add_argument('ticker', help='Stock ticker symbol')
    p_analyze.set_defaults(func=cmd_analyze)
    
    # trending
    p_trending = subparsers.add_parser('trending', help='Show trending tickers')
    p_trending.add_argument('--hours', type=int, default=24, help='Time window (hours)')
    p_trending.add_argument('--limit', type=int, default=10, help='Number of results')
    p_trending.set_defaults(func=cmd_trending)
    
    # bullish
    p_bullish = subparsers.add_parser('bullish', help='Show most bullish tickers')
    p_bullish.add_argument('--hours', type=int, default=24, help='Time window (hours)')
    p_bullish.add_argument('--min-mentions', type=int, default=5, help='Minimum mentions')
    p_bullish.add_argument('--limit', type=int, default=10, help='Number of results')
    p_bullish.set_defaults(func=cmd_bullish)
    
    # bearish
    p_bearish = subparsers.add_parser('bearish', help='Show most bearish tickers')
    p_bearish.add_argument('--hours', type=int, default=24, help='Time window (hours)')
    p_bearish.add_argument('--min-mentions', type=int, default=5, help='Minimum mentions')
    p_bearish.add_argument('--limit', type=int, default=10, help='Number of results')
    p_bearish.set_defaults(func=cmd_bearish)
    
    # alerts
    p_alerts = subparsers.add_parser('alerts', help='Show sentiment alerts')
    p_alerts.add_argument('tickers', nargs='*', help='Filter by tickers (optional)')
    p_alerts.set_defaults(func=cmd_alerts)
    
    # scan
    p_scan = subparsers.add_parser('scan', help='Scan watchlist for sentiment')
    p_scan.add_argument('tickers', nargs='*', help='Tickers to scan')
    p_scan.set_defaults(func=cmd_scan)
    
    # momentum
    p_momentum = subparsers.add_parser('momentum', help='Show sentiment momentum changes')
    p_momentum.add_argument('--min-mentions', type=int, default=5, help='Minimum mentions')
    p_momentum.add_argument('--limit', type=int, default=10, help='Number of results')
    p_momentum.set_defaults(func=cmd_momentum)
    
    # summary
    p_summary = subparsers.add_parser('summary', help='Voice-friendly summary')
    p_summary.set_defaults(func=cmd_summary)
    
    # test
    p_test = subparsers.add_parser('test', help='Run all tests')
    p_test.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
