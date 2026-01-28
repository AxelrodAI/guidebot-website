#!/usr/bin/env python3
"""
Correlation Matrix Monitor CLI
Track rolling correlations, detect regime changes, analyze diversification.
"""

import argparse
import json
import sys
from datetime import datetime

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from correlation_tracker import (
    analyze_portfolio_correlations,
    compare_correlation_periods,
    get_benchmark_correlations,
    generate_alerts,
    load_cache,
    DEFAULT_WATCHLIST
)


def format_correlation(val: float) -> str:
    """Format correlation with indicator."""
    if val is None:
        return "  N/A "
    if val >= 0.8:
        return f" {val:+.2f}*"  # Very high
    elif val <= -0.2:
        return f" {val:+.2f}-"  # Negative (hedge)
    else:
        return f" {val:+.2f} "


def cmd_analyze(args):
    """Full correlation analysis for portfolio."""
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"\n  Fetching data for {len(tickers)} tickers...")
    result = analyze_portfolio_correlations(tickers, window=args.window, refresh=args.refresh)
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    
    if "error" in result:
        print(f"  Error: {result['error']}\n")
        return
    
    print(f"\n{'='*70}")
    print(f"  CORRELATION ANALYSIS - {args.window} Day Window")
    print(f"{'='*70}\n")
    
    # Diversification summary
    div = result["diversification"]
    status_emoji = {
        "EXCELLENT": "[OK]",
        "GOOD": "[+]",
        "MODERATE": "[~]",
        "POOR": "[!]"
    }
    
    print(f"  DIVERSIFICATION SCORE")
    print(f"  {'-'*66}")
    print(f"  Status:     {status_emoji.get(div.get('status', ''), '')} {div.get('status', 'N/A')} (Score: {div.get('score', 0)}/100)")
    print(f"  Avg Corr:   {div.get('average_correlation', 0):.3f}")
    print(f"  Max Corr:   {div.get('max_correlation', 0):.3f}")
    print(f"  Min Corr:   {div.get('min_correlation', 0):.3f}")
    print(f"  Pairs:      {div.get('num_pairs_analyzed', 0)} analyzed")
    
    # Correlation matrix
    print(f"\n  CORRELATION MATRIX ({args.window}d)")
    print(f"  {'-'*66}")
    
    matrix = result.get("correlation_matrix", {})
    cols = list(matrix.keys())
    
    if cols:
        # Header
        header = "        " + "".join(f"{c[:6]:>8}" for c in cols)
        print(f"  {header}")
        
        # Rows
        for row in cols:
            row_str = f"  {row[:6]:<6}"
            for col in cols:
                val = matrix.get(row, {}).get(col)
                row_str += format_correlation(val)
            print(row_str)
    
    # High correlation pairs
    high_pairs = div.get("high_correlation_pairs", [])
    if high_pairs:
        print(f"\n  [!] HIGH CORRELATION PAIRS (>0.8)")
        print(f"  {'-'*66}")
        for pair in high_pairs:
            print(f"  >> {pair['pair'][0]} <-> {pair['pair'][1]}: {pair['correlation']:.3f}")
    
    # Hedges
    hedges = div.get("hedges", [])
    if hedges:
        print(f"\n  [OK] NEGATIVE CORRELATIONS (HEDGES)")
        print(f"  {'-'*66}")
        for hedge in hedges:
            print(f"  << {hedge['pair'][0]} <-> {hedge['pair'][1]}: {hedge['correlation']:.3f}")
    
    # Alerts
    alerts = result.get("alerts", [])
    if alerts:
        print(f"\n  [!!] CORRELATION ALERTS")
        print(f"  {'-'*66}")
        for alert in alerts[:5]:
            alert_type = alert.get("type", "ALERT")
            print(f"  [{alert_type}] {alert.get('ticker', '?')} vs {alert.get('benchmark', '?')}")
            if "recent_corr" in alert:
                print(f"      Recent: {alert['recent_corr']:.3f} | Historical: {alert.get('historical_corr', 0):.3f}")
            if "description" in alert:
                print(f"      {alert['description']}")
    
    # Suggestions
    suggestions = result.get("suggestions", [])
    if suggestions:
        print(f"\n  REBALANCING SUGGESTIONS")
        print(f"  {'-'*66}")
        for sug in suggestions:
            severity_emoji = {"HIGH": "[!!!]", "MEDIUM": "[!!]", "LOW": "[!]"}
            print(f"  {severity_emoji.get(sug.get('severity', 'LOW'), '[!]')} {sug.get('action', '')}")
    
    print()


