#!/usr/bin/env python3
"""
Options Flow Scanner CLI
Track unusual options activity, sweeps, and whale trades.
"""

import argparse
import json
import sys
from datetime import datetime

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from options_flow import OptionsFlowScanner, generate_sample_data


def format_currency(value: float) -> str:
    """Format currency with K/M suffixes."""
    if value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.0f}K"
    return f"${value:.0f}"


def cmd_overview(args):
    """Show market-wide options flow overview."""
    scanner = generate_sample_data()
    overview = scanner.get_market_overview(lookback_hours=args.hours)
    
    if args.json:
        print(json.dumps(overview, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  OPTIONS FLOW OVERVIEW ({args.hours}h)")
    print(f"{'='*60}\n")
    
    print(f"  📊 Total Flows:    {overview['total_flows']}")
    print(f"  💰 Total Premium:  {format_currency(overview['total_premium'])}")
    
    sentiment_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}
    print(f"  🎯 Sentiment:      {sentiment_emoji.get(overview['market_sentiment'], '⚪')} {overview['market_sentiment']}")
    
    print(f"\n  {'─'*56}")
    print(f"  TOP ACTIVE TICKERS")
    print(f"  {'─'*56}")
    print(f"  {'Ticker':<8} {'Premium':>12} {'Calls':>10} {'Puts':>10} {'Sentiment':>12}")
    print(f"  {'─'*56}")
    
    for t in overview['top_tickers'][:10]:
        sentiment_icon = sentiment_emoji.get(t['sentiment'], '⚪')
        print(f"  {t['ticker']:<8} {format_currency(t['total_premium']):>12} "
              f"{format_currency(t['call_premium']):>10} {format_currency(t['put_premium']):>10} "
              f"{sentiment_icon} {t['sentiment']:>9}")
    
    print()


def cmd_scan(args):
    """Scan a specific ticker for unusual activity."""
    scanner = generate_sample_data()
    result = scanner.scan_ticker(args.ticker.upper(), lookback_hours=args.hours)
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    
    ticker = result['ticker']
    
    print(f"\n{'='*60}")
    print(f"  OPTIONS FLOW: {ticker}")
    print(f"{'='*60}\n")
    
    if result['total_flows'] == 0:
        print(f"  No flow data for {ticker}\n")
        return
    
    print(f"  📊 Total Flows:       {result['total_flows']}")
    print(f"  📈 Call Volume:       {result['call_volume']:,}")
    print(f"  📉 Put Volume:        {result['put_volume']:,}")
    print(f"  💵 Call Premium:      {format_currency(result['call_premium'])}")
    print(f"  💵 Put Premium:       {format_currency(result['put_premium'])}")
    print(f"  📊 P/C Volume Ratio:  {result['put_call_volume_ratio']}")
    print(f"  📊 P/C Premium Ratio: {result['put_call_premium_ratio']}")
    
    sentiment_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}
    print(f"\n  🎯 Net Sentiment:     {sentiment_emoji.get(result['net_sentiment'], '⚪')} {result['net_sentiment']}")
    print(f"     Bullish Premium:   {format_currency(result['bullish_premium'])}")
    print(f"     Bearish Premium:   {format_currency(result['bearish_premium'])}")
    
    if result['largest_flows']:
        print(f"\n  {'─'*56}")
        print(f"  LARGEST FLOWS")
        print(f"  {'─'*56}")
        print(f"  {'Type':<6} {'Strike':>8} {'Exp':>12} {'Premium':>12} {'Vol':>8} {'Sent':>10}")
        print(f"  {'─'*56}")
        
        for f in result['largest_flows']:
            sent_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}[f['sentiment']]
            print(f"  {f['type'].upper():<6} ${f['strike']:>7.0f} {f['expiration']:>12} "
                  f"{format_currency(f['premium']):>12} {f['volume']:>8,} {sent_icon}{f['sentiment']:>9}")
    
    print()


