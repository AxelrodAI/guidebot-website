#!/usr/bin/env python3
"""
Earnings Estimate Revision Tracker CLI
Track estimate revisions, beat/miss history, and revision momentum.

Usage:
    python cli.py estimates TICKER [--full]
    python cli.py history TICKER
    python cli.py revisions [--severity high|medium|low]
    python cli.py scan [--alert]
    python cli.py watch add TICKER
    python cli.py watch remove TICKER
    python cli.py watch list
    python cli.py momentum TICKER
    python cli.py compare TICKER1,TICKER2,...
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from estimate_tracker import (
    load_cache, save_cache, get_earnings_estimates, get_earnings_history,
    detect_revision, calculate_beat_miss_history, get_revision_momentum,
    load_watchlist, save_watchlist, load_alerts, scan_watchlist,
    print_estimate_summary, format_currency, EstimateSnapshot
)

SCRIPT_DIR = Path(__file__).parent


def cmd_estimates(args):
    """Get earnings estimates for a ticker."""
    cache = load_cache()
    
    print(f"Fetching estimates for {args.ticker}...")
    snapshot = get_earnings_estimates(args.ticker, cache)
    
    if not snapshot:
        print(f"Could not fetch estimates for {args.ticker}")
        return 1
    
    save_cache(cache)
    print_estimate_summary(snapshot)
    
    if args.full:
        # Also show beat/miss history
        history = calculate_beat_miss_history(args.ticker, cache)
        print("\nBEAT/MISS HISTORY:")
        print("-" * 40)
        print(f"  Quarters Tracked: {history['quarters_tracked']}")
        print(f"  Beats: {history['beats']} | Misses: {history['misses']} | Meets: {history['meets']}")
        print(f"  Beat Rate: {history['beat_rate']}%")
        if history.get('avg_surprise_pct'):
            sign = "+" if history['avg_surprise_pct'] > 0 else ""
            print(f"  Avg Surprise: {sign}{history['avg_surprise_pct']}%")
        
        # Recent quarters
        if history.get('history'):
            print("\n  Recent Quarters:")
            for q in history['history'][-4:]:
                est = q.get('eps_estimate', 'N/A')
                act = q.get('eps_actual', 'N/A')
                surp = q.get('surprise_pct')
                surp_str = f"{'+' if surp > 0 else ''}{surp:.1f}%" if surp is not None else "N/A"
                print(f"    {q['date']}: Est ${est} vs Act ${act} ({surp_str})")
        
        save_cache(cache)
    
    return 0


def cmd_history(args):
    """Get beat/miss history for a ticker."""
    cache = load_cache()
    
    print(f"Fetching earnings history for {args.ticker}...")
    result = get_earnings_history(args.ticker, cache)
    
    if not result:
        print(f"Could not fetch history for {args.ticker}")
        return 1
    
    save_cache(cache)
    
    history = calculate_beat_miss_history(args.ticker, cache)
    
    print(f"\n{'='*60}")
    print(f"EARNINGS HISTORY: {args.ticker}")
    print(f"{'='*60}")
    
    print(f"\nSUMMARY:")
    print("-" * 40)
    print(f"  Quarters Tracked: {history['quarters_tracked']}")
    print(f"  Beats: {history['beats']} ({history['beats']/history['quarters_tracked']*100:.0f}%)" if history['quarters_tracked'] else "  Beats: 0")
    print(f"  Misses: {history['misses']} ({history['misses']/history['quarters_tracked']*100:.0f}%)" if history['quarters_tracked'] else "  Misses: 0")
    print(f"  Meets: {history['meets']}")
    if history.get('avg_surprise_pct'):
        sign = "+" if history['avg_surprise_pct'] > 0 else ""
        print(f"  Avg Surprise: {sign}{history['avg_surprise_pct']}%")
    
    print(f"\nQUARTERLY RESULTS:")
    print("-" * 60)
    print(f"{'Quarter':<15}{'Estimate':>12}{'Actual':>12}{'Surprise':>12}{'Result':>10}")
    print("-" * 60)
    
    for q in result['history']:
        est = q.get('eps_estimate')
        act = q.get('eps_actual')
        surp = q.get('surprise_pct')
        
        est_str = f"${est:.2f}" if est else "N/A"
        act_str = f"${act:.2f}" if act else "N/A"
        
        if surp is not None:
            surp_str = f"{'+' if surp > 0 else ''}{surp:.1f}%"
            result_str = "BEAT" if surp > 1 else "MISS" if surp < -1 else "MEET"
        else:
            surp_str = "N/A"
            result_str = "N/A"
        
        print(f"{q['date']:<15}{est_str:>12}{act_str:>12}{surp_str:>12}{result_str:>10}")
    
    return 0


def cmd_revisions(args):
    """Show recent revision alerts."""
    alerts = load_alerts()
    
    if not alerts:
        print("No revision alerts recorded. Run 'python cli.py scan' to detect revisions.")
        return 0
    
    # Filter by severity if specified
    if args.severity:
        alerts = [a for a in alerts if a.get('severity') == args.severity]
    
    # Sort by timestamp (newest first)
    alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Limit to recent
    alerts = alerts[:20]
    
    print(f"\n{'='*70}")
    print("ESTIMATE REVISION ALERTS")
    print(f"{'='*70}")
    
    if not alerts:
        print("\nNo alerts matching criteria.")
        return 0
    
    print(f"\n{'Ticker':<8}{'Type':<12}{'Metric':<8}{'Period':<12}{'Change':>10}{'Severity':<10}")
    print("-" * 70)
    
    for alert in alerts:
        change_str = f"{'+' if alert['change_pct'] > 0 else ''}{alert['change_pct']:.1f}%"
        type_str = alert['alert_type'].upper()[:10]
        
        severity_indicator = {
            'high': '[!!!]',
            'medium': '[!!]',
            'low': '[!]'
        }.get(alert['severity'], '')
        
        print(f"{alert['ticker']:<8}{type_str:<12}{alert['metric'].upper():<8}"
              f"{alert['period']:<12}{change_str:>10}{severity_indicator:<10}")
    
    return 0


def cmd_scan(args):
    """Scan watchlist for estimate changes."""
    cache = load_cache()
    
    alerts = scan_watchlist(cache)
    save_cache(cache)
    
    if alerts:
        print(f"\n[ALERT] Found {len(alerts)} estimate revision(s)!")
        print("-" * 50)
        
        for alert in alerts:
            direction = "UP" if alert.change_pct > 0 else "DOWN"
            print(f"  {alert.ticker}: {alert.metric.upper()} {alert.period} {direction} {abs(alert.change_pct):.1f}%")
            print(f"    Old: {alert.old_estimate} -> New: {alert.new_estimate}")
        
        if args.alert:
            # Would integrate with notification system here
            print("\n[Would send alert notifications]")
    else:
        print("\nNo significant estimate revisions detected.")
    
    return 0


def cmd_watch(args):
    """Manage watchlist."""
    tickers = load_watchlist()
    
    if args.watch_action == "add":
        if not args.ticker:
            print("Usage: python cli.py watch add TICKER")
            return 1
        
        ticker = args.ticker.upper()
        if ticker not in tickers:
            tickers.append(ticker)
            save_watchlist(tickers)
            print(f"Added {ticker} to watchlist ({len(tickers)} total)")
        else:
            print(f"{ticker} already in watchlist")
        return 0
    
    elif args.watch_action == "remove":
        if not args.ticker:
            print("Usage: python cli.py watch remove TICKER")
            return 1
        
        ticker = args.ticker.upper()
        if ticker in tickers:
            tickers.remove(ticker)
            save_watchlist(tickers)
            print(f"Removed {ticker} from watchlist ({len(tickers)} remaining)")
        else:
            print(f"{ticker} not in watchlist")
        return 0
    
    elif args.watch_action == "list":
        if not tickers:
            print("Watchlist is empty.")
        else:
            print(f"\nWatchlist ({len(tickers)} tickers):")
            print("-" * 30)
            for t in sorted(tickers):
                print(f"  {t}")
        return 0
    
    elif args.watch_action == "clear":
        save_watchlist([])
        print("Watchlist cleared.")
        return 0
    
    return 1


def cmd_momentum(args):
    """Show estimate revision momentum."""
    cache = load_cache()
    
    # First fetch fresh data
    snapshot = get_earnings_estimates(args.ticker, cache)
    if not snapshot:
        print(f"Could not fetch data for {args.ticker}")
        return 1
    
    save_cache(cache)
    
    momentum = get_revision_momentum(args.ticker, cache)
    
    print(f"\n{'='*50}")
    print(f"REVISION MOMENTUM: {args.ticker}")
    print(f"{'='*50}")
    
    if momentum['momentum'] == 'insufficient_data':
        print("\nInsufficient historical data. Keep scanning to build history.")
        return 0
    
    momentum_indicators = {
        'strong_positive': '[++] Strong Upward Revisions',
        'positive': '[+] Positive Revisions',
        'stable': '[=] Stable Estimates',
        'negative': '[-] Negative Revisions',
        'strong_negative': '[--] Strong Downward Revisions'
    }
    
    print(f"\nMomentum: {momentum_indicators.get(momentum['momentum'], momentum['momentum'])}")
    print(f"Snapshots Analyzed: {momentum['snapshots_analyzed']}")
    
    if momentum.get('first_eps') and momentum.get('last_eps'):
        print(f"EPS Estimate Change: ${momentum['first_eps']:.2f} -> ${momentum['last_eps']:.2f}")
        print(f"Total Change: {'+' if momentum['change_pct'] > 0 else ''}{momentum['change_pct']:.1f}%")
    
    return 0


def cmd_compare(args):
    """Compare estimates across multiple tickers."""
    cache = load_cache()
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"Fetching estimates for {len(tickers)} tickers...")
    
    data = []
    for ticker in tickers:
        snapshot = get_earnings_estimates(ticker, cache)
        if snapshot:
            # Also get beat history
            history = calculate_beat_miss_history(ticker, cache)
            data.append({
                'ticker': ticker,
                'snapshot': snapshot,
                'history': history
            })
            print(f"  [OK] {ticker}")
        else:
            print(f"  [--] {ticker}")
    
    save_cache(cache)
    
    if not data:
        print("No data retrieved")
        return 1
    
    print(f"\n{'='*80}")
    print("ESTIMATE COMPARISON")
    print(f"{'='*80}")
    
    # Header
    print(f"\n{'Ticker':<8}{'Curr Q EPS':>12}{'Next Q EPS':>12}{'FY EPS':>12}{'Beat Rate':>12}{'Analysts':>10}")
    print("-" * 80)
    
    for item in data:
        s = item['snapshot']
        h = item['history']
        
        curr_q = s.current_quarter.get('eps_estimate')
        next_q = s.next_quarter.get('eps_estimate')
        fy = s.current_year.get('eps_estimate')
        beat_rate = h.get('beat_rate', 0)
        analysts = s.num_analysts
        
        print(f"{s.ticker:<8}"
              f"{f'${curr_q:.2f}' if curr_q else 'N/A':>12}"
              f"{f'${next_q:.2f}' if next_q else 'N/A':>12}"
              f"{f'${fy:.2f}' if fy else 'N/A':>12}"
              f"{f'{beat_rate:.0f}%' if beat_rate else 'N/A':>12}"
              f"{analysts:>10}")
    
    # Price targets
    print(f"\n{'Ticker':<8}{'Target':>12}{'Low':>12}{'High':>12}{'Rec':>15}")
    print("-" * 60)
    
    for item in data:
        s = item['snapshot']
        print(f"{s.ticker:<8}"
              f"{f'${s.target_price:.2f}' if s.target_price else 'N/A':>12}"
              f"{f'${s.target_low:.2f}' if s.target_low else 'N/A':>12}"
              f"{f'${s.target_high:.2f}' if s.target_high else 'N/A':>12}"
              f"{s.recommendation.upper():>15}")
    
    return 0


def cmd_upcoming(args):
    """Show upcoming earnings dates (if available)."""
    cache = load_cache()
    tickers = load_watchlist() if not args.tickers else [t.strip().upper() for t in args.tickers.split(",")]
    
    if not tickers:
        print("No tickers specified. Use watchlist or provide tickers.")
        return 1
    
    print(f"Checking earnings dates for {len(tickers)} tickers...")
    
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance required")
        return 1
    
    results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar
            if calendar is not None and not calendar.empty:
                earnings_date = calendar.get('Earnings Date')
                if earnings_date is not None:
                    if isinstance(earnings_date, list) and len(earnings_date) > 0:
                        results.append({'ticker': ticker, 'date': str(earnings_date[0])})
                    else:
                        results.append({'ticker': ticker, 'date': str(earnings_date)})
        except:
            pass
    
    if not results:
        print("\nNo upcoming earnings dates found.")
        return 0
    
    # Sort by date
    results.sort(key=lambda x: x['date'])
    
    print(f"\n{'='*40}")
    print("UPCOMING EARNINGS")
    print(f"{'='*40}")
    print(f"\n{'Ticker':<10}{'Earnings Date':<20}")
    print("-" * 30)
    
    for r in results:
        print(f"{r['ticker']:<10}{r['date']:<20}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Earnings Estimate Revision Tracker"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Estimates command
    est_parser = subparsers.add_parser("estimates", help="Get earnings estimates")
    est_parser.add_argument("ticker", help="Stock ticker")
    est_parser.add_argument("--full", "-f", action="store_true", help="Include beat/miss history")
    
    # History command
    hist_parser = subparsers.add_parser("history", help="Get beat/miss history")
    hist_parser.add_argument("ticker", help="Stock ticker")
    
    # Revisions command
    rev_parser = subparsers.add_parser("revisions", help="Show revision alerts")
    rev_parser.add_argument("--severity", "-s", choices=["high", "medium", "low"])
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan watchlist")
    scan_parser.add_argument("--alert", "-a", action="store_true", help="Send alerts")
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Manage watchlist")
    watch_parser.add_argument("watch_action", choices=["add", "remove", "list", "clear"])
    watch_parser.add_argument("ticker", nargs="?", help="Ticker to add/remove")
    
    # Momentum command
    mom_parser = subparsers.add_parser("momentum", help="Show revision momentum")
    mom_parser.add_argument("ticker", help="Stock ticker")
    
    # Compare command
    cmp_parser = subparsers.add_parser("compare", help="Compare multiple tickers")
    cmp_parser.add_argument("tickers", help="Comma-separated tickers")
    
    # Upcoming command
    up_parser = subparsers.add_parser("upcoming", help="Show upcoming earnings dates")
    up_parser.add_argument("--tickers", "-t", help="Comma-separated tickers (default: watchlist)")
    
    args = parser.parse_args()
    
    if args.command == "estimates":
        return cmd_estimates(args)
    elif args.command == "history":
        return cmd_history(args)
    elif args.command == "revisions":
        return cmd_revisions(args)
    elif args.command == "scan":
        return cmd_scan(args)
    elif args.command == "watch":
        return cmd_watch(args)
    elif args.command == "momentum":
        return cmd_momentum(args)
    elif args.command == "compare":
        return cmd_compare(args)
    elif args.command == "upcoming":
        return cmd_upcoming(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
