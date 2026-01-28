#!/usr/bin/env python3
"""
CLI interface for 13F Holdings Change Tracker
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from tracker import SEC13FTracker
from config import SUPERINVESTORS, OUTPUT_DIR


def cmd_track(args):
    """Track all superinvestors or specific funds"""
    tracker = SEC13FTracker(cache_enabled=not args.no_cache)
    
    if args.fund:
        # Track specific fund(s)
        results = []
        for fund in args.fund:
            # Find by name or CIK
            cik = None
            fund_name = fund
            
            # Check if it's a CIK
            if fund.isdigit() or (fund.startswith("0") and fund[1:].isdigit()):
                cik = fund.zfill(10)
                fund_name = f"CIK {cik}"
            else:
                # Look up by name
                for name, c in SUPERINVESTORS.items():
                    if fund.lower() in name.lower():
                        cik = c
                        fund_name = name
                        break
            
            if cik:
                result = tracker.track_fund(fund_name, cik)
                results.append(result)
            else:
                print(f"Unknown fund: {fund}")
    else:
        # Track all
        results = tracker.track_all_superinvestors()
    
    # Generate report
    if args.format == "excel":
        tracker.generate_excel_report(results, args.output)
    elif args.format == "json":
        output = {
            "generated": datetime.now().isoformat(),
            "results": [
                {
                    "fund": r.get("fund"),
                    "cik": r.get("cik"),
                    "current_period": r.get("current_period"),
                    "summary": r.get("summary"),
                    "significant_changes": [
                        {
                            "cusip": c.cusip,
                            "name": c.name,
                            "change_type": c.change_type,
                            "prev_shares": c.prev_shares,
                            "curr_shares": c.curr_shares,
                            "shares_change_pct": c.shares_change_pct if c.shares_change_pct != float('inf') else None
                        }
                        for c in r.get("significant_changes", [])
                    ] if "significant_changes" in r else []
                }
                for r in results
            ]
        }
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"JSON report saved: {args.output}")
        else:
            print(json.dumps(output, indent=2))
    
    # Show alerts
    if args.alerts:
        alerts = tracker.generate_alerts(results)
        if alerts:
            print("\n=== ALERTS ===")
            for alert in alerts:
                # Handle potential Unicode issues on Windows console
                try:
                    print(alert)
                except UnicodeEncodeError:
                    print(alert.encode('ascii', 'replace').decode('ascii'))


def cmd_list(args):
    """List tracked superinvestors"""
    print("Tracked Superinvestors:")
    print("-" * 50)
    for name, cik in sorted(SUPERINVESTORS.items()):
        print(f"  {name:<30} CIK: {cik}")


def cmd_filings(args):
    """List recent 13F filings for a fund"""
    tracker = SEC13FTracker()
    
    cik = None
    fund_name = args.fund
    
    # Check if it's a CIK
    if args.fund.isdigit() or (args.fund.startswith("0") and args.fund[1:].isdigit()):
        cik = args.fund.zfill(10)
    else:
        # Look up by name
        for name, c in SUPERINVESTORS.items():
            if args.fund.lower() in name.lower():
                cik = c
                fund_name = name
                break
    
    if not cik:
        print(f"Unknown fund: {args.fund}")
        return
    
    print(f"\nRecent 13F filings for {fund_name} (CIK: {cik}):")
    print("-" * 60)
    
    filings = tracker.find_13f_filings(cik, limit=args.limit)
    
    for f in filings:
        print(f"  {f['form']:<10} Report: {f['report_date']}  Filed: {f['filing_date']}")
        print(f"             Accession: {f['accession_number']}")


def cmd_holdings(args):
    """Show current holdings for a fund"""
    tracker = SEC13FTracker()
    
    cik = None
    fund_name = args.fund
    
    if args.fund.isdigit() or (args.fund.startswith("0") and args.fund[1:].isdigit()):
        cik = args.fund.zfill(10)
    else:
        for name, c in SUPERINVESTORS.items():
            if args.fund.lower() in name.lower():
                cik = c
                fund_name = name
                break
    
    if not cik:
        print(f"Unknown fund: {args.fund}")
        return
    
    filings = tracker.find_13f_filings(cik, limit=1)
    if not filings:
        print("No filings found")
        return
    
    filing = filings[0]
    print(f"\nHoldings for {fund_name}")
    print(f"Report date: {filing['report_date']}")
    print("-" * 80)
    
    holdings = tracker.get_13f_holdings(cik, filing['accession_number'])
    
    # Sort by value descending
    holdings.sort(key=lambda h: h.value, reverse=True)
    
    # Print top holdings
    limit = args.limit or 25
    for i, h in enumerate(holdings[:limit], 1):
        print(f"{i:3}. {h.name[:35]:<35} {h.shares:>15,} shares  ${h.value:>12,}K")
    
    if len(holdings) > limit:
        print(f"\n... and {len(holdings) - limit} more positions")
    
    total_value = sum(h.value for h in holdings)
    print(f"\nTotal holdings: {len(holdings)} positions, ${total_value:,}K")


def cmd_clear_cache(args):
    """Clear the cache"""
    from config import CACHE_DIR
    import shutil
    
    cache_path = Path(CACHE_DIR)
    if cache_path.exists():
        shutil.rmtree(cache_path)
        cache_path.mkdir()
        print("Cache cleared.")
    else:
        print("No cache to clear.")


def main():
    parser = argparse.ArgumentParser(
        description="13F Holdings Change Tracker - Track superinvestor moves"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # track command
    track_parser = subparsers.add_parser("track", help="Track 13F changes")
    track_parser.add_argument("-f", "--fund", action="append", help="Specific fund(s) to track")
    track_parser.add_argument("-o", "--output", help="Output filename")
    track_parser.add_argument("--format", choices=["excel", "json"], default="excel")
    track_parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    track_parser.add_argument("--alerts", action="store_true", help="Show alerts")
    track_parser.set_defaults(func=cmd_track)
    
    # list command
    list_parser = subparsers.add_parser("list", help="List tracked superinvestors")
    list_parser.set_defaults(func=cmd_list)
    
    # filings command
    filings_parser = subparsers.add_parser("filings", help="List recent filings for a fund")
    filings_parser.add_argument("fund", help="Fund name or CIK")
    filings_parser.add_argument("-n", "--limit", type=int, default=8, help="Number of filings")
    filings_parser.set_defaults(func=cmd_filings)
    
    # holdings command
    holdings_parser = subparsers.add_parser("holdings", help="Show current holdings")
    holdings_parser.add_argument("fund", help="Fund name or CIK")
    holdings_parser.add_argument("-n", "--limit", type=int, help="Number of holdings to show")
    holdings_parser.set_defaults(func=cmd_holdings)
    
    # clear-cache command
    cache_parser = subparsers.add_parser("clear-cache", help="Clear cached data")
    cache_parser.set_defaults(func=cmd_clear_cache)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default: run full tracking
        args.fund = None
        args.output = None
        args.format = "excel"
        args.no_cache = False
        args.alerts = True
        cmd_track(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
