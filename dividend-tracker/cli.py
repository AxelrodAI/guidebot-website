#!/usr/bin/env python3
"""
Dividend Calendar + Yield Monitor - CLI Interface

Commands:
  scan <tickers...>    Scan specific tickers for dividend info
  watchlist            Scan default dividend watchlist
  calendar [days]      Show upcoming ex-dividend dates
  yields               Show yield rankings
  alerts               Show recent alerts
  export               Export data to CSV
  clear                Clear cache files
"""

import sys
# Fix Windows encoding for emojis
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
from dividend_tracker import DividendTracker, DEFAULT_DIVIDEND_WATCHLIST


def cmd_scan(args):
    """Scan specific tickers"""
    tracker = DividendTracker()
    tickers = [t.upper() for t in args.tickers]
    
    print(f"\n🔍 Scanning {len(tickers)} tickers for dividend data...\n")
    
    div_infos, alerts = tracker.scan_watchlist(tickers, verbose=True)
    
    # Filter by minimum yield if specified
    if args.min_yield:
        div_infos = [d for d in div_infos if d.dividend_yield >= args.min_yield / 100]
    
    print("\n" + "=" * 60)
    print("📊 DIVIDEND INFORMATION")
    print("=" * 60)
    
    for div_info in div_infos:
        print()
        print(tracker.format_dividend_info(div_info))
    
    if alerts:
        print("\n" + "=" * 60)
        print(f"⚠️ ALERTS ({len(alerts)} total)")
        print("=" * 60)
        
        for alert in alerts[:10]:  # Show top 10
            print(tracker.format_alert(alert))
    
    print(f"\n✅ Scan complete. {len(div_infos)} stocks analyzed, {len(alerts)} alerts generated.")


def cmd_watchlist(args):
    """Scan default watchlist"""
    args.tickers = DEFAULT_DIVIDEND_WATCHLIST
    cmd_scan(args)


def cmd_calendar(args):
    """Show upcoming ex-dividend dates"""
    tracker = DividendTracker()
    days = args.days or 30
    
    # Use cached data or scan watchlist
    tickers = args.tickers if args.tickers else DEFAULT_DIVIDEND_WATCHLIST
    
    print(f"\n📅 Ex-Dividend Calendar (Next {days} days)")
    print("=" * 60)
    
    calendar = tracker.get_upcoming_exdates(tickers, days_ahead=days)
    
    if not calendar:
        print("\n  No upcoming ex-dividend dates found.\n")
        return
    
    print(f"\n{'Date':<12} {'Ticker':<8} {'Amount':<10} {'Yield':<8} {'Days':<6}")
    print("-" * 50)
    
    for event in calendar:
        print(f"{event['ex_date']:<12} {event['ticker']:<8} ${event['amount_est']:<9.2f} {event['yield']*100:<7.2f}% {event['days_until']:<6}")
    
    print(f"\n✅ {len(calendar)} upcoming ex-dates found.")


def cmd_yields(args):
    """Show yield rankings"""
    tracker = DividendTracker()
    
    tickers = args.tickers if args.tickers else DEFAULT_DIVIDEND_WATCHLIST
    
    print("\n📈 Dividend Yield Rankings")
    print("=" * 60)
    
    rankings = tracker.get_yield_rankings(tickers)
    
    if not rankings:
        print("\n  No dividend-paying stocks found.\n")
        return
    
    print(f"\n{'Rank':<6} {'Ticker':<8} {'Yield':<8} {'Payout':<10} {'Annual Div':<12} {'Change'}")
    print("-" * 60)
    
    for i, r in enumerate(rankings[:20], 1):  # Top 20
        payout_str = f"{r['payout_ratio']*100:.1f}%" if r['payout_ratio'] else "N/A"
        print(f"{i:<6} {r['ticker']:<8} {r['yield']*100:<7.2f}% {payout_str:<10} ${r['annual_dividend']:<11.2f} {r['last_change']}")
    
    print(f"\n✅ Showing top {min(20, len(rankings))} of {len(rankings)} dividend payers.")


def cmd_alerts(args):
    """Show recent alerts"""
    tracker = DividendTracker()
    
    alerts_file = tracker.alerts_file
    
    if not os.path.exists(alerts_file):
        print("\n  No alerts found. Run a scan first.\n")
        return
    
    with open(alerts_file, 'r') as f:
        alerts = json.load(f)
    
    # Filter by ticker if specified
    if args.ticker:
        alerts = [a for a in alerts if a['ticker'] == args.ticker.upper()]
    
    # Filter by type if specified
    if args.type:
        alerts = [a for a in alerts if a['alert_type'] == args.type.upper()]
    
    print("\n⚠️ Recent Dividend Alerts")
    print("=" * 60)
    
    if not alerts:
        print("\n  No matching alerts found.\n")
        return
    
    # Show most recent first
    for alert in reversed(alerts[-20:]):
        severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(alert['severity'], "⚪")
        print(f"\n{severity_emoji} [{alert['ticker']}] {alert['alert_type']}")
        print(f"   {alert['message']}")
        print(f"   📅 {alert['timestamp'][:10]}")
    
    print(f"\n✅ Showing {min(20, len(alerts))} of {len(alerts)} alerts.")


