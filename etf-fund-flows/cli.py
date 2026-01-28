#!/usr/bin/env python3
"""
ETF Fund Flows Tracker CLI
Monitor ETF inflows/outflows for sector/thematic trends.
"""

import argparse
import json
import sys
from datetime import datetime

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from etf_flows import ETFFundFlowsTracker, generate_sample_data


def format_currency(value: float) -> str:
    """Format currency with B/M suffixes."""
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"${value/1_000_000:.0f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.0f}K"
    return f"${value:.0f}"


def cmd_inflows(args):
    """Show top ETF inflows."""
    tracker = generate_sample_data()
    inflows = tracker.get_top_inflows(days=args.days, limit=args.limit)
    
    if args.json:
        print(json.dumps(inflows, indent=2, default=str))
        return
    
    print(f"\n{'='*65}")
    print(f"  TOP ETF INFLOWS ({args.days} days)")
    print(f"{'='*65}\n")
    
    if not inflows:
        print("  No inflows found\n")
        return
    
    print(f"  {'Ticker':<8} {'Name':<35} {'Flow':>12} {'Category':>12}")
    print(f"  {'─'*61}")
    
    for etf in inflows:
        name = etf['etf_name'][:33] + ".." if len(etf['etf_name']) > 35 else etf['etf_name']
        flow_str = format_currency(etf['flow'])
        print(f"  🟢 {etf['ticker']:<6} {name:<35} {flow_str:>10} {etf['category']:>12}")
    
    print()


def cmd_outflows(args):
    """Show top ETF outflows."""
    tracker = generate_sample_data()
    outflows = tracker.get_top_outflows(days=args.days, limit=args.limit)
    
    if args.json:
        print(json.dumps(outflows, indent=2, default=str))
        return
    
    print(f"\n{'='*65}")
    print(f"  TOP ETF OUTFLOWS ({args.days} days)")
    print(f"{'='*65}\n")
    
    if not outflows:
        print("  No outflows found\n")
        return
    
    print(f"  {'Ticker':<8} {'Name':<35} {'Flow':>12} {'Category':>12}")
    print(f"  {'─'*61}")
    
    for etf in outflows:
        name = etf['etf_name'][:33] + ".." if len(etf['etf_name']) > 35 else etf['etf_name']
        flow_str = format_currency(etf['flow'])
        print(f"  🔴 {etf['ticker']:<6} {name:<35} {flow_str:>10} {etf['category']:>12}")
    
    print()


