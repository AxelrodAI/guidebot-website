#!/usr/bin/env python3
"""
Options Flow Scanner CLI

Commands:
  scan [TICKERS...]   - Scan tickers for unusual activity
  watchlist           - Scan default watchlist  
  alerts              - Show recent alerts
  summary             - Show summary statistics
  export              - Export alerts to CSV
  clear               - Clear cache and alerts
"""

import argparse
import sys
import json
import os
from datetime import datetime

# Fix Windows encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from options_scanner import OptionsFlowScanner, DEFAULT_WATCHLIST

def cmd_scan(args):
    """Scan specific tickers"""
    tickers = args.tickers if args.tickers else DEFAULT_WATCHLIST[:5]
    
    print("=" * 60)
    print("🔍 OPTIONS FLOW SCANNER")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    scanner = OptionsFlowScanner()
    alerts = scanner.scan_watchlist(tickers, verbose=not args.quiet)
    
    # Filter by score if specified
    if args.min_score:
        alerts = [a for a in alerts if a.score >= args.min_score]
    
    # Filter by type if specified
    if args.type:
        alerts = [a for a in alerts if a.alert_type == args.type.upper()]
    
    if not alerts:
        print("\n✅ No unusual activity detected.")
        return
    
    print("\n" + "=" * 60)
    print(f"🚨 TOP {min(args.limit, len(alerts))} UNUSUAL ACTIVITIES")
    print("=" * 60)
    
    for alert in alerts[:args.limit]:
        print()
        print(scanner.format_alert(alert))
    
    if len(alerts) > args.limit:
        print(f"\n... and {len(alerts) - args.limit} more alerts")
    
    # Show summary
    summary = scanner.get_summary(alerts)
    print("\n" + "-" * 40)
    print(f"📊 Total: {summary['total_alerts']} alerts | Premium: ${summary.get('total_premium_traded', 0):,.0f}")

def cmd_watchlist(args):
    """Scan default watchlist"""
    args.tickers = DEFAULT_WATCHLIST
    cmd_scan(args)

def cmd_alerts(args):
    """Show recent alerts"""
    scanner = OptionsFlowScanner()
    
    if not os.path.exists(scanner.alerts_file):
        print("No alerts found. Run 'scan' first.")
        return
    
    with open(scanner.alerts_file, 'r') as f:
        alerts = json.load(f)
    
    if args.ticker:
        alerts = [a for a in alerts if a['ticker'].upper() == args.ticker.upper()]
    
    if args.type:
        alerts = [a for a in alerts if a['alert_type'] == args.type.upper()]
    
    # Sort by timestamp descending
    alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    print("=" * 60)
    print("📋 RECENT ALERTS")
    print("=" * 60)
    
    for alert in alerts[:args.limit]:
        emoji = {
            "VOLUME_SPIKE": "📈",
            "LARGE_PREMIUM": "💰",
            "OI_CHANGE": "📊",
            "PC_RATIO": "⚖️",
            "BLOCK_TRADE": "🔷"
        }.get(alert['alert_type'], "🔔")
        
        opt_emoji = "📗" if alert.get('option_type') == "call" else "📕"
        
        print(f"\n{emoji} [{alert['ticker']}] {alert['alert_type']} - Score: {alert.get('score', 0)}/100")
        print(f"   {opt_emoji} {alert.get('option_type', '').upper()} ${alert.get('strike', 0)} exp {alert.get('expiry', 'N/A')}")
        print(f"   💵 Premium: ${alert.get('premium_traded', 0):,.0f}")
        print(f"   ℹ️  {alert.get('details', '')}")
        print(f"   🕐 {alert.get('timestamp', 'N/A')[:19]}")

def cmd_summary(args):
    """Show summary statistics"""
    scanner = OptionsFlowScanner()
    
    if not os.path.exists(scanner.alerts_file):
        print("No alerts found. Run 'scan' first.")
        return
    
    with open(scanner.alerts_file, 'r') as f:
        alerts = json.load(f)
    
    if not alerts:
        print("No alerts found.")
        return
    
    # Calculate stats
    by_type = {}
    by_ticker = {}
    total_premium = 0
    call_count = 0
    put_count = 0
    
    for a in alerts:
        by_type[a['alert_type']] = by_type.get(a['alert_type'], 0) + 1
        by_ticker[a['ticker']] = by_ticker.get(a['ticker'], 0) + 1
        total_premium += a.get('premium_traded', 0)
        if a.get('option_type') == 'call':
            call_count += 1
        elif a.get('option_type') == 'put':
            put_count += 1
    
    print("=" * 60)
    print("📊 OPTIONS FLOW SUMMARY")
    print("=" * 60)
    
    print(f"\n📈 Total Alerts: {len(alerts)}")
    print(f"💰 Total Premium Tracked: ${total_premium:,.0f}")
    print(f"📗 Calls: {call_count} | 📕 Puts: {put_count}")
    
    print("\n📋 By Alert Type:")
    for atype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"   {atype}: {count}")
    
    print("\n🎯 Most Active Tickers:")
    for ticker, count in sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {ticker}: {count} alerts")

