#!/usr/bin/env python3
"""
Peer Comparison CLI
Command-line interface for peer comparison generator.

Usage:
    python cli.py compare TICKER [--peers PEER1,PEER2,...] [--metrics all|valuation|growth|margins]
    python cli.py peers TICKER [--max 10]
    python cli.py group create GROUP_NAME TICKER1,TICKER2,...
    python cli.py group list
    python cli.py group show GROUP_NAME
    python cli.py scan TICKER1,TICKER2,... [--find-cheapest]
    python cli.py export TICKER [--format json|csv]
"""

import argparse
import json
import sys
from pathlib import Path

from peer_comparison import (
    load_cache, save_cache, get_stock_info, get_peer_group,
    find_peers_by_industry, build_comparison_table, print_comparison_table,
    create_custom_peer_group, list_peer_groups, load_peer_groups,
    export_comparison, METRICS, format_value, format_market_cap
)

SCRIPT_DIR = Path(__file__).parent


def cmd_compare(args):
    """Compare a ticker to its peers."""
    cache = load_cache()
    
    # Get peers
    if args.peers:
        peers = [p.strip() for p in args.peers.split(",")]
    elif args.group:
        groups = load_peer_groups()
        if args.group.upper() not in groups:
            print(f"Error: Peer group '{args.group}' not found")
            return 1
        peers = groups[args.group.upper()]
    else:
        peers = find_peers_by_industry(args.ticker, cache, max_peers=args.max_peers or 8)
        if not peers:
            print(f"No peers found for {args.ticker}. Use --peers to specify manually.")
            return 1
        print(f"Auto-detected peers: {', '.join(peers)}")
    
    # Select metrics
    if args.metrics == "all":
        metrics = list(METRICS.keys())
    elif args.metrics == "valuation":
        metrics = ["pe_ratio", "forward_pe", "peg_ratio", "ps_ratio", "pb_ratio", "ev_ebitda", "ev_revenue"]
    elif args.metrics == "growth":
        metrics = ["revenue_growth", "earnings_growth", "peg_ratio"]
    elif args.metrics == "margins":
        metrics = ["profit_margin", "operating_margin", "gross_margin", "roe", "roa"]
    elif args.metrics == "financial":
        metrics = ["debt_equity", "current_ratio", "roe", "roa"]
    else:
        # Default balanced view
        metrics = ["pe_ratio", "forward_pe", "ps_ratio", "ev_ebitda", "profit_margin", "roe", "revenue_growth"]
    
    # Build and display comparison
    comparison = build_comparison_table(args.ticker, peers, cache, metrics)
    print_comparison_table(comparison)
    
    # Export if requested
    if args.export:
        export_comparison(comparison)
    
    return 0


def cmd_peers(args):
    """Find peers for a ticker."""
    cache = load_cache()
    
    info = get_stock_info(args.ticker, cache)
    if not info:
        print(f"Could not fetch info for {args.ticker}")
        return 1
    
    save_cache(cache)
    
    print(f"\n{args.ticker.upper()} - {info.get('name', args.ticker)}")
    print(f"Sector: {info.get('sector', 'N/A')}")
    print(f"Industry: {info.get('industry', 'N/A')}")
    print()
    
    peers = find_peers_by_industry(args.ticker, cache, max_peers=args.max or 10)
    
    if peers:
        print(f"Suggested Peers ({len(peers)}):")
        for p in peers:
            peer_info = get_stock_info(p, cache)
            if peer_info:
                mcap = format_market_cap(peer_info.get("marketCap"))
                print(f"  {p:<6} {peer_info.get('name', '')[:30]:<32} {mcap}")
        save_cache(cache)
    else:
        print("No industry peers found in database.")
        print("Use 'python cli.py group create' to define custom peer groups.")
    
    return 0


