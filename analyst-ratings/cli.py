#!/usr/bin/env python3
"""
Analyst Rating Changes Monitor - CLI Interface

Commands:
  scan <tickers...>    Scan tickers for analyst ratings
  watchlist            Scan default watchlist
  best                 Show best-rated stocks
  upside               Show stocks with biggest upside to targets
  changes <ticker>     Show recent rating changes for a ticker
  alerts               Show recent alerts
  export               Export data to CSV
"""

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import argparse
import json
import csv
import os
from datetime import datetime
from analyst_tracker import AnalystTracker, DEFAULT_WATCHLIST


def cmd_scan(args):
    """Scan specific tickers"""
    tracker = AnalystTracker()
    tickers = [t.upper() for t in args.tickers]
    
    print(f"\n🔍 Scanning {len(tickers)} tickers for analyst ratings...\n")
    
    ratings, alerts = tracker.scan_watchlist(tickers, verbose=True)
    
    print("\n" + "=" * 60)
    print("📊 ANALYST CONSENSUS")
    print("=" * 60)
    
    for r in ratings:
        print()
        print(tracker.format_consensus(r))
    
    if alerts:
        print("\n" + "=" * 60)
        print(f"⚠️ ALERTS ({len(alerts)})")
        print("=" * 60)
        
        for alert in alerts[:10]:
            print(tracker.format_alert(alert))
    
    print(f"\n✅ Scan complete. {len(ratings)} stocks analyzed.")


def cmd_watchlist(args):
    """Scan default watchlist"""
    args.tickers = DEFAULT_WATCHLIST
    cmd_scan(args)


def cmd_best(args):
    """Show best-rated stocks"""
    tracker = AnalystTracker()
    tickers = args.tickers if args.tickers else DEFAULT_WATCHLIST
    top_n = args.top or 10
    
    print(f"\n🏆 Top {top_n} Best-Rated Stocks\n")
    
    best = tracker.get_best_rated(tickers, top_n=top_n)
    
    print(f"{'Rank':<6} {'Ticker':<8} {'Rating':<12} {'Score':<8} {'Analysts':<10} {'Target':<10} {'Upside'}")
    print("-" * 70)
    
    for i, r in enumerate(best, 1):
        print(f"{i:<6} {r.ticker:<8} {r.consensus_rating:<12} {r.consensus_score:<8.1f} {r.num_analysts:<10} ${r.target_mean:<9.0f} {r.upside_pct*100:+.1f}%")
    
    print(f"\n✅ Showing {len(best)} best-rated stocks.")


def cmd_upside(args):
    """Show stocks with biggest upside"""
    tracker = AnalystTracker()
    tickers = args.tickers if args.tickers else DEFAULT_WATCHLIST
    top_n = args.top or 10
    
    print(f"\n📈 Top {top_n} Stocks by Upside Potential\n")
    
    top_upside = tracker.get_biggest_upside(tickers, top_n=top_n)
    
    print(f"{'Rank':<6} {'Ticker':<8} {'Price':<10} {'Target':<10} {'Upside':<10} {'Rating'}")
    print("-" * 65)
    
    for i, r in enumerate(top_upside, 1):
        print(f"{i:<6} {r.ticker:<8} ${r.current_price:<9.2f} ${r.target_mean:<9.0f} {r.upside_pct*100:+9.1f}% {r.consensus_rating}")
    
    print(f"\n✅ Showing {len(top_upside)} stocks with biggest upside.")


def cmd_changes(args):
    """Show recent rating changes"""
    tracker = AnalystTracker()
    ticker = args.ticker.upper()
    days = args.days or 30
    
    print(f"\n📋 Recent Rating Changes for {ticker} (last {days} days)\n")
    
    changes = tracker.get_recent_changes(ticker, days=days)
    
    if not changes:
        print("  No recent rating changes found.\n")
        return
    
    print(f"{'Date':<12} {'Firm':<25} {'Action':<12} {'From':<15} {'To'}")
    print("-" * 80)
    
    for c in changes:
        from_grade = c.prior_rating or "-"
        print(f"{c.date:<12} {c.firm[:24]:<25} {c.action:<12} {from_grade:<15} {c.rating}")
    
    print(f"\n✅ Found {len(changes)} rating changes.")


