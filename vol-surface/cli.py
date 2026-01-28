#!/usr/bin/env python3
"""
Volatility Surface Monitor - CLI Interface
Track IV, skew, term structure across options chains.

Author: PM3

Commands:
    scan [TICKERS...]  - Scan tickers for vol opportunities
    analyze TICKER     - Deep dive on single ticker
    smile TICKER       - Show vol smile (IV across strikes)
    alerts             - Show all current alerts
    term               - Show term structure comparison
    export             - Export analysis to JSON
"""

import argparse
from datetime import datetime

from vol_surface import (
    analyze_vol_surface,
    scan_watchlist,
    generate_vol_report,
    get_vol_smile,
    export_to_json,
    DEFAULT_WATCHLIST
)


def cmd_scan(args):
    """Scan tickers for vol opportunities."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\nScanning {len(tickers)} tickers for volatility opportunities...\n")
    
    results = scan_watchlist(tickers)
    report = generate_vol_report(results)
    
    print(report)
    
    if args.export:
        json_file = export_to_json(results)
        print(f"Exported to: {json_file}")


def cmd_analyze(args):
    """Deep analysis of single ticker."""
    ticker = args.ticker.upper()
    
    print(f"\nAnalyzing volatility surface for {ticker}...\n")
    
    analysis = analyze_vol_surface(ticker)
    
    if "error" in analysis:
        print(f"Error: {analysis['error']}")
        return
    
    print(f"{'='*60}")
    print(f"{ticker} VOLATILITY SURFACE ANALYSIS")
    print(f"{'='*60}")
    print()
    print(f"Current Price: ${analysis['current_price']:.2f}")
    print(f"Current IV: {analysis['current_iv']:.1f}%" if analysis['current_iv'] else "Current IV: N/A")
    print(f"Term Structure: {analysis['term_structure']}")
    print(f"Put/Call Ratio: {analysis['put_call_ratio']:.2f}")
    
    # Alerts
    if analysis['alerts']:
        print(f"\n{'-'*60}")
        print("ALERTS:")
        for alert in analysis['alerts']:
            severity = {"HIGH": "[!!!]", "MEDIUM": "[!!]", "LOW": "[!]"}.get(alert["severity"], "")
            print(f"  {severity} {alert['message']}")
    
    # Expirations breakdown
    print(f"\n{'-'*60}")
    print("TERM STRUCTURE BY EXPIRATION:")
    print(f"{'Exp':<12} {'DTE':<6} {'ATM IV':<10} {'Skew':<8} {'P Vol':<10} {'C Vol':<10}")
    print("-" * 60)
    
    for exp in analysis['expirations']:
        exp_date = exp['expiration'][-5:]  # MM-DD
        dte = str(exp['dte'])
        atm_iv = f"{exp['atm_avg_iv']:.1f}%" if exp['atm_avg_iv'] else "N/A"
        skew = f"{exp['skew']:+.1f}" if exp['skew'] else "N/A"
        p_vol = f"{exp['put_volume']:,}" if exp['put_volume'] else "0"
        c_vol = f"{exp['call_volume']:,}" if exp['call_volume'] else "0"
        
        print(f"{exp_date:<12} {dte:<6} {atm_iv:<10} {skew:<8} {p_vol:<10} {c_vol:<10}")
    
    print()


def cmd_smile(args):
    """Show volatility smile."""
    ticker = args.ticker.upper()
    
    print(f"\nFetching vol smile for {ticker}...\n")
    
    smile_data = get_vol_smile(ticker, args.expiration)
    
    if "error" in smile_data:
        print(f"Error: {smile_data['error']}")
        return
    
    print(f"{'='*60}")
    print(f"{ticker} VOLATILITY SMILE")
    print(f"Expiration: {smile_data['expiration']}")
    print(f"Current Price: ${smile_data['current_price']:.2f}")
    print(f"{'='*60}")
    print()
    print(f"{'Strike':<10} {'Moneyness':<12} {'Call IV':<10} {'Put IV':<10} {'Avg IV':<10}")
    print("-" * 60)
    
    # Filter to show interesting strikes (around ATM)
    strikes = [s for s in smile_data['smile'] if -20 <= s['moneyness'] <= 20]
    
    for s in strikes:
        strike = f"${s['strike']:.0f}"
        moneyness = f"{s['moneyness']:+.1f}%"
        call_iv = f"{s['call_iv']:.1f}%" if s['call_iv'] else "N/A"
        put_iv = f"{s['put_iv']:.1f}%" if s['put_iv'] else "N/A"
        avg_iv = f"{s['avg_iv']:.1f}%" if s['avg_iv'] else "N/A"
        
        # Highlight ATM
        marker = " *" if abs(s['moneyness']) < 3 else ""
        
        print(f"{strike:<10} {moneyness:<12} {call_iv:<10} {put_iv:<10} {avg_iv:<10}{marker}")
    
    print()
    print("* = Near ATM")
    print()


def cmd_alerts(args):
    """Show all current vol alerts."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\nScanning {len(tickers)} tickers for alerts...\n")
    
    results = scan_watchlist(tickers)
    
    all_alerts = []
    for r in results:
        if "error" not in r:
            for alert in r.get("alerts", []):
                all_alerts.append((r["ticker"], r.get("current_iv"), alert))
    
    if not all_alerts:
        print("No vol alerts at this time.")
        return
    
    # Sort by severity
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_alerts.sort(key=lambda x: severity_order.get(x[2]["severity"], 3))
    
    print(f"{'='*70}")
    print(f"VOLATILITY ALERTS ({len(all_alerts)} total)")
    print(f"{'='*70}")
    
    current_severity = None
    for ticker, iv, alert in all_alerts:
        if alert["severity"] != current_severity:
            current_severity = alert["severity"]
            print(f"\n--- {current_severity} SEVERITY ---")
        
        iv_str = f"(IV: {iv:.1f}%)" if iv else ""
        print(f"[{ticker}] {alert['message']} {iv_str}")
    
    print()