def cmd_matrix(args):
    """Show just the correlation matrix."""
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"\n  Fetching data...")
    result = analyze_portfolio_correlations(tickers, window=args.window)
    
    if args.json:
        print(json.dumps(result.get("correlation_matrix", {}), indent=2, default=str))
        return
    
    print(f"\n{'='*70}")
    print(f"  CORRELATION MATRIX - {args.window} Day Rolling")
    print(f"{'='*70}\n")
    
    matrix = result.get("correlation_matrix", {})
    cols = list(matrix.keys())
    
    if not cols:
        print("  No data available\n")
        return
    
    # Header
    header = "          " + "".join(f"{c[:7]:>9}" for c in cols)
    print(f"  {header}")
    print(f"  {'-'*len(header)}")
    
    # Rows
    for row in cols:
        row_str = f"  {row[:7]:<8}"
        for col in cols:
            val = matrix.get(row, {}).get(col)
            if val is not None:
                if row == col:
                    row_str += "    1.00 "
                elif val >= 0.8:
                    row_str += f"  {val:+.2f}* "
                elif val <= -0.2:
                    row_str += f"  {val:+.2f}- "
                else:
                    row_str += f"  {val:+.2f}  "
            else:
                row_str += "    N/A  "
        print(row_str)
    
    print(f"\n  Legend: * = High (>0.8), - = Negative (hedge)")
    print()


def cmd_benchmark(args):
    """Show correlations vs major benchmarks."""
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    benchmarks = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
    if args.benchmarks:
        benchmarks = [b.strip().upper() for b in args.benchmarks.split(",")]
    
    print(f"\n  Fetching data...")
    cache = load_cache()
    result = get_benchmark_correlations(tickers, benchmarks=benchmarks, window=args.window, cache=cache)
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    
    print(f"\n{'='*70}")
    print(f"  BENCHMARK CORRELATIONS - {args.window} Day Window")
    print(f"{'='*70}\n")
    
    # Filter benchmarks that aren't in tickers list
    display_benchmarks = [b for b in benchmarks if b not in tickers]
    
    # Header
    header = "  Ticker  " + "".join(f"{b[:6]:>9}" for b in display_benchmarks)
    print(header)
    print(f"  {'-'*66}")
    
    for ticker in tickers:
        if ticker not in result:
            continue
        row_str = f"  {ticker:<8}"
        for benchmark in display_benchmarks:
            val = result[ticker].get(benchmark)
            row_str += format_correlation(val)
        print(row_str)
    
    print(f"\n  Benchmarks: SPY (S&P500), QQQ (Nasdaq), IWM (Russell), TLT (Bonds), GLD (Gold)")
    print()


def cmd_alerts(args):
    """Show correlation regime change alerts."""
    tickers = DEFAULT_WATCHLIST
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"\n  Scanning {len(tickers)} tickers for alerts...")
    cache = load_cache()
    alerts = generate_alerts(tickers, window=args.window, cache=cache)
    
    if args.json:
        print(json.dumps(alerts, indent=2, default=str))
        return
    
    print(f"\n{'='*70}")
    print(f"  CORRELATION ALERTS")
    print(f"{'='*70}\n")
    
    if not alerts:
        print("  No correlation regime changes detected.\n")
        return
    
    alert_emoji = {
        "REGIME_CHANGE": "[~]",
        "BREAKDOWN": "[!]",
        "CONVERGENCE": "[!!]"
    }
    
    for alert in alerts:
        emoji = alert_emoji.get(alert.get("type"), "[*]")
        print(f"  {emoji} {alert.get('ticker', '?')} vs {alert.get('benchmark', '?')}")
        
        if alert.get("type") == "REGIME_CHANGE":
            direction = "UP" if alert.get("direction") == "INCREASE" else "DOWN"
            print(f"      Correlation {direction}: {alert.get('historical_corr', 0):.3f} -> {alert.get('recent_corr', 0):.3f}")
            print(f"      Change: {alert.get('change', 0):+.3f}")
        elif alert.get("description"):
            print(f"      {alert['description']}")
            print(f"      Historical: {alert.get('historical_corr', 0):.3f} -> Recent: {alert.get('recent_corr', 0):.3f}")
        print()


def cmd_compare(args):
    """Compare correlations over different time periods."""
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"\n  Comparing {args.short}d vs {args.long}d correlations...")
    result = compare_correlation_periods(tickers, window1=args.short, window2=args.long)
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    
    print(f"\n{'='*70}")
    print(f"  CORRELATION COMPARISON: {args.short}d vs {args.long}d")
    print(f"{'='*70}\n")
    
    changes = result.get("significant_changes", [])
    if changes:
        print(f"  SIGNIFICANT CHANGES (>0.2 difference)")
        print(f"  {'-'*66}")
        print(f"  {'Pair':<20} {f'{args.short}d':>10} {f'{args.long}d':>10} {'Change':>10} {'Direction':>12}")
        print(f"  {'-'*66}")
        
        for change in changes:
            pair_str = f"{change['pair'][0]}/{change['pair'][1]}"
            short_key = f"corr_{args.short}d"
            long_key = f"corr_{args.long}d"
            direction_emoji = "^" if change.get("direction") == "INCREASING" else "v"
            print(f"  {pair_str:<20} {change.get(short_key, 0):>+10.3f} {change.get(long_key, 0):>+10.3f} "
                  f"{change.get('change', 0):>+10.3f} {direction_emoji:>12}")
    else:
        print("  No significant correlation changes detected between periods.\n")
    
    print()


