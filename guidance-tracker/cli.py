#!/usr/bin/env python3
"""
Guidance vs Actuals Tracker - CLI Interface
Command-line tool for analyzing management guidance accuracy.

Author: PM3

Commands:
    analyze <TICKER>    - Analyze single ticker
    track [TICKERS...]  - Track multiple tickers (or default watchlist)
    report              - Generate full report for watchlist
    sandbagging         - Show companies with high sandbagging scores
    credibility         - Rank companies by credibility score
    alerts              - Show all companies with active alerts
    watchlist           - Manage watchlist (list/add/remove)
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
from datetime import datetime
from pathlib import Path

# Import from tracker module
from tracker import (
    analyze_guidance_patterns,
    track_watchlist,
    generate_report,
    export_to_json,
    export_to_excel,
    DEFAULT_WATCHLIST,
    DATA_DIR
)


def cmd_analyze(args):
    """Analyze a single ticker."""
    ticker = args.ticker.upper()
    print(f"\n[*] Analyzing guidance patterns for {ticker}...\n")
    
    result = analyze_guidance_patterns(ticker)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"📊 {result['ticker']} - {result.get('company_name', 'N/A')}")
    print(f"   Sector: {result.get('sector', 'Unknown')}")
    print(f"   Pattern: {result.get('pattern', 'Unknown')}")
    print()
    
    if result.get("accuracy_metrics") and "error" not in result.get("accuracy_metrics", {}):
        m = result["accuracy_metrics"]
        print("   ACCURACY METRICS:")
        print(f"   ├─ Beat Rate: {m['beat_rate']}% ({m['beats']} beats / {m['total_quarters']} quarters)")
        print(f"   ├─ Avg Surprise: {m['avg_surprise_pct']:+.2f}%")
        print(f"   ├─ Credibility Score: {m['credibility_score']}/100")
        print(f"   ├─ Sandbagging Score: {m['sandbagging_score']}/100")
        print(f"   └─ Consistency Score: {m['consistency_score']}/100")
        
        if m.get("last_4q_surprises"):
            print(f"\n   Last 4Q Surprises: {[f'{s:+.1f}%' for s in m['last_4q_surprises']]}")
    else:
        print("   ⚠️ Insufficient earnings history data")
    
    if result.get("alerts"):
        print("\n   ⚠️ ALERTS:")
        for alert in result["alerts"]:
            print(f"   • {alert}")
    
    # EPS info
    if result.get("forward_eps") or result.get("trailing_eps"):
        print(f"\n   Forward EPS: ${result.get('forward_eps', 'N/A')}")
        print(f"   Trailing EPS: ${result.get('trailing_eps', 'N/A')}")
    
    print()


def cmd_track(args):
    """Track multiple tickers."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\n📈 Tracking {len(tickers)} companies...\n")
    
    results = track_watchlist(tickers)
    
    # Display summary table
    print("\n" + "=" * 80)
    print(f"{'Ticker':<8} {'Pattern':<20} {'Beat%':<8} {'Cred':<6} {'Sand':<6} {'Alerts':<30}")
    print("=" * 80)
    
    for r in results:
        ticker = r["ticker"]
        pattern = r.get("pattern", "N/A")[:18]
        
        if r.get("accuracy_metrics") and "error" not in r.get("accuracy_metrics", {}):
            m = r["accuracy_metrics"]
            beat = f"{m['beat_rate']:.0f}%"
            cred = f"{m['credibility_score']:.0f}"
            sand = f"{m['sandbagging_score']:.0f}"
        else:
            beat = cred = sand = "N/A"
        
        alerts = "⚠️" if r.get("alerts") else ""
        
        print(f"{ticker:<8} {pattern:<20} {beat:<8} {cred:<6} {sand:<6} {alerts}")
    
    print("=" * 80)
    print()
    
    if args.export:
        json_file = export_to_json(results)
        print(f"📄 Exported to: {json_file}")
        
        try:
            excel_file = export_to_excel(results)
            print(f"📊 Excel exported to: {excel_file}")
        except:
            pass


def cmd_report(args):
    """Generate full report."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\n📋 Generating report for {len(tickers)} companies...\n")
    
    results = track_watchlist(tickers)
    report = generate_report(results)
    
    print(report)
    
    # Export
    json_file = export_to_json(results)
    print(f"\n📄 JSON: {json_file}")
    
    try:
        excel_file = export_to_excel(results)
        print(f"📊 Excel: {excel_file}")
    except:
        pass


def cmd_sandbagging(args):
    """Show companies with high sandbagging scores."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\n🎯 Identifying potential sandbagging in {len(tickers)} companies...\n")
    
    results = track_watchlist(tickers)
    
    # Filter and sort by sandbagging score
    sandbagging = []
    for r in results:
        if r.get("accuracy_metrics") and "error" not in r.get("accuracy_metrics", {}):
            score = r["accuracy_metrics"].get("sandbagging_score", 0)
            if score > 30:  # Threshold for potential sandbagging
                sandbagging.append((r, score))
    
    sandbagging.sort(key=lambda x: x[1], reverse=True)
    
    if not sandbagging:
        print("✅ No significant sandbagging detected.")
        return
    
    print("⚠️ POTENTIAL SANDBAGGING DETECTED:")
    print("-" * 60)
    
    for r, score in sandbagging:
        m = r["accuracy_metrics"]
        print(f"\n🎯 {r['ticker']} - Sandbagging Score: {score:.0f}/100")
        print(f"   Beat Rate: {m['beat_rate']}% (beats {m['beats']}/{m['total_quarters']} quarters)")
        print(f"   Avg Surprise: {m['avg_surprise_pct']:+.2f}%")
        print(f"   Interpretation: Management may be lowballing guidance")
    
    print()