def cmd_sectors(args):
    """Show sector rotation analysis."""
    tracker = generate_sample_data()
    rotation = tracker.get_sector_rotation(days=args.days)
    
    if args.json:
        print(json.dumps(rotation, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  SECTOR ROTATION ({args.days} days)")
    print(f"{'='*60}\n")
    
    print(f"  📊 {rotation['rotation_analysis']}\n")
    
    print(f"  {'Sector':<25} {'Flow':>15} {'Direction':>12}")
    print(f"  {'─'*54}")
    
    for s in rotation['sector_flows']:
        flow_str = format_currency(s['flow'])
        if s['flow'] > 100_000_000:
            direction = "🟢 Inflow"
        elif s['flow'] < -100_000_000:
            direction = "🔴 Outflow"
        else:
            direction = "⚪ Neutral"
        print(f"  {s['sector']:<25} {flow_str:>15} {direction:>12}")
    
    print()


def cmd_themes(args):
    """Show thematic ETF trends."""
    tracker = generate_sample_data()
    themes = tracker.get_thematic_trends(days=args.days)
    
    if args.json:
        print(json.dumps(themes, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  THEMATIC ETF TRENDS ({args.days} days)")
    print(f"{'='*60}\n")
    
    if not themes['thematic_flows']:
        print("  No thematic data available\n")
        return
    
    print(f"  {'Theme':<25} {'Flow':>15} {'Status':>12}")
    print(f"  {'─'*54}")
    
    for t in themes['thematic_flows']:
        flow_str = format_currency(t['flow'])
        print(f"  {t['theme']:<25} {flow_str:>15} {t['trend']:>12}")
    
    print()


def cmd_analyze(args):
    """Analyze a specific ETF."""
    tracker = generate_sample_data()
    analysis = tracker.get_etf_analysis(args.ticker.upper(), days=args.days)
    
    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
        return
    
    if 'error' in analysis:
        print(f"\n  Error: {analysis['error']}\n")
        return
    
    print(f"\n{'='*60}")
    print(f"  ETF ANALYSIS: {analysis['ticker']}")
    print(f"{'='*60}\n")
    
    print(f"  📛 Name:           {analysis['name']}")
    print(f"  📂 Category:       {analysis['category']}")
    if analysis['sector']:
        print(f"  🏭 Sector:         {analysis['sector']}")
    if analysis['theme']:
        print(f"  🎯 Theme:          {analysis['theme']}")
    
    print(f"\n  {'─'*56}")
    print(f"  FLOW ANALYSIS ({analysis['period_days']} days)")
    print(f"  {'─'*56}")
    
    total_emoji = "🟢" if analysis['total_flow'] > 0 else "🔴"
    print(f"  {total_emoji} Total Flow:      {format_currency(analysis['total_flow'])}")
    print(f"  📊 Avg Daily Flow: {format_currency(analysis['avg_daily_flow'])}")
    print(f"  📈 AUM:            {format_currency(analysis['latest_aum'])}")
    print(f"  💱 NAV P/D:        {analysis['latest_nav_pd']:.2f}%")
    
    streak_emoji = "🟢" if analysis['streak_type'] == 'inflow' else "🔴"
    print(f"  🔥 Current Streak: {streak_emoji} {analysis['current_streak']} day {analysis['streak_type']}")
    
    if analysis['daily_flows']:
        print(f"\n  {'─'*56}")
        print(f"  RECENT DAILY FLOWS")
        print(f"  {'─'*56}")
        print(f"  {'Date':<12} {'Flow':>15} {'% AUM':>10} {'NAV P/D':>10}")
        print(f"  {'─'*50}")
        
        for d in analysis['daily_flows']:
            flow_emoji = "🟢" if d['flow'] > 0 else "🔴"
            print(f"  {d['date']:<12} {flow_emoji}{format_currency(d['flow']):>13} {d['flow_pct']:>9.2f}% {d['nav_pd']:>9.2f}%")
    
    print()


def cmd_smart_money(args):
    """Show smart money signals."""
    tracker = generate_sample_data()
    signals = tracker.get_smart_money_signals(days=args.days)
    
    if args.json:
        print(json.dumps(signals, indent=2, default=str))
        return
    
    print(f"\n{'='*65}")
    print(f"  SMART MONEY SIGNALS ({args.days} days)")
    print(f"{'='*65}\n")
    
    if not signals:
        print("  No signals detected\n")
        return
    
    signal_emoji = {
        "ACCUMULATION": "🟢",
        "DISTRIBUTION": "🔴",
        "CONTRARIAN_BUY": "🟡"
    }
    
    for signal in signals:
        emoji = signal_emoji.get(signal['signal'], '⚪')
        print(f"  {emoji} {signal['signal']}: {signal['ticker']} ({signal['name'][:30]})")
        print(f"     {signal['description']}")
        conf_bar = "█" * int(signal['confidence'] * 5) + "░" * (5 - int(signal['confidence'] * 5))
        print(f"     Confidence: [{conf_bar}] {signal['confidence']*100:.0f}%")
        print()


def cmd_alerts(args):
    """Show recent flow alerts."""
    tracker = generate_sample_data()
    alerts = tracker.get_recent_alerts(limit=args.limit)
    
    if args.json:
        print(json.dumps(alerts, indent=2, default=str))
        return
    
    print(f"\n{'='*60}")
    print(f"  RECENT FLOW ALERTS")
    print(f"{'='*60}\n")
    
    if not alerts:
        print("  No recent alerts\n")
        return
    
    alert_emoji = {
        "LARGE_FLOW": "💰",
        "MEGA_FLOW": "🐋",
        "HIGH_PCT_FLOW": "📊",
        "NAV_DEVIATION": "⚠️",
        "INFLOW_STREAK": "🟢",
        "OUTFLOW_STREAK": "🔴"
    }
    
    for alert in alerts:
        emoji = alert_emoji.get(alert['type'], '⚡')
        time_str = datetime.fromisoformat(alert['time']).strftime("%m/%d %H:%M")
        sig_bar = "█" * int(alert['significance'] * 5) + "░" * (5 - int(alert['significance'] * 5))
        
        print(f"  {emoji} [{alert['type']}] {alert['ticker']}")
        print(f"     {alert['description']}")
        print(f"     Flow: {format_currency(alert['flow'])} | Significance: [{sig_bar}] | {time_str}")
        print()


def cmd_export(args):
    """Export flow data to JSON."""
    tracker = generate_sample_data()
    
    data = {
        "exported_at": datetime.now().isoformat(),
        "top_inflows": tracker.get_top_inflows(days=7, limit=20),
        "top_outflows": tracker.get_top_outflows(days=7, limit=20),
        "sector_rotation": tracker.get_sector_rotation(days=30),
        "thematic_trends": tracker.get_thematic_trends(days=30),
        "smart_money_signals": tracker.get_smart_money_signals(days=7),
        "recent_alerts": tracker.get_recent_alerts(limit=50)
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Exported to {args.output}")
    else:
        print(json.dumps(data, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="ETF Fund Flows Tracker - Monitor ETF inflows/outflows"
    )
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Inflows command
    p_inflows = subparsers.add_parser('inflows', help='Show top ETF inflows')
    p_inflows.add_argument('--days', type=int, default=7, help='Lookback days (default: 7)')
    p_inflows.add_argument('--limit', type=int, default=15, help='Number of results (default: 15)')
    p_inflows.add_argument('--json', action='store_true', help='JSON output')
    p_inflows.set_defaults(func=cmd_inflows)
    
    # Outflows command
    p_outflows = subparsers.add_parser('outflows', help='Show top ETF outflows')
    p_outflows.add_argument('--days', type=int, default=7, help='Lookback days (default: 7)')
    p_outflows.add_argument('--limit', type=int, default=15, help='Number of results (default: 15)')
    p_outflows.add_argument('--json', action='store_true', help='JSON output')
    p_outflows.set_defaults(func=cmd_outflows)
    
    # Sectors command
    p_sectors = subparsers.add_parser('sectors', help='Show sector rotation analysis')
    p_sectors.add_argument('--days', type=int, default=30, help='Lookback days (default: 30)')
    p_sectors.add_argument('--json', action='store_true', help='JSON output')
    p_sectors.set_defaults(func=cmd_sectors)
    
    # Themes command
    p_themes = subparsers.add_parser('themes', help='Show thematic ETF trends')
    p_themes.add_argument('--days', type=int, default=30, help='Lookback days (default: 30)')
    p_themes.add_argument('--json', action='store_true', help='JSON output')
    p_themes.set_defaults(func=cmd_themes)
    
    # Analyze command
    p_analyze = subparsers.add_parser('analyze', help='Analyze specific ETF')
    p_analyze.add_argument('ticker', help='ETF ticker symbol')
    p_analyze.add_argument('--days', type=int, default=30, help='Lookback days (default: 30)')
    p_analyze.add_argument('--json', action='store_true', help='JSON output')
    p_analyze.set_defaults(func=cmd_analyze)
    
    # Smart money command
    p_smart = subparsers.add_parser('smart', help='Show smart money signals')
    p_smart.add_argument('--days', type=int, default=7, help='Lookback days (default: 7)')
    p_smart.add_argument('--json', action='store_true', help='JSON output')
    p_smart.set_defaults(func=cmd_smart_money)
    
    # Alerts command
    p_alerts = subparsers.add_parser('alerts', help='Show recent flow alerts')
    p_alerts.add_argument('--limit', type=int, default=20, help='Number of alerts (default: 20)')
    p_alerts.add_argument('--json', action='store_true', help='JSON output')
    p_alerts.set_defaults(func=cmd_alerts)
    
    # Export command
    p_export = subparsers.add_parser('export', help='Export flow data to JSON')
    p_export.add_argument('-o', '--output', help='Output file path')
    p_export.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default to inflows
        args.days = 7
        args.limit = 15
        args.json = False
        cmd_inflows(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