def cmd_group(args):
    """Manage peer groups."""
    if args.group_action == "create":
        if not args.name or not args.tickers:
            print("Usage: python cli.py group create GROUP_NAME TICKER1,TICKER2,...")
            return 1
        tickers = [t.strip() for t in args.tickers.split(",")]
        create_custom_peer_group(args.name, tickers)
        return 0
    
    elif args.group_action == "list":
        list_peer_groups()
        return 0
    
    elif args.group_action == "show":
        if not args.name:
            print("Usage: python cli.py group show GROUP_NAME")
            return 1
        groups = load_peer_groups()
        name = args.name.upper()
        if name not in groups:
            print(f"Group '{args.name}' not found")
            return 1
        
        cache = load_cache()
        print(f"\nPeer Group: {name}")
        print("-" * 50)
        for ticker in groups[name]:
            info = get_stock_info(ticker, cache)
            if info:
                mcap = format_market_cap(info.get("marketCap"))
                print(f"  {ticker:<6} {info.get('name', '')[:35]:<37} {mcap}")
        save_cache(cache)
        return 0
    
    elif args.group_action == "delete":
        if not args.name:
            print("Usage: python cli.py group delete GROUP_NAME")
            return 1
        groups = load_peer_groups()
        name = args.name.upper()
        if name in groups:
            del groups[name]
            from peer_comparison import save_peer_groups
            save_peer_groups(groups)
            print(f"Deleted group '{name}'")
        else:
            print(f"Group '{args.name}' not found")
        return 0
    
    return 1


def cmd_scan(args):
    """Scan multiple tickers and rank by valuation."""
    cache = load_cache()
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    print(f"Scanning {len(tickers)} stocks...")
    print()
    
    data = []
    for ticker in tickers:
        info = get_stock_info(ticker, cache)
        if info:
            data.append(info)
            print(f"  [OK] {ticker}")
        else:
            print(f"  [--] {ticker}")
    
    save_cache(cache)
    
    if not data:
        print("No data retrieved")
        return 1
    
    # Sort by forward P/E (or trailing P/E if not available)
    def sort_key(x):
        return x.get("forward_pe") or x.get("pe_ratio") or 999
    
    if args.find_cheapest:
        data.sort(key=sort_key)
        print(f"\n{'='*70}")
        print("RANKED BY VALUATION (Forward P/E)")
        print(f"{'='*70}")
        print(f"{'Rank':<5}{'Ticker':<8}{'Name':<25}{'Fwd P/E':>10}{'P/S':>8}{'Margin':>10}")
        print("-" * 70)
        
        for i, stock in enumerate(data, 1):
            fpe = stock.get("forward_pe")
            ps = stock.get("ps_ratio")
            margin = stock.get("profit_margin")
            
            print(f"{i:<5}{stock['ticker']:<8}{stock.get('name', '')[:24]:<25}"
                  f"{format_value(fpe):>10}{format_value(ps):>8}"
                  f"{format_value(margin, True):>10}")
    else:
        # Just list all metrics
        print(f"\n{'='*90}")
        print("SCAN RESULTS")
        print(f"{'='*90}")
        print(f"{'Ticker':<8}{'P/E':>8}{'Fwd PE':>8}{'P/S':>8}{'EV/EB':>8}{'Margin':>10}{'ROE':>10}{'Growth':>10}")
        print("-" * 90)
        
        for stock in data:
            print(f"{stock['ticker']:<8}"
                  f"{format_value(stock.get('pe_ratio')):>8}"
                  f"{format_value(stock.get('forward_pe')):>8}"
                  f"{format_value(stock.get('ps_ratio')):>8}"
                  f"{format_value(stock.get('ev_ebitda')):>8}"
                  f"{format_value(stock.get('profit_margin'), True):>10}"
                  f"{format_value(stock.get('roe'), True):>10}"
                  f"{format_value(stock.get('revenue_growth'), True):>10}")
    
    return 0


def cmd_export(args):
    """Export comparison data."""
    cache = load_cache()
    
    # Get peers
    if args.peers:
        peers = [p.strip() for p in args.peers.split(",")]
    else:
        peers = find_peers_by_industry(args.ticker, cache, max_peers=8)
    
    comparison = build_comparison_table(args.ticker, peers, cache)
    
    if args.format == "csv":
        output_path = SCRIPT_DIR / f"comparison_{args.ticker}_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.csv"
        
        import csv
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            
            # Header
            stocks = list(comparison.get("stocks", {}).keys())
            writer.writerow(["Metric"] + stocks + ["Peer Avg"])
            
            # Metrics
            for metric_id, metric_data in comparison.get("metrics", {}).items():
                row = [metric_data["name"]]
                for stock in stocks:
                    if stock in metric_data.get("values", {}):
                        row.append(metric_data["values"][stock].get("value", ""))
                    else:
                        row.append("")
                row.append(metric_data.get("peerAverage", ""))
                writer.writerow(row)
        
        print(f"[OK] Exported to {output_path}")
    else:
        export_comparison(comparison)
    
    return 0


