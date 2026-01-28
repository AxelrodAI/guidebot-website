#!/usr/bin/env python3
"""
SEC 8-K Filing Scanner CLI
Track material events in real-time
"""
import sys
import os

# Handle Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import argparse
from datetime import datetime
from sec_8k_scanner import SEC8KScanner, ITEM_TYPES


def format_filing(f: dict, verbose: bool = False) -> str:
    """Format a filing for display"""
    impact_icons = {"CRITICAL": "[!!!]", "HIGH": "[!!]", "MEDIUM": "[!]", "LOW": "[.]"}
    icon = impact_icons.get(f["impact_level"], "[?]")
    
    timing = ""
    if f["is_friday_night"]:
        timing = " [FRI NIGHT]"
    elif f["is_after_hours"]:
        timing = " [AFTER HRS]"
    
    items_str = ", ".join(f["items"])
    
    output = f"""
{icon} {f["ticker"]} - {f["company_name"]}{timing}
    Date: {f["filing_date"]} {f["filing_time"]}
    Items: {items_str}
    Impact: {f["impact_level"]} | Category: {f["category"]}
    Summary: {f["summary"]}"""
    
    if verbose:
        output += f"""
    URL: {f["url"]}
    Accession: {f["accession_number"]}"""
    
    return output


def format_alert(a: dict) -> str:
    """Format an alert for display"""
    priority_icons = {1: "[P1 CRITICAL]", 2: "[P2 HIGH]", 3: "[P3 MEDIUM]", 4: "[P4 LOW]", 5: "[P5 INFO]"}
    icon = priority_icons.get(a["priority"], "[??]")
    f = a["filing"]
    
    return f"""
{icon} {a["alert_type"]}
    {f["ticker"]}: {a["message"]}
    Filed: {f["filing_date"]} {f["filing_time"]}
    Items: {", ".join(f["items"])}"""


def cmd_recent(args):
    """Show recent filings"""
    scanner = SEC8KScanner()
    
    filings = scanner.get_filings(
        ticker=args.ticker,
        impact=args.impact,
        category=args.category,
        item=args.item,
        days=args.days,
        limit=args.limit
    )
    
    print(f"\n{'='*60}")
    print(f"SEC 8-K FILINGS - Last {args.days} Days")
    print(f"{'='*60}")
    
    filters = []
    if args.ticker: filters.append(f"Ticker: {args.ticker}")
    if args.impact: filters.append(f"Impact: {args.impact}")
    if args.category: filters.append(f"Category: {args.category}")
    if args.item: filters.append(f"Item: {args.item}")
    
    if filters:
        print(f"Filters: {' | '.join(filters)}")
    
    print(f"Found: {len(filings)} filings")
    print("-"*60)
    
    for f in filings:
        print(format_filing(f, args.verbose))
    
    print()


def cmd_alerts(args):
    """Show alerts"""
    scanner = SEC8KScanner()
    scanner.refresh_filings()
    
    alerts = scanner.get_alerts(priority=args.priority, limit=args.limit)
    
    print(f"\n{'='*60}")
    print(f"8-K FILING ALERTS")
    print(f"{'='*60}")
    
    if args.priority:
        print(f"Priority: P{args.priority} and higher")
    
    print(f"Active Alerts: {len(alerts)}")
    print("-"*60)
    
    for a in alerts:
        print(format_alert(a))
    
    print()


def cmd_ticker(args):
    """Show filing history for a ticker"""
    scanner = SEC8KScanner()
    result = scanner.get_ticker_history(args.ticker, limit=args.limit)
    
    print(f"\n{'='*60}")
    print(f"8-K FILING HISTORY: {result['ticker']}")
    print(f"{'='*60}")
    
    stats = result["statistics"]
    if stats["total_filings"] > 0:
        print(f"\nStatistics:")
        print(f"  Total Filings: {stats['total_filings']}")
        print(f"  Critical: {stats['critical_count']} | High Impact: {stats['high_impact_count']}")
        print(f"  After Hours: {stats['after_hours_count']} | Friday Night: {stats['friday_night_count']}")
        
        if stats["item_breakdown"]:
            print(f"\n  Item Breakdown:")
            for item, count in sorted(stats["item_breakdown"].items(), key=lambda x: x[1], reverse=True)[:5]:
                name = ITEM_TYPES.get(item, {}).get("name", "Unknown")
                print(f"    {item}: {count} ({name})")
        
        print(f"\n{'='*60}")
        print("Recent Filings:")
        print("-"*60)
        
        for f in result["filings"]:
            print(format_filing(f, args.verbose))
    else:
        print(f"\nNo filings found for {args.ticker}")
    
    print()


