#!/usr/bin/env python3
"""
Technical Divergence Alert System CLI
Detect price vs indicator divergences with accuracy tracking.
"""

import argparse
import json
import sys
from datetime import datetime
from divergence import (
    DivergenceScanner, DivergenceType, IndicatorType, Strength,
    generate_sample_data
)


def format_pct(value: float) -> str:
    """Format percentage."""
    return f"{value:+.1f}%"


def cmd_scan(args):
    """Scan for divergences."""
    scanner = generate_sample_data()
    
    if args.ticker:
        signals = [s for s in scanner.signals if s.ticker == args.ticker.upper()]
    else:
        signals = scanner.signals
    
    if args.bullish:
        signals = [s for s in signals if s.is_bullish]
    elif args.bearish:
        signals = [s for s in signals if not s.is_bullish]
    
    if args.strong:
        signals = [s for s in signals if s.strength == Strength.STRONG]
    
    if args.json:
        output = [{
            "ticker": s.ticker,
            "type": s.divergence_type.value,
            "indicator": s.indicator.value,
            "strength": s.strength.value,
            "confidence": s.confidence,
            "price_start": s.price_start,
            "price_end": s.price_end,
            "timeframe": s.timeframe,
            "detected_at": s.detected_at.isoformat()
        } for s in signals]
        print(json.dumps(output, indent=2))
        return
    
    print(f"\n{'='*70}")
    print(f"  DIVERGENCE SCAN RESULTS")
    print(f"{'='*70}\n")
    
    if not signals:
        print("  No divergences detected\n")
        return
    
    bullish = [s for s in signals if s.is_bullish]
    bearish = [s for s in signals if not s.is_bullish]
    
    if bullish:
        print("  [+] BULLISH DIVERGENCES")
        print(f"  {'-'*66}")
        for s in bullish:
            strength_icon = "*" if s.strength == Strength.STRONG else "o" if s.strength == Strength.WEAK else "-"
            conf_bar = "#" * int(s.confidence * 5) + "." * (5 - int(s.confidence * 5))
            print(f"  {strength_icon} {s.ticker:<6} {s.indicator.value:<6} {s.divergence_type.value:<15}")
            print(f"    Price: ${s.price_start:.2f} -> ${s.price_end:.2f} ({s.price_change_pct:+.1f}%)")
            print(f"    Confidence: [{conf_bar}] {s.confidence:.0%} | Bars: {s.lookback_bars}")
            print()
    
    if bearish:
        print("  [-] BEARISH DIVERGENCES")
        print(f"  {'-'*66}")
        for s in bearish:
            strength_icon = "*" if s.strength == Strength.STRONG else "o" if s.strength == Strength.WEAK else "-"
            conf_bar = "#" * int(s.confidence * 5) + "." * (5 - int(s.confidence * 5))
            print(f"  {strength_icon} {s.ticker:<6} {s.indicator.value:<6} {s.divergence_type.value:<15}")
            print(f"    Price: ${s.price_start:.2f} -> ${s.price_end:.2f} ({s.price_change_pct:+.1f}%)")
            print(f"    Confidence: [{conf_bar}] {s.confidence:.0%} | Bars: {s.lookback_bars}")
            print()


def cmd_alerts(args):
    """Show recent divergence alerts."""
    scanner = generate_sample_data()
    signals = scanner.get_recent_signals(hours=args.hours)
    
    if args.json:
        output = [{
            "ticker": s.ticker,
            "type": s.divergence_type.value,
            "indicator": s.indicator.value,
            "strength": s.strength.value,
            "confidence": s.confidence,
            "detected_at": s.detected_at.isoformat()
        } for s in signals[:args.limit]]
        print(json.dumps(output, indent=2))
        return
    
    print(f"\n{'='*70}")
    print(f"  DIVERGENCE ALERTS (Last {args.hours}h)")
    print(f"{'='*70}\n")
    
    if not signals:
        print("  No recent alerts\n")
        return
    
    for s in signals[:args.limit]:
        emoji = "[UP]" if s.is_bullish else "[DN]"
        strength_emoji = "*" if s.strength == Strength.STRONG else "-"
        time_str = s.detected_at.strftime("%H:%M")
        
        print(f"  {emoji} {strength_emoji} {s.ticker} - {s.divergence_type.value} {s.indicator.value}")
        print(f"     Confidence: {s.confidence:.0%} | Strength: {s.strength.value} | {time_str}")
        print()