def cmd_alerts(args):
    """Show recent alerts"""
    tracker = AnalystTracker()
    
    if not os.path.exists(tracker.alerts_file):
        print("\n  No alerts found. Run a scan first.\n")
        return
    
    with open(tracker.alerts_file, 'r') as f:
        alerts = json.load(f)
    
    # Filter
    if args.ticker:
        alerts = [a for a in alerts if a['ticker'] == args.ticker.upper()]
    if args.type:
        alerts = [a for a in alerts if a['alert_type'] == args.type.upper()]
    
    print("\n⚠️ Recent Rating Alerts")
    print("=" * 60)
    
    if not alerts:
        print("\n  No matching alerts.\n")
        return
    
    for alert in reversed(alerts[-20:]):
        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(alert['severity'], "⚪")
        print(f"\n{severity_emoji} [{alert['ticker']}] {alert['alert_type']}")
        print(f"   {alert['message']}")
        print(f"   📅 {alert['timestamp'][:10]}")
    
    print(f"\n✅ Showing {min(20, len(alerts))} of {len(alerts)} alerts.")


def cmd_export(args):
    """Export to CSV"""
    tracker = AnalystTracker()
    output = args.output or f"ratings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    tickers = args.tickers if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\n📤 Exporting ratings to {output}...")
    
    ratings, _ = tracker.scan_watchlist(tickers, verbose=False)
    
    with open(output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Ticker', 'Name', 'Price', 'Consensus', 'Score',
            'Analysts', 'Target Mean', 'Target Low', 'Target High',
            'Upside %', 'Upgrades', 'Downgrades'
        ])
        
        for r in ratings:
            writer.writerow([
                r.ticker, r.name, f"{r.current_price:.2f}",
                r.consensus_rating, f"{r.consensus_score:.1f}",
                r.num_analysts, f"{r.target_mean:.0f}",
                f"{r.target_low:.0f}", f"{r.target_high:.0f}",
                f"{r.upside_pct*100:.1f}",
                r.recent_upgrades, r.recent_downgrades
            ])
    
    print(f"✅ Exported {len(ratings)} records to {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyst Rating Changes Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py scan AAPL NVDA TSLA     # Scan specific tickers
  python cli.py watchlist                # Scan default watchlist
  python cli.py best --top 5             # Top 5 best-rated
  python cli.py upside                   # Biggest upside potential
  python cli.py changes AAPL --days 60   # Recent changes for AAPL
  python cli.py alerts                   # View all alerts
  python cli.py alerts --ticker NVDA     # Alerts for specific ticker
  python cli.py export -o ratings.csv    # Export to CSV
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # scan
    scan_p = subparsers.add_parser('scan', help='Scan tickers')
    scan_p.add_argument('tickers', nargs='+', help='Tickers to scan')
    
    # watchlist
    subparsers.add_parser('watchlist', help='Scan default watchlist')
    
    # best
    best_p = subparsers.add_parser('best', help='Best-rated stocks')
    best_p.add_argument('--top', type=int, default=10, help='Number to show')
    best_p.add_argument('tickers', nargs='*', help='Optional custom list')
    
    # upside
    upside_p = subparsers.add_parser('upside', help='Biggest upside')
    upside_p.add_argument('--top', type=int, default=10, help='Number to show')
    upside_p.add_argument('tickers', nargs='*', help='Optional custom list')
    
    # changes
    changes_p = subparsers.add_parser('changes', help='Recent changes')
    changes_p.add_argument('ticker', help='Ticker symbol')
    changes_p.add_argument('--days', type=int, default=30, help='Days to look back')
    
    # alerts
    alerts_p = subparsers.add_parser('alerts', help='View alerts')
    alerts_p.add_argument('--ticker', help='Filter by ticker')
    alerts_p.add_argument('--type', help='Filter by type')
    
    # export
    export_p = subparsers.add_parser('export', help='Export to CSV')
    export_p.add_argument('-o', '--output', help='Output file')
    export_p.add_argument('tickers', nargs='*', help='Tickers to export')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    cmds = {
        'scan': cmd_scan,
        'watchlist': cmd_watchlist,
        'best': cmd_best,
        'upside': cmd_upside,
        'changes': cmd_changes,
        'alerts': cmd_alerts,
        'export': cmd_export
    }
    
    cmds[args.command](args)


if __name__ == "__main__":
    main()