def cmd_export(args):
    """Export data to CSV"""
    tracker = DividendTracker()
    
    output = args.output or f"dividends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    tickers = args.tickers if args.tickers else DEFAULT_DIVIDEND_WATCHLIST
    
    print(f"\n📤 Exporting dividend data to {output}...")
    
    div_infos, _ = tracker.scan_watchlist(tickers, verbose=False)
    
    with open(output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Ticker', 'Name', 'Price', 'Annual Dividend', 'Yield %',
            'Payout Ratio %', 'Ex-Date', 'Frequency', 'Last Change', 'Last Change %'
        ])
        
        for d in div_infos:
            writer.writerow([
                d.ticker,
                d.name,
                f"{d.current_price:.2f}",
                f"{d.annual_dividend:.2f}",
                f"{d.dividend_yield*100:.2f}",
                f"{d.payout_ratio*100:.1f}" if d.payout_ratio else "N/A",
                d.ex_date or "N/A",
                d.frequency,
                d.last_change_type,
                f"{d.last_change_pct*100:.1f}"
            ])
    
    print(f"✅ Exported {len(div_infos)} records to {output}")


def cmd_clear(args):
    """Clear cache files"""
    tracker = DividendTracker()
    
    files_to_clear = []
    
    if args.all or args.cache:
        files_to_clear.append(tracker.cache_file)
    
    if args.all or args.alerts:
        files_to_clear.append(tracker.alerts_file)
    
    for f in files_to_clear:
        if os.path.exists(f):
            os.remove(f)
            print(f"🗑️ Deleted {os.path.basename(f)}")
        else:
            print(f"⚠️ {os.path.basename(f)} not found")
    
    print("✅ Cache cleared.")


def main():
    parser = argparse.ArgumentParser(
        description="Dividend Calendar + Yield Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py scan JNJ KO PG           # Scan specific tickers
  python cli.py scan JNJ --min-yield 3   # Only show >3% yield
  python cli.py watchlist                # Scan default watchlist
  python cli.py calendar                 # Show next 30 days ex-dates
  python cli.py calendar --days 60       # Show next 60 days
  python cli.py yields                   # Show yield rankings
  python cli.py alerts                   # Show recent alerts
  python cli.py alerts --ticker T        # Alerts for specific ticker
  python cli.py export -o my_divs.csv    # Export to CSV
  python cli.py clear --all              # Clear all cache files
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # scan command
    scan_parser = subparsers.add_parser('scan', help='Scan tickers for dividend info')
    scan_parser.add_argument('tickers', nargs='+', help='Ticker symbols to scan')
    scan_parser.add_argument('--min-yield', type=float, help='Minimum yield %% filter')
    
    # watchlist command
    watchlist_parser = subparsers.add_parser('watchlist', help='Scan default dividend watchlist')
    watchlist_parser.add_argument('--min-yield', type=float, help='Minimum yield %% filter')
    
    # calendar command
    calendar_parser = subparsers.add_parser('calendar', help='Show upcoming ex-dividend dates')
    calendar_parser.add_argument('--days', type=int, default=30, help='Days to look ahead (default: 30)')
    calendar_parser.add_argument('tickers', nargs='*', help='Optional: specific tickers')
    
    # yields command
    yields_parser = subparsers.add_parser('yields', help='Show yield rankings')
    yields_parser.add_argument('tickers', nargs='*', help='Optional: specific tickers')
    
    # alerts command
    alerts_parser = subparsers.add_parser('alerts', help='Show recent alerts')
    alerts_parser.add_argument('--ticker', help='Filter by ticker')
    alerts_parser.add_argument('--type', help='Filter by alert type')
    
    # export command
    export_parser = subparsers.add_parser('export', help='Export to CSV')
    export_parser.add_argument('-o', '--output', help='Output filename')
    export_parser.add_argument('tickers', nargs='*', help='Optional: specific tickers')
    
    # clear command
    clear_parser = subparsers.add_parser('clear', help='Clear cache files')
    clear_parser.add_argument('--all', action='store_true', help='Clear all files')
    clear_parser.add_argument('--cache', action='store_true', help='Clear cache only')
    clear_parser.add_argument('--alerts', action='store_true', help='Clear alerts only')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    commands = {
        'scan': cmd_scan,
        'watchlist': cmd_watchlist,
        'calendar': cmd_calendar,
        'yields': cmd_yields,
        'alerts': cmd_alerts,
        'export': cmd_export,
        'clear': cmd_clear
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