def cmd_quick(args):
    """Quick valuation check for a single stock."""
    cache = load_cache()
    ticker = args.ticker.upper()
    
    info = get_stock_info(ticker, cache)
    if not info:
        print(f"Could not fetch data for {ticker}")
        return 1
    
    save_cache(cache)
    
    print(f"\n{'='*50}")
    print(f"{ticker} - {info.get('name', ticker)}")
    print(f"{'='*50}")
    print(f"Sector: {info.get('sector', 'N/A')}")
    print(f"Industry: {info.get('industry', 'N/A')}")
    print(f"Market Cap: {format_market_cap(info.get('marketCap'))}")
    print(f"Price: ${info.get('price', 0):.2f}")
    print()
    
    print("VALUATION METRICS:")
    print("-" * 30)
    metrics_to_show = ["pe_ratio", "forward_pe", "peg_ratio", "ps_ratio", "pb_ratio", "ev_ebitda"]
    for m in metrics_to_show:
        if m in METRICS:
            value = info.get(m)
            print(f"  {METRICS[m]['name']:<18}: {format_value(value)}")
    
    print("\nPROFITABILITY:")
    print("-" * 30)
    metrics_to_show = ["profit_margin", "operating_margin", "gross_margin", "roe", "roa"]
    for m in metrics_to_show:
        if m in METRICS:
            value = info.get(m)
            print(f"  {METRICS[m]['name']:<18}: {format_value(value, METRICS[m].get('pct', False))}")
    
    print("\nGROWTH:")
    print("-" * 30)
    metrics_to_show = ["revenue_growth", "earnings_growth"]
    for m in metrics_to_show:
        if m in METRICS:
            value = info.get(m)
            print(f"  {METRICS[m]['name']:<18}: {format_value(value, True)}")
    
    print("\nFINANCIAL HEALTH:")
    print("-" * 30)
    metrics_to_show = ["debt_equity", "current_ratio"]
    for m in metrics_to_show:
        if m in METRICS:
            value = info.get(m)
            print(f"  {METRICS[m]['name']:<18}: {format_value(value)}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Peer Comparison Generator - Relative valuation analysis tool"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare ticker to peers")
    compare_parser.add_argument("ticker", help="Stock ticker to analyze")
    compare_parser.add_argument("--peers", "-p", help="Comma-separated list of peer tickers")
    compare_parser.add_argument("--group", "-g", help="Use a saved peer group")
    compare_parser.add_argument("--metrics", "-m", 
                               choices=["all", "valuation", "growth", "margins", "financial"],
                               default="valuation", help="Metric set to compare")
    compare_parser.add_argument("--max-peers", type=int, default=8, help="Max peers for auto-detection")
    compare_parser.add_argument("--export", "-e", action="store_true", help="Export to JSON")
    
    # Peers command
    peers_parser = subparsers.add_parser("peers", help="Find peers for a ticker")
    peers_parser.add_argument("ticker", help="Stock ticker")
    peers_parser.add_argument("--max", type=int, default=10, help="Max peers to show")
    
    # Group command
    group_parser = subparsers.add_parser("group", help="Manage peer groups")
    group_parser.add_argument("group_action", choices=["create", "list", "show", "delete"])
    group_parser.add_argument("name", nargs="?", help="Group name")
    group_parser.add_argument("tickers", nargs="?", help="Comma-separated tickers (for create)")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan multiple tickers")
    scan_parser.add_argument("tickers", help="Comma-separated list of tickers")
    scan_parser.add_argument("--find-cheapest", "-c", action="store_true", help="Rank by valuation")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export comparison data")
    export_parser.add_argument("ticker", help="Stock ticker")
    export_parser.add_argument("--peers", "-p", help="Comma-separated peer tickers")
    export_parser.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    
    # Quick command
    quick_parser = subparsers.add_parser("quick", help="Quick valuation check")
    quick_parser.add_argument("ticker", help="Stock ticker")
    
    args = parser.parse_args()
    
    if args.command == "compare":
        return cmd_compare(args)
    elif args.command == "peers":
        return cmd_peers(args)
    elif args.command == "group":
        return cmd_group(args)
    elif args.command == "scan":
        return cmd_scan(args)
    elif args.command == "export":
        return cmd_export(args)
    elif args.command == "quick":
        return cmd_quick(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