def cmd_export(args):
    """Export alerts to CSV"""
    scanner = OptionsFlowScanner()
    
    if not os.path.exists(scanner.alerts_file):
        print("No alerts found. Run 'scan' first.")
        return
    
    with open(scanner.alerts_file, 'r') as f:
        alerts = json.load(f)
    
    import csv
    
    output_file = args.output or "options_flow_export.csv"
    
    with open(output_file, 'w', newline='') as f:
        if alerts:
            writer = csv.DictWriter(f, fieldnames=alerts[0].keys())
            writer.writeheader()
            writer.writerows(alerts)
    
    print(f"✅ Exported {len(alerts)} alerts to {output_file}")

def cmd_clear(args):
    """Clear cache and alerts"""
    scanner = OptionsFlowScanner()
    
    files_to_clear = []
    if args.cache or args.all:
        files_to_clear.append(scanner.cache_file)
    if args.alerts or args.all:
        files_to_clear.append(scanner.alerts_file)
    
    for f in files_to_clear:
        if os.path.exists(f):
            os.remove(f)
            print(f"🗑️ Deleted {os.path.basename(f)}")
    
    if not files_to_clear:
        print("Specify --cache, --alerts, or --all")

def main():
    parser = argparse.ArgumentParser(
        description="🔍 Options Flow / Unusual Activity Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py scan AAPL TSLA NVDA    # Scan specific tickers
  python cli.py scan --min-score 70    # Show only high-score alerts
  python cli.py watchlist              # Scan default watchlist (15 stocks)
  python cli.py alerts --ticker TSLA   # Show recent TSLA alerts
  python cli.py summary                # Show summary statistics
  python cli.py export -o flow.csv     # Export to CSV

Alert Types:
  VOLUME_SPIKE   - Volume > 5x average
  LARGE_PREMIUM  - Premium traded > $500k
  OI_CHANGE      - Open Interest change > 20%
  PC_RATIO       - Unusual Put/Call ratio
  BLOCK_TRADE    - Large block (> 1000 contracts)
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # scan command
    scan_parser = subparsers.add_parser('scan', help='Scan tickers for unusual activity')
    scan_parser.add_argument('tickers', nargs='*', help='Tickers to scan (default: top 5)')
    scan_parser.add_argument('-l', '--limit', type=int, default=20, help='Max alerts to show')
    scan_parser.add_argument('-s', '--min-score', type=int, help='Minimum score filter')
    scan_parser.add_argument('-t', '--type', help='Filter by alert type')
    scan_parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')
    scan_parser.set_defaults(func=cmd_scan)
    
    # watchlist command
    wl_parser = subparsers.add_parser('watchlist', help='Scan default watchlist')
    wl_parser.add_argument('-l', '--limit', type=int, default=20, help='Max alerts to show')
    wl_parser.add_argument('-s', '--min-score', type=int, help='Minimum score filter')
    wl_parser.add_argument('-t', '--type', help='Filter by alert type')
    wl_parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')
    wl_parser.set_defaults(func=cmd_watchlist)
    
    # alerts command
    alerts_parser = subparsers.add_parser('alerts', help='Show recent alerts')
    alerts_parser.add_argument('--ticker', help='Filter by ticker')
    alerts_parser.add_argument('-t', '--type', help='Filter by alert type')
    alerts_parser.add_argument('-l', '--limit', type=int, default=20, help='Max alerts to show')
    alerts_parser.set_defaults(func=cmd_alerts)
    
    # summary command
    summary_parser = subparsers.add_parser('summary', help='Show summary statistics')
    summary_parser.set_defaults(func=cmd_summary)
    
    # export command
    export_parser = subparsers.add_parser('export', help='Export alerts to CSV')
    export_parser.add_argument('-o', '--output', help='Output file (default: options_flow_export.csv)')
    export_parser.set_defaults(func=cmd_export)
    
    # clear command
    clear_parser = subparsers.add_parser('clear', help='Clear cache and alerts')
    clear_parser.add_argument('--cache', action='store_true', help='Clear cache')
    clear_parser.add_argument('--alerts', action='store_true', help='Clear alerts')
    clear_parser.add_argument('--all', action='store_true', help='Clear everything')
    clear_parser.set_defaults(func=cmd_clear)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)

if __name__ == "__main__":
    main()
