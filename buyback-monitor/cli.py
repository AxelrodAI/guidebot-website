#!/usr/bin/env python3
"""
Buyback & Share Count Monitor CLI

Commands:
  analyze <ticker>    - Full buyback analysis
  program <ticker>    - Show active buyback programs
  shares <ticker>     - Share count trend analysis
  execution <ticker>  - Execution history and timing
  insiders <ticker>   - Insider activity during buybacks
  yields              - Compare buyback yields
  scan                - Scan for high-yield opportunities
  worst               - Find worst executors
  alerts [ticker]     - Show buyback alerts
  watchlist           - Manage watchlist
  test                - Run tests
"""

import sys
import json
import argparse
from datetime import datetime
from dataclasses import asdict

# Windows Unicode fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from buyback_tracker import get_monitor, CompanyBuybackProfile


def format_money(amount: float) -> str:
    """Format money amount"""
    if amount >= 1e12:
        return f"${amount/1e12:.1f}T"
    elif amount >= 1e9:
        return f"${amount/1e9:.1f}B"
    elif amount >= 1e6:
        return f"${amount/1e6:.1f}M"
    else:
        return f"${amount:,.0f}"


def format_shares(shares: int) -> str:
    """Format share count"""
    if shares >= 1e9:
        return f"{shares/1e9:.2f}B"
    elif shares >= 1e6:
        return f"{shares/1e6:.1f}M"
    else:
        return f"{shares:,}"


def score_bar(score: float, width: int = 10) -> str:
    """Create a visual score bar"""
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def cmd_analyze(args):
    """Full buyback analysis"""
    monitor = get_monitor()
    ticker = args.ticker.upper()
    
    profile = monitor.analyze(ticker)
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  BUYBACK ANALYSIS: {profile.ticker}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    # Overview
    print("📊 OVERVIEW")
    print(f"   Company:           {profile.company_name}")
    print(f"   Current Price:     ${profile.current_price:,.2f}")
    print(f"   Market Cap:        {format_money(profile.market_cap)}")
    print(f"   Shares Outstanding: {format_shares(profile.shares_outstanding)}")
    print()
    
    # Buyback Yield
    print("💰 YIELD METRICS")
    print(f"   Buyback Yield:     {profile.buyback_yield:.2f}%")
    print(f"   Total Yield:       {profile.total_yield:.2f}% (dividends + buybacks)")
    print()
    
    # Active Programs
    print("📋 ACTIVE BUYBACK PROGRAMS")
    if profile.active_programs:
        for prog in profile.active_programs:
            utilized = (prog.authorized_amount - prog.remaining_amount) / prog.authorized_amount * 100
            print(f"   Program: {prog.program_type}")
            print(f"      Announced:    {prog.announcement_date}")
            print(f"      Authorized:   {format_money(prog.authorized_amount)}")
            print(f"      Remaining:    {format_money(prog.remaining_amount)} ({100-utilized:.0f}% left)")
            print(f"      Expires:      {prog.expiration_date}")
    else:
        print("   No active buyback programs")
    print()
    
    # Share Count Trend
    print("📈 SHARE COUNT TREND (Last 4 Quarters)")
    print(f"   {'Quarter':<12} {'Shares':>15} {'Change':>12} {'Source':<12}")
    print("   " + "-" * 55)
    for change in profile.share_changes[:4]:
        direction = "🔻" if change.change_pct < 0 else "🔺" if change.change_pct > 0 else "➡️"
        print(f"   {change.quarter:<12} {format_shares(change.basic_shares):>15} "
              f"{direction} {change.change_pct:>+.2f}%    {change.source:<12}")
    print()
    print(f"   Net 1-Year Change: {profile.net_share_change_1y:+.2f}%")
    if profile.net_share_change_1y < -2:
        print("   ✓ Share count declining (buybacks > dilution)")
    elif profile.net_share_change_1y > 2:
        print("   ⚠️ Share count increasing despite buybacks (dilution > buybacks)")
    print()
    
    # Execution Scores
    print("📊 BUYBACK SCORECARD")
    print(f"   Execution Score:   {score_bar(profile.execution_score)} {profile.execution_score:.0f}/100")
    print(f"   Timing Score:      {score_bar(profile.timing_score)} {profile.timing_score:.0f}/100")
    print(f"   Credibility:       {score_bar(profile.credibility_score)} {profile.credibility_score:.0f}/100")
    print()
    print(f"   Execution Rate:    {profile.execution_rate:.0%} of authorized amount")
    print(f"   Avg Buy Price:     ${profile.avg_execution_price:,.2f}")
    print(f"   Current vs Avg:    {profile.current_price_vs_avg:+.1f}%")
    if profile.current_price_vs_avg > 10:
        print("   ⚠️ Stock up significantly since avg buyback price - good timing!")
    elif profile.current_price_vs_avg < -10:
        print("   ⚠️ Stock down since avg buyback price - poor timing")
    print()
    
    # Insider Activity Warning
    if profile.insider_selling_during_buyback:
        print("⚠️  INSIDER ACTIVITY WARNING")
        print("   Insiders selling while company buys back shares!")
        for insider in profile.insider_activity:
            if insider.during_buyback and insider.transaction_type == 'sell':
                print(f"   • {insider.insider_name} ({insider.insider_role}): "
                      f"Sold {insider.shares:,} shares @ ${insider.price:.2f}")
        print()
    
    # Alerts
    if profile.alerts:
        print("🔔 ALERTS")
        for alert in profile.alerts:
            icon = "🔴" if alert.severity == 'high' else "🟡" if alert.severity == 'medium' else "⚪"
            print(f"   {icon} [{alert.alert_type}] {alert.message}")
        print()
    
    if args.json:
        print("\n📄 JSON Output:")
        # Convert dataclasses to dicts
        output = asdict(profile)
        print(json.dumps(output, indent=2, default=str))