def cmd_term(args):
    """Show term structure comparison."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST[:5]
    
    print(f"\nComparing term structures for {len(tickers)} tickers...\n")
    
    results = scan_watchlist(tickers)
    
    print(f"{'='*70}")
    print("TERM STRUCTURE COMPARISON")
    print(f"{'='*70}")
    print()
    
    # Header
    print(f"{'Ticker':<8} {'Structure':<12} {'Near IV':<10} {'Far IV':<10} {'Diff':<10}")
    print("-" * 60)
    
    for r in results:
        if "error" in r:
            continue
        
        ticker = r["ticker"]
        structure = r.get("term_structure", "N/A")
        
        # Get near and far IV
        exps = r.get("expirations", [])
        near_iv = exps[0]["atm_avg_iv"] if exps and exps[0].get("atm_avg_iv") else None
        far_iv = exps[-1]["atm_avg_iv"] if exps and exps[-1].get("atm_avg_iv") else None
        
        near_str = f"{near_iv:.1f}%" if near_iv else "N/A"
        far_str = f"{far_iv:.1f}%" if far_iv else "N/A"
        diff_str = f"{near_iv - far_iv:+.1f}%" if near_iv and far_iv else "N/A"
        
        # Mark inverted
        marker = " <-- INVERTED" if structure == "INVERTED" else ""
        
        print(f"{ticker:<8} {structure:<12} {near_str:<10} {far_str:<10} {diff_str:<10}{marker}")
    
    print()
    print("INVERTED term structure often precedes significant moves.")
    print()


def cmd_export(args):
    """Export analysis to JSON."""
    tickers = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST
    
    print(f"\nExporting analysis for {len(tickers)} tickers...")
    
    results = scan_watchlist(tickers)
    output = args.output if args.output else None
    
    json_file = export_to_json(results, output)
    print(f"Exported to: {json_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Volatility Surface Monitor - Track IV, skew, term structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cli.py scan                    # Scan default watchlist
    python cli.py scan AAPL MSFT NVDA     # Scan specific tickers
    python cli.py analyze SPY             # Deep dive on SPY
    python cli.py smile AAPL              # Show vol smile
    python cli.py alerts                  # Show all alerts
    python cli.py term                    # Compare term structures
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # scan
    p_scan = subparsers.add_parser("scan", help="Scan tickers for vol opportunities")
    p_scan.add_argument("tickers", nargs="*", help="Tickers to scan")
    p_scan.add_argument("--export", "-e", action="store_true", help="Export to JSON")
    p_scan.set_defaults(func=cmd_scan)
    
    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Deep analysis of single ticker")
    p_analyze.add_argument("ticker", help="Ticker symbol")
    p_analyze.set_defaults(func=cmd_analyze)
    
    # smile
    p_smile = subparsers.add_parser("smile", help="Show volatility smile")
    p_smile.add_argument("ticker", help="Ticker symbol")
    p_smile.add_argument("--expiration", "-e", help="Specific expiration date")
    p_smile.set_defaults(func=cmd_smile)
    
    # alerts
    p_alerts = subparsers.add_parser("alerts", help="Show all current alerts")
    p_alerts.add_argument("tickers", nargs="*", help="Tickers to check")
    p_alerts.set_defaults(func=cmd_alerts)
    
    # term
    p_term = subparsers.add_parser("term", help="Compare term structures")
    p_term.add_argument("tickers", nargs="*", help="Tickers to compare")
    p_term.set_defaults(func=cmd_term)
    
    # export
    p_export = subparsers.add_parser("export", help="Export to JSON")
    p_export.add_argument("tickers", nargs="*", help="Tickers to export")
    p_export.add_argument("-o", "--output", help="Output file path")
    p_export.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default to scan
        args.tickers = None
        args.export = False
        cmd_scan(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