def cmd_alerts(args):
    """Show recent unusual activity alerts."""
    scanner = generate_sample_data()
    alerts = scanner.get_recent_alerts(limit=args.limit)
    
    if args.json:
        print(json.dumps(alerts, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  UNUSUAL ACTIVITY ALERTS")
    print(f"{'='*60}\n")
    
    if not alerts:
        print("  No recent alerts\n")
        return
    
    alert_emoji = {
        "LARGE_PREMIUM": "💰",
        "WHALE_ALERT": "🐋",
        "SWEEP": "⚡",
        "VOLUME_OI_ANOMALY": "📊",
        "UNUSUAL_VOLUME": "🔥"
    }
    
    for alert in alerts:
        emoji = alert_emoji.get(alert['type'], '⚠️')
        time_str = datetime.fromisoformat(alert['time']).strftime("%H:%M")
        confidence_bar = "█" * int(alert['confidence'] * 5) + "░" * (5 - int(alert['confidence'] * 5))
        
        print(f"  {emoji} [{alert['type']}] {alert['ticker']}")
        print(f"     {alert['description']}")
        print(f"     Premium: {format_currency(alert['premium'])} | Confidence: [{confidence_bar}]")
        print()


def cmd_skew(args):
    """Detect unusual put/call ratios."""
    scanner = generate_sample_data()
    skewed = scanner.detect_put_call_skew(lookback_hours=args.hours)
    
    if args.json:
        print(json.dumps(skewed, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  UNUSUAL PUT/CALL SKEW ({args.hours}h)")
    print(f"{'='*60}\n")
    
    if not skewed:
        print("  No unusual skew detected\n")
        return
    
    print(f"  {'Ticker':<8} {'P/C Ratio':>10} {'Calls':>12} {'Puts':>12} {'Bias':>10}")
    print(f"  {'─'*56}")
    
    for s in skewed[:15]:
        ratio_str = f"{s['put_call_ratio']:.2f}" if s['put_call_ratio'] != float('inf') else "∞"
        bias_emoji = "🔴" if s['bias'] == "BEARISH" else "🟢"
        print(f"  {s['ticker']:<8} {ratio_str:>10} {format_currency(s['call_premium']):>12} "
              f"{format_currency(s['put_premium']):>12} {bias_emoji}{s['bias']:>8}")
    
    print()


def cmd_whales(args):
    """Show whale trades (>$1M premium)."""
    scanner = generate_sample_data()
    
    # Filter for whale alerts
    whale_alerts = [a for a in scanner.get_recent_alerts(50) 
                   if a['type'] in ('WHALE_ALERT', 'LARGE_PREMIUM') and a['premium'] >= 500000]
    
    if args.json:
        print(json.dumps(whale_alerts, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  🐋 WHALE TRADES")
    print(f"{'='*60}\n")
    
    if not whale_alerts:
        print("  No whale trades detected\n")
        return
    
    for alert in sorted(whale_alerts, key=lambda x: x['premium'], reverse=True)[:10]:
        sentiment_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}
        print(f"  🐋 {alert['ticker']} - {format_currency(alert['premium'])}")
        print(f"     {alert['description']}")
        print(f"     Sentiment: {sentiment_emoji.get(alert['sentiment'], '⚪')} {alert['sentiment'].upper()}")
        print()


def cmd_export(args):
    """Export flow data to JSON."""
    scanner = generate_sample_data()
    
    data = {
        "exported_at": datetime.now().isoformat(),
        "overview": scanner.get_market_overview(lookback_hours=24),
        "alerts": scanner.get_recent_alerts(50),
        "skew": scanner.detect_put_call_skew(lookback_hours=24)
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Exported to {args.output}")
    else:
        print(json.dumps(data, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="Options Flow Scanner - Track unusual options activity"
    )
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Overview command
    p_overview = subparsers.add_parser('overview', help='Market-wide flow overview')
    p_overview.add_argument('--hours', type=int, default=24, help='Lookback hours (default: 24)')
    p_overview.add_argument('--json', action='store_true', help='JSON output')
    p_overview.set_defaults(func=cmd_overview)
    
    # Scan command
    p_scan = subparsers.add_parser('scan', help='Scan specific ticker')
    p_scan.add_argument('ticker', help='Ticker symbol')
    p_scan.add_argument('--hours', type=int, default=24, help='Lookback hours (default: 24)')
    p_scan.add_argument('--json', action='store_true', help='JSON output')
    p_scan.set_defaults(func=cmd_scan)
    
    # Alerts command
    p_alerts = subparsers.add_parser('alerts', help='Show unusual activity alerts')
    p_alerts.add_argument('--limit', type=int, default=20, help='Number of alerts (default: 20)')
    p_alerts.add_argument('--json', action='store_true', help='JSON output')
    p_alerts.set_defaults(func=cmd_alerts)
    
    # Skew command
    p_skew = subparsers.add_parser('skew', help='Detect unusual put/call ratios')
    p_skew.add_argument('--hours', type=int, default=24, help='Lookback hours (default: 24)')
    p_skew.add_argument('--json', action='store_true', help='JSON output')
    p_skew.set_defaults(func=cmd_skew)
    
    # Whales command
    p_whales = subparsers.add_parser('whales', help='Show whale trades')
    p_whales.add_argument('--json', action='store_true', help='JSON output')
    p_whales.set_defaults(func=cmd_whales)
    
    # Export command
    p_export = subparsers.add_parser('export', help='Export flow data to JSON')
    p_export.add_argument('-o', '--output', help='Output file path')
    p_export.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default to overview
        args.hours = 24
        args.json = False
        cmd_overview(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