def cmd_program(args):
    """Show buyback programs"""
    monitor = get_monitor()
    ticker = args.ticker.upper()
    
    profile = monitor.analyze(ticker)
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  BUYBACK PROGRAMS: {ticker}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print("📋 ACTIVE PROGRAMS")
    if profile.active_programs:
        for i, prog in enumerate(profile.active_programs, 1):
            utilized = (prog.authorized_amount - prog.remaining_amount) / prog.authorized_amount * 100
            print(f"\n   Program #{i}: {prog.program_type}")
            print(f"   ┌─────────────────────────────────────────────")
            print(f"   │ Announced:     {prog.announcement_date}")
            print(f"   │ Authorized:    {format_money(prog.authorized_amount)}")
            print(f"   │ Executed:      {format_money(prog.authorized_amount - prog.remaining_amount)} ({utilized:.1f}%)")
            print(f"   │ Remaining:     {format_money(prog.remaining_amount)}")
            print(f"   │ Expires:       {prog.expiration_date}")
            print(f"   │ Shares Auth:   {format_shares(prog.shares_authorized or 0)}")
            print(f"   └─────────────────────────────────────────────")
    else:
        print("   No active buyback programs")
    
    print("\n📚 HISTORICAL PROGRAMS")
    if profile.historical_programs:
        for i, prog in enumerate(profile.historical_programs, 1):
            print(f"\n   Program #{i}: {prog.program_type} - {prog.status.upper()}")
            print(f"      Period:     {prog.announcement_date} to {prog.expiration_date}")
            print(f"      Authorized: {format_money(prog.authorized_amount)}")
    else:
        print("   No historical programs on record")
    
    print()
    print(f"📊 TOTALS")
    print(f"   Total Authorized:  {format_money(profile.total_authorized)}")
    print(f"   Total Executed:    {format_money(profile.total_executed)}")
    print(f"   Execution Rate:    {profile.execution_rate:.0%}")