def cmd_accuracy(args):
    """Show historical accuracy statistics."""
    scanner = generate_sample_data()
    
    indicator = None
    if args.indicator:
        try:
            indicator = IndicatorType(args.indicator.upper())
        except ValueError:
            pass
    
    stats = scanner.get_accuracy_stats(indicator)
    
    if args.json:
        print(json.dumps(stats, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  DIVERGENCE ACCURACY STATS")
    print(f"{'='*60}\n")
    
    if 'message' in stats:
        print(f"  {stats['message']}\n")
        return
    
    print(f"  Total Signals Tracked: {stats['total_signals']}")
    print(f"  Successful:           {stats['successful']}")
    print(f"  Overall Accuracy:     {stats['accuracy']:.1f}%")
    print()
    print(f"  {'-'*56}")
    print(f"  BY DIRECTION")
    print(f"  {'-'*56}")
    print(f"  Bullish Accuracy:     {stats['bullish_accuracy']:.1f}%")
    print(f"  Bearish Accuracy:     {stats['bearish_accuracy']:.1f}%")
    print()
    print(f"  {'-'*56}")
    print(f"  RETURNS")
    print(f"  {'-'*56}")
    print(f"  Avg Return:           {format_pct(stats['avg_return'])}")
    print(f"  Avg Winning Return:   {format_pct(stats['avg_winning_return'])}")
    
    if stats['by_indicator']:
        print(f"\n  {'-'*56}")
        print(f"  BY INDICATOR")
        print(f"  {'-'*56}")
        for ind, data in stats['by_indicator'].items():
            print(f"  {ind:<12} {data['count']:>3} signals | {data['accuracy']:.1f}% accuracy")
    
    print()


def cmd_summary(args):
    """Show signal summary."""
    scanner = generate_sample_data()
    summary = scanner.get_signal_summary()
    
    if args.json:
        print(json.dumps(summary, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  DIVERGENCE SUMMARY")
    print(f"{'='*60}\n")
    
    print(f"  Total Signals (48h):  {summary['total_signals']}")
    print(f"  Bullish:              {summary['bullish']}")
    print(f"  Bearish:              {summary['bearish']}")
    print(f"  Strong Signals:       {summary['strong_signals']}")
    print(f"  High Confidence:      {summary['high_confidence']}")
    
    if summary['by_indicator']:
        print(f"\n  {'-'*56}")
        print(f"  BY INDICATOR")
        print(f"  {'-'*56}")
        for ind, count in summary['by_indicator'].items():
            bar = "#" * count + "." * (10 - count)
            print(f"  {ind:<12} [{bar}] {count}")
    
    if summary['tickers_with_signals']:
        print(f"\n  Active Tickers: {', '.join(summary['tickers_with_signals'][:10])}")
    
    print()


def cmd_watch(args):
    """Manage watchlist."""
    scanner = generate_sample_data()
    
    if args.action == "list":
        if args.json:
            print(json.dumps(scanner.watchlist))
            return
        print(f"\n  WATCHLIST ({len(scanner.watchlist)} tickers)")
        print(f"  {'-'*40}")
        for ticker in scanner.watchlist:
            print(f"  - {ticker}")
        print()
    
    elif args.action == "add":
        if args.ticker:
            scanner.add_to_watchlist(args.ticker.upper())
            print(f"  Added {args.ticker.upper()} to watchlist")
    
    elif args.action == "remove":
        if args.ticker:
            scanner.remove_from_watchlist(args.ticker.upper())
            print(f"  Removed {args.ticker.upper()} from watchlist")


def cmd_export(args):
    """Export divergence data."""
    scanner = generate_sample_data()
    
    data = {
        "exported_at": datetime.now().isoformat(),
        "summary": scanner.get_signal_summary(),
        "accuracy": scanner.get_accuracy_stats(),
        "recent_signals": [
            {
                "ticker": s.ticker,
                "type": s.divergence_type.value,
                "indicator": s.indicator.value,
                "strength": s.strength.value,
                "confidence": s.confidence,
                "price_start": s.price_start,
                "price_end": s.price_end,
                "detected_at": s.detected_at.isoformat()
            }
            for s in scanner.get_recent_signals(hours=72)
        ]
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Exported to {args.output}")
    else:
        print(json.dumps(data, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="Technical Divergence Alert System"
    )
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Scan command
    p_scan = subparsers.add_parser('scan', help='Scan for divergences')
    p_scan.add_argument('--ticker', '-t', help='Filter by ticker')
    p_scan.add_argument('--bullish', action='store_true', help='Only bullish')
    p_scan.add_argument('--bearish', action='store_true', help='Only bearish')
    p_scan.add_argument('--strong', action='store_true', help='Only strong signals')
    p_scan.add_argument('--json', action='store_true', help='JSON output')
    p_scan.set_defaults(func=cmd_scan)
    
    # Alerts command
    p_alerts = subparsers.add_parser('alerts', help='Show recent alerts')
    p_alerts.add_argument('--hours', type=int, default=24, help='Lookback hours (default: 24)')
    p_alerts.add_argument('--limit', type=int, default=20, help='Number of alerts (default: 20)')
    p_alerts.add_argument('--json', action='store_true', help='JSON output')
    p_alerts.set_defaults(func=cmd_alerts)
    
    # Accuracy command
    p_accuracy = subparsers.add_parser('accuracy', help='Show accuracy stats')
    p_accuracy.add_argument('--indicator', '-i', help='Filter by indicator (RSI, MACD, OBV)')
    p_accuracy.add_argument('--json', action='store_true', help='JSON output')
    p_accuracy.set_defaults(func=cmd_accuracy)
    
    # Summary command
    p_summary = subparsers.add_parser('summary', help='Show signal summary')
    p_summary.add_argument('--json', action='store_true', help='JSON output')
    p_summary.set_defaults(func=cmd_summary)
    
    # Watch command
    p_watch = subparsers.add_parser('watch', help='Manage watchlist')
    p_watch.add_argument('action', choices=['list', 'add', 'remove'], help='Watchlist action')
    p_watch.add_argument('--ticker', '-t', help='Ticker for add/remove')
    p_watch.add_argument('--json', action='store_true', help='JSON output')
    p_watch.set_defaults(func=cmd_watch)
    
    # Export command
    p_export = subparsers.add_parser('export', help='Export data to JSON')
    p_export.add_argument('-o', '--output', help='Output file path')
    p_export.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default to summary
        args.json = False
        cmd_summary(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