def cmd_scan(args):
    """Quick scan of watchlist."""
    tickers = DEFAULT_WATCHLIST
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"\n  Scanning {len(tickers)} tickers...")
    result = analyze_portfolio_correlations(tickers, window=args.window)
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    
    print(f"\n{'='*70}")
    print(f"  PORTFOLIO SCAN - {len(result.get('tickers', []))} Assets")
    print(f"{'='*70}\n")
    
    div = result.get("diversification", {})
    
    # Quick summary
    score = div.get("score", 0)
    status_bar = "=" * (score // 5) + "-" * (20 - score // 5)
    print(f"  Diversification: [{status_bar}] {score}/100 ({div.get('status', 'N/A')})")
    print(f"  Avg Correlation: {div.get('average_correlation', 0):.3f}")
    
    # High risk pairs
    high_pairs = div.get("high_correlation_pairs", [])
    if high_pairs:
        print(f"\n  [!] {len(high_pairs)} highly correlated pair(s) found:")
        for p in high_pairs[:3]:
            print(f"      {p['pair'][0]} <-> {p['pair'][1]}: {p['correlation']:.3f}")
    
    # Alerts count
    alerts = result.get("alerts", [])
    if alerts:
        print(f"\n  [!!] {len(alerts)} correlation alert(s)")
    
    # Suggestions count
    sugs = result.get("suggestions", [])
    if sugs:
        print(f"\n  Suggestions:")
        for s in sugs[:2]:
            action = s.get('action', '')
            print(f"    - {action[:70]}{'...' if len(action) > 70 else ''}")
    
    print()


def cmd_export(args):
    """Export correlation data to JSON file."""
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"\n  Generating report...")
    result = analyze_portfolio_correlations(tickers, window=args.window)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  Exported to {args.output}")
    else:
        print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="Correlation Matrix Monitor - Track portfolio correlations"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    p_analyze = subparsers.add_parser('analyze', help='Full correlation analysis')
    p_analyze.add_argument('tickers', help='Comma-separated ticker symbols')
    p_analyze.add_argument('--window', '-w', type=int, default=60, help='Rolling window in days (default: 60)')
    p_analyze.add_argument('--refresh', '-r', action='store_true', help='Force refresh data')
    p_analyze.add_argument('--json', action='store_true', help='JSON output')
    p_analyze.set_defaults(func=cmd_analyze)
    
    # Matrix command
    p_matrix = subparsers.add_parser('matrix', help='Show correlation matrix')
    p_matrix.add_argument('tickers', help='Comma-separated ticker symbols')
    p_matrix.add_argument('--window', '-w', type=int, default=60, help='Rolling window in days')
    p_matrix.add_argument('--json', action='store_true', help='JSON output')
    p_matrix.set_defaults(func=cmd_matrix)
    
    # Benchmark command
    p_bench = subparsers.add_parser('benchmark', help='Correlations vs benchmarks')
    p_bench.add_argument('tickers', help='Comma-separated ticker symbols')
    p_bench.add_argument('--benchmarks', '-b', help='Custom benchmarks (default: SPY,QQQ,IWM,TLT,GLD)')
    p_bench.add_argument('--window', '-w', type=int, default=60, help='Rolling window in days')
    p_bench.add_argument('--json', action='store_true', help='JSON output')
    p_bench.set_defaults(func=cmd_benchmark)
    
    # Alerts command
    p_alerts = subparsers.add_parser('alerts', help='Correlation regime alerts')
    p_alerts.add_argument('--tickers', '-t', help='Comma-separated tickers (default: watchlist)')
    p_alerts.add_argument('--window', '-w', type=int, default=60, help='Rolling window in days')
    p_alerts.add_argument('--json', action='store_true', help='JSON output')
    p_alerts.set_defaults(func=cmd_alerts)
    
    # Compare command
    p_compare = subparsers.add_parser('compare', help='Compare correlation periods')
    p_compare.add_argument('tickers', help='Comma-separated ticker symbols')
    p_compare.add_argument('--short', '-s', type=int, default=30, help='Short window (default: 30)')
    p_compare.add_argument('--long', '-l', type=int, default=90, help='Long window (default: 90)')
    p_compare.add_argument('--json', action='store_true', help='JSON output')
    p_compare.set_defaults(func=cmd_compare)
    
    # Scan command
    p_scan = subparsers.add_parser('scan', help='Quick portfolio scan')
    p_scan.add_argument('--tickers', '-t', help='Comma-separated tickers (default: watchlist)')
    p_scan.add_argument('--window', '-w', type=int, default=60, help='Rolling window in days')
    p_scan.add_argument('--json', action='store_true', help='JSON output')
    p_scan.set_defaults(func=cmd_scan)
    
    # Export command
    p_export = subparsers.add_parser('export', help='Export to JSON')
    p_export.add_argument('tickers', help='Comma-separated ticker symbols')
    p_export.add_argument('--window', '-w', type=int, default=60, help='Rolling window in days')
    p_export.add_argument('-o', '--output', help='Output file path')
    p_export.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default: quick scan
        class DefaultArgs:
            tickers = None
            window = 60
            json = False
        cmd_scan(DefaultArgs())
    else:
        args.func(args)


if __name__ == "__main__":
    main()