def cmd_credibility(args):
    """Rank companies by credibility score."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\n⭐ Ranking {len(tickers)} companies by management credibility...\n")
    
    results = track_watchlist(tickers)
    
    # Filter and sort by credibility
    ranked = []
    for r in results:
        if r.get("accuracy_metrics") and "error" not in r.get("accuracy_metrics", {}):
            cred = r["accuracy_metrics"].get("credibility_score", 0)
            ranked.append((r, cred))
    
    ranked.sort(key=lambda x: x[1], reverse=True)
    
    print("MANAGEMENT CREDIBILITY RANKING")
    print("=" * 60)
    print(f"{'Rank':<6} {'Ticker':<8} {'Score':<8} {'Pattern':<25}")
    print("-" * 60)
    
    for i, (r, cred) in enumerate(ranked, 1):
        emoji = "🏆" if i <= 3 else "⚠️" if cred < 50 else "  "
        print(f"{emoji} {i:<4} {r['ticker']:<8} {cred:<8.0f} {r.get('pattern', 'N/A')}")
    
    print()


def cmd_alerts(args):
    """Show all active alerts."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\n🚨 Checking alerts for {len(tickers)} companies...\n")
    
    results = track_watchlist(tickers)
    
    # Collect all alerts
    all_alerts = []
    for r in results:
        for alert in r.get("alerts", []):
            all_alerts.append((r["ticker"], r.get("company_name", ""), alert))
    
    if not all_alerts:
        print("✅ No alerts! All companies have acceptable guidance accuracy.")
        return
    
    print(f"⚠️ {len(all_alerts)} ALERTS FOUND:")
    print("-" * 70)
    
    for ticker, name, alert in all_alerts:
        print(f"\n[{ticker}] {name}")
        print(f"   {alert}")
    
    print()


def cmd_watchlist(args):
    """Manage watchlist."""
    watchlist_file = DATA_DIR / "watchlist.json"
    
    # Load or use defaults
    if watchlist_file.exists():
        with open(watchlist_file) as f:
            watchlist = json.load(f)["tickers"]
    else:
        watchlist = DEFAULT_WATCHLIST.copy()
    
    if args.action == "list":
        print("\n📋 CURRENT WATCHLIST:")
        print("-" * 40)
        for t in sorted(watchlist):
            print(f"   • {t}")
        print(f"\nTotal: {len(watchlist)} companies")
    
    elif args.action == "add":
        ticker = args.ticker.upper()
        if ticker not in watchlist:
            watchlist.append(ticker)
            with open(watchlist_file, "w") as f:
                json.dump({"tickers": watchlist}, f, indent=2)
            print(f"✅ Added {ticker} to watchlist")
        else:
            print(f"⚠️ {ticker} already in watchlist")
    
    elif args.action == "remove":
        ticker = args.ticker.upper()
        if ticker in watchlist:
            watchlist.remove(ticker)
            with open(watchlist_file, "w") as f:
                json.dump({"tickers": watchlist}, f, indent=2)
            print(f"✅ Removed {ticker} from watchlist")
        else:
            print(f"⚠️ {ticker} not in watchlist")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Guidance vs Actuals Tracker - Analyze management guidance accuracy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cli.py analyze AAPL           # Analyze single ticker
    python cli.py track AAPL MSFT GOOGL  # Track specific tickers
    python cli.py report                 # Full report for watchlist
    python cli.py sandbagging            # Find potential sandbagging
    python cli.py credibility            # Rank by credibility
    python cli.py alerts                 # Show all alerts
    python cli.py watchlist list         # Show watchlist
    python cli.py watchlist add NVDA     # Add to watchlist
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze single ticker")
    p_analyze.add_argument("ticker", help="Stock ticker symbol")
    p_analyze.set_defaults(func=cmd_analyze)
    
    # track
    p_track = subparsers.add_parser("track", help="Track multiple tickers")
    p_track.add_argument("tickers", nargs="*", help="Tickers (or leave empty for watchlist)")
    p_track.add_argument("--export", "-e", action="store_true", help="Export to JSON/Excel")
    p_track.set_defaults(func=cmd_track)
    
    # report
    p_report = subparsers.add_parser("report", help="Generate full report")
    p_report.add_argument("tickers", nargs="*", help="Tickers (or leave empty for watchlist)")
    p_report.set_defaults(func=cmd_report)
    
    # sandbagging
    p_sand = subparsers.add_parser("sandbagging", help="Find potential sandbagging")
    p_sand.add_argument("tickers", nargs="*", help="Tickers (or leave empty for watchlist)")
    p_sand.set_defaults(func=cmd_sandbagging)
    
    # credibility
    p_cred = subparsers.add_parser("credibility", help="Rank by credibility score")
    p_cred.add_argument("tickers", nargs="*", help="Tickers (or leave empty for watchlist)")
    p_cred.set_defaults(func=cmd_credibility)
    
    # alerts
    p_alerts = subparsers.add_parser("alerts", help="Show all active alerts")
    p_alerts.add_argument("tickers", nargs="*", help="Tickers (or leave empty for watchlist)")
    p_alerts.set_defaults(func=cmd_alerts)
    
    # watchlist
    p_watch = subparsers.add_parser("watchlist", help="Manage watchlist")
    p_watch.add_argument("action", choices=["list", "add", "remove"], help="Action")
    p_watch.add_argument("ticker", nargs="?", help="Ticker (for add/remove)")
    p_watch.set_defaults(func=cmd_watchlist)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