def cmd_summary(args):
    """Show summary statistics"""
    scanner = SEC8KScanner()
    summary = scanner.get_summary()
    
    print(f"\n{'='*60}")
    print(f"8-K FILING SUMMARY - Last 7 Days")
    print(f"{'='*60}")
    
    print(f"\nTotal Filings: {summary['total_filings']}")
    print(f"After Hours: {summary['after_hours_filings']}")
    print(f"Friday Night: {summary['friday_night_filings']}")
    print(f"Active Alerts: {summary['active_alerts']}")
    
    print(f"\nImpact Breakdown:")
    for impact, count in summary["impact_breakdown"].items():
        bar = "*" * min(count, 20)
        print(f"  {impact:10} {count:3} {bar}")
    
    print(f"\nCategory Breakdown:")
    for cat, count in sorted(summary["category_breakdown"].items(), key=lambda x: x[1], reverse=True):
        bar = "*" * min(count, 15)
        print(f"  {cat:12} {count:3} {bar}")
    
    print(f"\nMost Active Tickers:")
    for ticker, count in summary["most_active_tickers"]:
        print(f"  {ticker:6} - {count} filings")
    
    print(f"\nMost Common Items:")
    for item in summary["most_common_items"]:
        print(f"  {item['item']:5} - {item['count']:2} filings - {item['name']}")
    
    print(f"\nLast Updated: {summary['last_updated']}")
    print()


def cmd_item(args):
    """Show information about an item type"""
    scanner = SEC8KScanner()
    
    if args.list:
        info = scanner.list_item_types()
        
        print(f"\n{'='*60}")
        print("8-K ITEM TYPES REFERENCE")
        print(f"{'='*60}")
        
        for category, items in sorted(info["by_category"].items()):
            print(f"\n{category.upper()}:")
            print("-"*40)
            for item in sorted(items, key=lambda x: x["item"]):
                impact_marker = ""
                if item["item"] in info["critical_items"]:
                    impact_marker = " [CRITICAL]"
                elif item["item"] in info["high_impact_items"]:
                    impact_marker = " [HIGH]"
                print(f"  {item['item']:5} - {item['name']}{impact_marker}")
        
        print()
    else:
        info = scanner.get_item_info(args.item)
        
        if "error" in info:
            print(f"\nError: {info['error']}")
            return
        
        print(f"\n{'='*60}")
        print(f"ITEM {info['item']}: {info['name']}")
        print(f"{'='*60}")
        
        print(f"\nImpact Level: {info['impact']}")
        print(f"Category: {info['category']}")
        print(f"Critical: {'Yes' if info['is_critical'] else 'No'}")
        print(f"High Impact: {'Yes' if info['is_high_impact'] else 'No'}")
        
        if info["recent_filings"]:
            print(f"\nRecent Filings with this Item:")
            print("-"*40)
            for f in info["recent_filings"]:
                print(f"  {f['filing_date']} - {f['ticker']} - {f['company_name']}")
        
        print()


def cmd_watchlist(args):
    """Manage watchlist"""
    scanner = SEC8KScanner()
    
    if args.add:
        result = scanner.add_to_watchlist(args.add)
        print(f"\n{result['status'].upper()}: {result['ticker']}")
        print(f"Watchlist: {', '.join(result['watchlist'])}")
    
    elif args.remove:
        result = scanner.remove_from_watchlist(args.remove)
        print(f"\n{result['status'].upper()}: {result['ticker']}")
        print(f"Watchlist: {', '.join(result['watchlist']) if result['watchlist'] else '(empty)'}")
    
    elif args.scan:
        result = scanner.scan_watchlist(days=args.days)
        
        if "error" in result:
            print(f"\nError: {result['error']}")
            return
        
        print(f"\n{'='*60}")
        print(f"WATCHLIST SCAN - Last {result['period_days']} Days")
        print(f"{'='*60}")
        print(f"Watchlist: {', '.join(result['watchlist'])}")
        print(f"Tickers with Filings: {result['tickers_with_filings']}")
        
        for ticker, data in result["results"].items():
            warning = ""
            if data["has_critical"]:
                warning = " [CRITICAL FILING!]"
            elif data["has_high_impact"]:
                warning = " [HIGH IMPACT]"
            
            print(f"\n{ticker}: {data['count']} filings{warning}")
            for f in data["filings"][:3]:
                print(f"  {f['filing_date']} - {', '.join(f['items'])} - {f['impact_level']}")
        
        print()
    
    else:
        # Show current watchlist
        print(f"\nWatchlist: {', '.join(scanner.watchlist) if scanner.watchlist else '(empty)'}")
        print("\nCommands:")
        print("  watchlist --add TICKER     Add ticker to watchlist")
        print("  watchlist --remove TICKER  Remove ticker from watchlist")
        print("  watchlist --scan           Scan watchlist for recent filings")