def cmd_shares(args):
    """Share count analysis"""
    monitor = get_monitor()
    ticker = args.ticker.upper()
    
    profile = monitor.analyze(ticker)
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  SHARE COUNT ANALYSIS: {ticker}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print(f"Current Shares Outstanding: {format_shares(profile.shares_outstanding)}")
    print(f"Net 1-Year Change:          {profile.net_share_change_1y:+.2f}%")
    print()
    
    print("📈 QUARTERLY CHANGES")
    print()
    print(f"   {'Quarter':<12} {'Basic Shares':>18} {'Change':>15} {'%':>8} {'Type':<12}")
    print("   " + "-" * 70)
    
    for change in profile.share_changes:
        direction = "↓" if change.change_pct < 0 else "↑" if change.change_pct > 0 else "→"
        
        if change.change_pct < -1:
            indicator = "🟢"  # Good - shares decreasing
        elif change.change_pct > 1:
            indicator = "🔴"  # Bad - shares increasing
        else:
            indicator = "⚪"  # Neutral
        
        print(f"   {change.quarter:<12} {format_shares(change.basic_shares):>18} "
              f"{direction} {change.change_basic:>+12,} {change.change_pct:>+7.2f}% {indicator} {change.source:<12}")
    
    print()
    print("📊 DILUTION ANALYSIS")
    
    dilution_quarters = [c for c in profile.share_changes if c.change_pct > 0]
    buyback_quarters = [c for c in profile.share_changes if c.change_pct < 0]
    
    print(f"   Quarters with dilution:  {len(dilution_quarters)}")
    print(f"   Quarters with buybacks:  {len(buyback_quarters)}")
    
    if dilution_quarters:
        total_dilution = sum(c.change_basic for c in dilution_quarters)
        print(f"   Total shares added:      {total_dilution:+,}")
    
    if buyback_quarters:
        total_reduced = sum(c.change_basic for c in buyback_quarters)
        print(f"   Total shares reduced:    {total_reduced:,}")
    
    print()
    if profile.net_share_change_1y < -3:
        print("   ✓ Strong share count reduction - buybacks exceeding dilution")
    elif profile.net_share_change_1y > 3:
        print("   ⚠️ Net dilution - issuance/SBC exceeding buybacks")
    else:
        print("   → Share count relatively stable")


def cmd_execution(args):
    """Execution history"""
    monitor = get_monitor()
    ticker = args.ticker.upper()
    
    profile = monitor.analyze(ticker)
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  BUYBACK EXECUTION: {ticker}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print("📊 EXECUTION METRICS")
    print(f"   Execution Rate:     {profile.execution_rate:.0%}")
    print(f"   Execution Score:    {profile.execution_score:.0f}/100 {score_bar(profile.execution_score)}")
    print(f"   Timing Score:       {profile.timing_score:.0f}/100 {score_bar(profile.timing_score)}")
    print()
    
    print("💵 PRICE ANALYSIS")
    print(f"   Avg Purchase Price: ${profile.avg_execution_price:,.2f}")
    print(f"   Current Price:      ${profile.current_price:,.2f}")
    print(f"   Difference:         {profile.current_price_vs_avg:+.1f}%")
    
    if profile.current_price_vs_avg > 15:
        print("   📈 Excellent timing! Stock up significantly since buybacks")
    elif profile.current_price_vs_avg > 0:
        print("   📈 Good timing - stock up since average purchase")
    elif profile.current_price_vs_avg > -10:
        print("   → Neutral timing - stock near average purchase price")
    else:
        print("   📉 Poor timing - stock down significantly since buybacks")
    print()
    
    print("📋 EXECUTION HISTORY")
    print(f"   {'Period':<12} {'Shares':>15} {'Amount':>12} {'Avg Price':>12}")
    print("   " + "-" * 55)
    
    for exec in profile.executions:
        print(f"   {exec.period:<12} {format_shares(exec.shares_repurchased):>15} "
              f"{format_money(exec.amount_spent):>12} ${exec.avg_price:>10,.2f}")
    
    total_shares = sum(e.shares_repurchased for e in profile.executions)
    total_amount = sum(e.amount_spent for e in profile.executions)
    print("   " + "-" * 55)
    print(f"   {'TOTAL':<12} {format_shares(total_shares):>15} {format_money(total_amount):>12}")


def cmd_insiders(args):
    """Insider activity"""
    monitor = get_monitor()
    ticker = args.ticker.upper()
    
    profile = monitor.analyze(ticker)
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  INSIDER ACTIVITY: {ticker}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    if profile.insider_selling_during_buyback:
        print("⚠️  WARNING: INSIDER SELLING DURING BUYBACK PERIOD")
        print("   This is a potential red flag - management may not believe")
        print("   in the value they're creating for shareholders.")
        print()
    
    if not profile.insider_activity:
        print("   No recent insider activity on record")
        return
    
    print("📋 RECENT INSIDER TRANSACTIONS")
    print()
    
    for activity in profile.insider_activity:
        icon = "🔴 SELL" if activity.transaction_type == 'sell' else "🟢 BUY"
        warning = " ⚠️ DURING BUYBACK" if activity.during_buyback and activity.transaction_type == 'sell' else ""
        
        print(f"   {activity.transaction_date}")
        print(f"      {activity.insider_name} ({activity.insider_role})")
        print(f"      {icon}: {activity.shares:,} shares @ ${activity.price:.2f}{warning}")
        print()


def cmd_yields(args):
    """Compare yields"""
    monitor = get_monitor()
    
    # Scan some tickers first
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'JPM', 'BAC', 'XOM', 'CVX', 'WMT']
    for t in tickers:
        if t not in monitor.profiles:
            monitor.analyze(t)
    
    yields = monitor.compare_yields()
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  BUYBACK YIELD COMPARISON")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print(f"   {'Ticker':<8} {'Buyback Yield':>14} {'Total Yield':>12} {'Execution':>10} {'Mkt Cap':>10}")
    print("   " + "-" * 60)
    
    for y in yields:
        exec_bar = "●" * int(y['execution_score'] / 20)
        print(f"   {y['ticker']:<8} {y['buyback_yield']:>13.2f}% {y['total_yield']:>11.2f}% "
              f"{exec_bar:<10} {y['market_cap_b']:>9.1f}B")
    
    print()
    print("Legend: Execution score (● = 20 points)")


def cmd_scan(args):
    """Scan for opportunities"""
    monitor = get_monitor()
    
    min_yield = args.min_yield or 3.0
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  HIGH BUYBACK YIELD SCAN (Min: {min_yield}%)")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    opportunities = monitor.scan_for_opportunities(min_yield)
    
    if not opportunities:
        print("   No opportunities found matching criteria")
        return
    
    print(f"   {'Ticker':<8} {'BB Yield':>10} {'Total':>8} {'Exec Score':>12} {'Share Δ':>10} {'Active':>8}")
    print("   " + "-" * 62)
    
    for opp in opportunities:
        active = "✓" if opp['active_program'] else ""
        change_icon = "🟢" if opp['net_share_change'] < 0 else "🔴" if opp['net_share_change'] > 2 else ""
        
        print(f"   {opp['ticker']:<8} {opp['buyback_yield']:>9.2f}% {opp['total_yield']:>7.2f}% "
              f"{opp['execution_score']:>11.0f} {opp['net_share_change']:>+9.1f}% {change_icon} {active:>6}")
    
    print()
    print(f"   Found {len(opportunities)} stocks with buyback yield ≥ {min_yield}%")