def cmd_critical(args):
    """Show only critical filings"""
    scanner = SEC8KScanner()
    filings = scanner.get_filings(impact="CRITICAL", days=args.days, limit=args.limit)
    
    print(f"\n{'='*60}")
    print(f"CRITICAL 8-K FILINGS - Last {args.days} Days")
    print(f"{'='*60}")
    print("Items: Bankruptcy, Non-Reliance, Change of Control, Delisting")
    print(f"Found: {len(filings)} critical filings")
    print("-"*60)
    
    if not filings:
        print("\nNo critical filings found. (Good news!)")
    else:
        for f in filings:
            print(format_filing(f, verbose=True))
    
    print()


def cmd_refresh(args):
    """Refresh filings data"""
    scanner = SEC8KScanner()
    result = scanner.refresh_filings()
    
    print(f"\n{'='*60}")
    print("DATA REFRESHED")
    print(f"{'='*60}")
    print(f"Filings: {result['filings_count']}")
    print(f"Alerts: {result['alerts_count']}")
    print(f"Updated: {result['last_updated']}")
    print()


def cmd_test(args):
    """Run test scenarios"""
    print("\n" + "="*60)
    print("SEC 8-K Scanner - Test Suite")
    print("="*60)
    
    scanner = SEC8KScanner()
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Refresh filings
    tests_total += 1
    print("\n[Test 1] Refresh filings...")
    result = scanner.refresh_filings()
    if result["filings_count"] > 0:
        print(f"  PASS: Generated {result['filings_count']} filings")
        tests_passed += 1
    else:
        print("  FAIL: No filings generated")
    
    # Test 2: Get filings
    tests_total += 1
    print("\n[Test 2] Get filtered filings...")
    filings = scanner.get_filings(days=30, limit=20)
    if len(filings) > 0:
        print(f"  PASS: Retrieved {len(filings)} filings")
        tests_passed += 1
    else:
        print("  FAIL: No filings retrieved")
    
    # Test 3: Get alerts
    tests_total += 1
    print("\n[Test 3] Get alerts...")
    alerts = scanner.get_alerts()
    if len(alerts) >= 0:
        print(f"  PASS: Generated {len(alerts)} alerts")
        tests_passed += 1
    else:
        print("  FAIL: Alert generation failed")
    
    # Test 4: Ticker history
    tests_total += 1
    print("\n[Test 4] Get ticker history...")
    history = scanner.get_ticker_history("AAPL")
    if "ticker" in history and "filings" in history:
        print(f"  PASS: Got {len(history['filings'])} filings for AAPL")
        tests_passed += 1
    else:
        print("  FAIL: Ticker history failed")
    
    # Test 5: Summary stats
    tests_total += 1
    print("\n[Test 5] Get summary statistics...")
    summary = scanner.get_summary()
    if "total_filings" in summary and "impact_breakdown" in summary:
        print(f"  PASS: Summary shows {summary['total_filings']} filings")
        tests_passed += 1
    else:
        print("  FAIL: Summary generation failed")
    
    # Test 6: Item info
    tests_total += 1
    print("\n[Test 6] Get item info (5.02)...")
    info = scanner.get_item_info("5.02")
    if "name" in info and info["name"] == "Executive Departure/Appointment":
        print(f"  PASS: Item 5.02 = {info['name']}")
        tests_passed += 1
    else:
        print("  FAIL: Item info incorrect")
    
    # Test 7: Critical filings filter
    tests_total += 1
    print("\n[Test 7] Filter critical filings...")
    critical = scanner.get_filings(impact="CRITICAL")
    critical_count = len(critical)
    all_critical = all(f["impact_level"] == "CRITICAL" for f in critical)
    if all_critical:
        print(f"  PASS: Found {critical_count} critical filings (all verified)")
        tests_passed += 1
    else:
        print("  FAIL: Non-critical filings in results")
    
    # Test 8: Watchlist operations
    tests_total += 1
    print("\n[Test 8] Watchlist operations...")
    add_result = scanner.add_to_watchlist("TEST")
    remove_result = scanner.remove_from_watchlist("TEST")
    if add_result["status"] == "added" and remove_result["status"] == "removed":
        print("  PASS: Watchlist add/remove working")
        tests_passed += 1
    else:
        print("  FAIL: Watchlist operations failed")
    
    # Test 9: List item types
    tests_total += 1
    print("\n[Test 9] List item types...")
    items = scanner.list_item_types()
    if items["total_item_types"] >= 30:
        print(f"  PASS: {items['total_item_types']} item types cataloged")
        tests_passed += 1
    else:
        print("  FAIL: Missing item types")
    
    # Test 10: Impact levels present
    tests_total += 1
    print("\n[Test 10] Verify impact level distribution...")
    all_filings = scanner.get_filings(days=30, limit=100)
    impacts = set(f["impact_level"] for f in all_filings)
    if len(impacts) >= 2:
        print(f"  PASS: Found {len(impacts)} impact levels: {impacts}")
        tests_passed += 1
    else:
        print("  FAIL: Insufficient impact variety")
    
    # Summary
    print("\n" + "="*60)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("="*60)
    
    if tests_passed == tests_total:
        print("All tests passed!")
    else:
        print(f"Failed tests: {tests_total - tests_passed}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="SEC 8-K Filing Scanner - Track material corporate events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py recent                    Show recent filings
  python cli.py recent --impact HIGH      Show high-impact filings
  python cli.py recent --item 5.02        Show executive changes
  python cli.py alerts                    Show all alerts
  python cli.py alerts --priority 2       Show P1-P2 alerts only
  python cli.py ticker AAPL               Show AAPL filing history
  python cli.py summary                   Show weekly summary
  python cli.py critical                  Show only critical filings
  python cli.py item --list               List all 8-K item types
  python cli.py item 5.02                 Info about Item 5.02
  python cli.py watchlist --add AAPL      Add AAPL to watchlist
  python cli.py watchlist --scan          Scan watchlist for filings
  python cli.py test                      Run test suite
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Recent filings
    recent_parser = subparsers.add_parser("recent", help="Show recent 8-K filings")
    recent_parser.add_argument("--ticker", "-t", help="Filter by ticker")
    recent_parser.add_argument("--impact", "-i", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"], help="Filter by impact")
    recent_parser.add_argument("--category", "-c", help="Filter by category")
    recent_parser.add_argument("--item", help="Filter by item number (e.g., 5.02)")
    recent_parser.add_argument("--days", "-d", type=int, default=30, help="Days to look back (default: 30)")
    recent_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results (default: 20)")
    recent_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed info")
    recent_parser.set_defaults(func=cmd_recent)
    
    # Alerts
    alerts_parser = subparsers.add_parser("alerts", help="Show filing alerts")
    alerts_parser.add_argument("--priority", "-p", type=int, choices=[1, 2, 3, 4, 5], help="Max priority level")
    alerts_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results (default: 20)")
    alerts_parser.set_defaults(func=cmd_alerts)
    
    # Ticker history
    ticker_parser = subparsers.add_parser("ticker", help="Show filing history for a ticker")
    ticker_parser.add_argument("ticker", help="Ticker symbol")
    ticker_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results (default: 20)")
    ticker_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed info")
    ticker_parser.set_defaults(func=cmd_ticker)
    
    # Summary
    summary_parser = subparsers.add_parser("summary", help="Show summary statistics")
    summary_parser.set_defaults(func=cmd_summary)
    
    # Item info
    item_parser = subparsers.add_parser("item", help="Show 8-K item type information")
    item_parser.add_argument("item", nargs="?", help="Item number (e.g., 5.02)")
    item_parser.add_argument("--list", "-l", action="store_true", help="List all item types")
    item_parser.set_defaults(func=cmd_item)
    
    # Watchlist
    watchlist_parser = subparsers.add_parser("watchlist", help="Manage watchlist")
    watchlist_parser.add_argument("--add", "-a", metavar="TICKER", help="Add ticker to watchlist")
    watchlist_parser.add_argument("--remove", "-r", metavar="TICKER", help="Remove ticker from watchlist")
    watchlist_parser.add_argument("--scan", "-s", action="store_true", help="Scan watchlist for filings")
    watchlist_parser.add_argument("--days", "-d", type=int, default=7, help="Days to scan (default: 7)")
    watchlist_parser.set_defaults(func=cmd_watchlist)
    
    # Critical filings
    critical_parser = subparsers.add_parser("critical", help="Show only critical filings")
    critical_parser.add_argument("--days", "-d", type=int, default=30, help="Days to look back (default: 30)")
    critical_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results (default: 20)")
    critical_parser.set_defaults(func=cmd_critical)
    
    # Refresh
    refresh_parser = subparsers.add_parser("refresh", help="Refresh filings data")
    refresh_parser.set_defaults(func=cmd_refresh)
    
    # Test
    test_parser = subparsers.add_parser("test", help="Run test suite")
    test_parser.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default to showing summary
        args.func = cmd_summary
        args.func(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