def cmd_worst(args):
    """Find worst executors"""
    monitor = get_monitor()
    
    # Analyze some tickers
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'JPM', 'BAC', 'XOM', 'CVX', 'WMT', 
               'HD', 'LOW', 'TGT', 'COST', 'DIS']
    for t in tickers:
        if t not in monitor.profiles:
            monitor.analyze(t)
    
    worst = monitor.get_worst_executors()
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  WORST BUYBACK EXECUTORS")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    if not worst:
        print("   No poor executors found")
        return
    
    print("   Companies with low execution rate or net dilution:")
    print()
    
    print(f"   {'Ticker':<8} {'Exec Rate':>12} {'Share Δ':>10} {'Credibility':>12} {'Insider Sell':>14}")
    print("   " + "-" * 60)
    
    for w in worst:
        insider = "⚠️ YES" if w['insider_selling'] else ""
        print(f"   {w['ticker']:<8} {w['execution_rate']:>11.0%} {w['net_share_change']:>+9.1f}% "
              f"{w['credibility_score']:>11.0f} {insider:>14}")
    
    print()
    print("   ⚠️ These companies announce buybacks but don't deliver")


def cmd_alerts(args):
    """Show alerts"""
    monitor = get_monitor()
    
    if args.ticker:
        ticker = args.ticker.upper()
        profile = monitor.analyze(ticker)
        alerts = profile.alerts
        print(f"═══════════════════════════════════════════════════════════════")
        print(f"  BUYBACK ALERTS: {ticker}")
        print(f"═══════════════════════════════════════════════════════════════")
    else:
        # Get all alerts from watchlist
        alerts = monitor.get_watchlist_alerts()
        print(f"═══════════════════════════════════════════════════════════════")
        print(f"  ALL BUYBACK ALERTS")
        print(f"═══════════════════════════════════════════════════════════════")
    
    print()
    
    if not alerts:
        print("   No active alerts")
        return
    
    for alert in alerts:
        icon = "🔴" if alert.severity == 'high' else "🟡" if alert.severity == 'medium' else "⚪"
        print(f"   {icon} {alert.ticker}: [{alert.alert_type}]")
        print(f"      {alert.message}")
        print(f"      {alert.timestamp}")
        print()
    
    print(f"   Total: {len(alerts)} alerts")


def cmd_watchlist(args):
    """Manage watchlist"""
    monitor = get_monitor()
    
    if args.add:
        monitor.add_to_watchlist(args.add)
        print(f"Added {args.add.upper()} to watchlist")
    elif args.remove:
        monitor.remove_from_watchlist(args.remove)
        print(f"Removed {args.remove.upper()} from watchlist")
    else:
        print(f"═══════════════════════════════════════════════════════════════")
        print(f"  BUYBACK WATCHLIST")
        print(f"═══════════════════════════════════════════════════════════════")
        print()
        
        if not monitor.watchlist:
            print("   Watchlist is empty")
            print("   Add tickers with: python cli.py watchlist --add TICKER")
            return
        
        print(f"   {'Ticker':<8} {'BB Yield':>10} {'Exec Score':>12} {'Alerts':>8}")
        print("   " + "-" * 42)
        
        for ticker in sorted(monitor.watchlist):
            if ticker in monitor.profiles:
                p = monitor.profiles[ticker]
                print(f"   {ticker:<8} {p.buyback_yield:>9.2f}% {p.execution_score:>11.0f} {len(p.alerts):>8}")


def cmd_test(args):
    """Run tests"""
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  BUYBACK MONITOR - TEST MODE")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    monitor = get_monitor()
    
    # Test 1: Analyze a ticker
    print("Test 1: Analyzing AAPL...")
    profile = monitor.analyze('AAPL')
    assert profile.ticker == 'AAPL', "Ticker mismatch"
    assert profile.market_cap > 0, "Invalid market cap"
    print(f"   ✓ Market cap: {format_money(profile.market_cap)}")
    print(f"   ✓ Buyback yield: {profile.buyback_yield:.2f}%")
    print(f"   ✓ Execution score: {profile.execution_score:.0f}")
    print()
    
    # Test 2: Share count tracking
    print("Test 2: Share count tracking...")
    assert len(profile.share_changes) > 0, "No share changes"
    print(f"   ✓ Tracked {len(profile.share_changes)} quarters")
    print(f"   ✓ Net change: {profile.net_share_change_1y:+.2f}%")
    print()
    
    # Test 3: Execution history
    print("Test 3: Execution history...")
    assert len(profile.executions) > 0, "No executions"
    print(f"   ✓ {len(profile.executions)} execution periods")
    print(f"   ✓ Avg price: ${profile.avg_execution_price:,.2f}")
    print()
    
    # Test 4: Scan for opportunities
    print("Test 4: Scanning for opportunities...")
    opps = monitor.scan_for_opportunities(2.0)
    print(f"   ✓ Found {len(opps)} high-yield opportunities")
    print()
    
    # Test 5: Yield comparison
    print("Test 5: Yield comparison...")
    yields = monitor.compare_yields()
    assert len(yields) > 0, "No yields"
    print(f"   ✓ Compared {len(yields)} tickers")
    print()
    
    # Test 6: Alert generation
    print("Test 6: Alert generation...")
    total_alerts = sum(len(p.alerts) for p in monitor.profiles.values())
    print(f"   ✓ Generated {total_alerts} alerts across {len(monitor.profiles)} tickers")
    print()
    
    print("═══════════════════════════════════════════════════════════════")
    print("  ALL TESTS PASSED ✓")
    print("═══════════════════════════════════════════════════════════════")


def main():
    parser = argparse.ArgumentParser(
        description="Buyback & Share Count Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py analyze AAPL           # Full buyback analysis
  python cli.py program MSFT           # Show buyback programs
  python cli.py shares GOOGL           # Share count trends
  python cli.py execution NVDA         # Execution history
  python cli.py insiders META          # Insider activity
  python cli.py yields                 # Compare yields
  python cli.py scan --min-yield 4     # Find high-yield stocks
  python cli.py worst                  # Find worst executors
  python cli.py test                   # Run tests
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # analyze
    p_analyze = subparsers.add_parser('analyze', help='Full buyback analysis')
    p_analyze.add_argument('ticker', help='Stock ticker')
    p_analyze.add_argument('--json', '-j', action='store_true', help='Output JSON')
    p_analyze.set_defaults(func=cmd_analyze)
    
    # program
    p_program = subparsers.add_parser('program', help='Show buyback programs')
    p_program.add_argument('ticker', help='Stock ticker')
    p_program.set_defaults(func=cmd_program)
    
    # shares
    p_shares = subparsers.add_parser('shares', help='Share count analysis')
    p_shares.add_argument('ticker', help='Stock ticker')
    p_shares.set_defaults(func=cmd_shares)
    
    # execution
    p_exec = subparsers.add_parser('execution', help='Execution history')
    p_exec.add_argument('ticker', help='Stock ticker')
    p_exec.set_defaults(func=cmd_execution)
    
    # insiders
    p_insider = subparsers.add_parser('insiders', help='Insider activity')
    p_insider.add_argument('ticker', help='Stock ticker')
    p_insider.set_defaults(func=cmd_insiders)
    
    # yields
    p_yields = subparsers.add_parser('yields', help='Compare yields')
    p_yields.set_defaults(func=cmd_yields)
    
    # scan
    p_scan = subparsers.add_parser('scan', help='Scan for opportunities')
    p_scan.add_argument('--min-yield', type=float, help='Minimum buyback yield (default: 3.0)')
    p_scan.set_defaults(func=cmd_scan)
    
    # worst
    p_worst = subparsers.add_parser('worst', help='Find worst executors')
    p_worst.set_defaults(func=cmd_worst)
    
    # alerts
    p_alerts = subparsers.add_parser('alerts', help='Show alerts')
    p_alerts.add_argument('ticker', nargs='?', help='Stock ticker (optional)')
    p_alerts.set_defaults(func=cmd_alerts)
    
    # watchlist
    p_watch = subparsers.add_parser('watchlist', help='Manage watchlist')
    p_watch.add_argument('--add', help='Add ticker to watchlist')
    p_watch.add_argument('--remove', help='Remove ticker from watchlist')
    p_watch.set_defaults(func=cmd_watchlist)
    
    # test
    p_test = subparsers.add_parser('test', help='Run tests')
    p_test.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == '__main__':
    main()
