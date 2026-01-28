#!/usr/bin/env python3
"""
Macro Economic Calendar - CLI Interface
Track upcoming economic events and their market impact.

Author: PM3

Commands:
    today       - Show today's events
    week        - Show this week's events  
    upcoming    - Show all upcoming events (default)
    event TYPE  - Details on specific event type
    history TYPE - Historical market reactions
    risk        - Event risk assessment
    export      - Export to JSON
"""

import argparse
from datetime import datetime, timedelta

from macro_calendar import (
    analyze_calendar,
    get_historical_reactions,
    generate_event_report,
    export_to_json,
    ECONOMIC_EVENTS
)


def cmd_today(args):
    """Show today's economic events."""
    today = datetime.now().strftime("%Y-%m-%d")
    calendar = analyze_calendar()
    
    today_events = [e for e in calendar["events"] if e["date"] == today]
    
    print(f"\n=== TODAY'S ECONOMIC EVENTS ({today}) ===\n")
    
    if not today_events:
        print("No major economic events scheduled for today.")
        print("\nNext event:")
        if calendar["events"]:
            next_ev = calendar["events"][0]
            print(f"  {next_ev['name']} - {next_ev['date']} ({next_ev['countdown']['countdown_str']})")
        return
    
    for event in today_events:
        impact = {"HIGH": "[HIGH IMPACT]", "MEDIUM": "[MEDIUM]", "LOW": "[LOW]"}.get(event["impact"], "")
        print(f"{impact} {event['name']}")
        print(f"   Time: {event['time']}")
        print(f"   Estimate: {event['estimate']} | Prior: {event['prior']}")
        print(f"   Countdown: {event['countdown']['countdown_str']}")
        if event.get("notes"):
            print(f"   Notes: {event['notes']}")
        print()


def cmd_week(args):
    """Show this week's economic events."""
    calendar = analyze_calendar()
    
    today = datetime.now()
    week_end = today + timedelta(days=7)
    
    week_events = [
        e for e in calendar["events"] 
        if datetime.strptime(e["date"], "%Y-%m-%d") <= week_end
    ]
    
    print(f"\n=== THIS WEEK'S ECONOMIC EVENTS ===\n")
    print(f"Period: {today.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
    print()
    
    if not week_events:
        print("No major economic events this week.")
        return
    
    # Group by day
    by_day = {}
    for event in week_events:
        day = event["date"]
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(event)
    
    for day in sorted(by_day.keys()):
        day_dt = datetime.strptime(day, "%Y-%m-%d")
        day_name = day_dt.strftime("%A, %b %d")
        
        if day == today.strftime("%Y-%m-%d"):
            day_name += " (TODAY)"
        
        print(f"--- {day_name} ---")
        
        for event in by_day[day]:
            impact = {"HIGH": "!!!", "MEDIUM": "!!", "LOW": "!"}.get(event["impact"], "")
            print(f"  [{impact}] {event['time']} - {event['name']}")
            print(f"       Est: {event['estimate']} | Prior: {event['prior']}")
        print()


def cmd_upcoming(args):
    """Show all upcoming events."""
    print(generate_event_report())


def cmd_event(args):
    """Show details for a specific event type."""
    event_type = args.type.lower().replace("-", "_").replace(" ", "_")
    
    # Find matching event type
    matched = None
    for key, info in ECONOMIC_EVENTS.items():
        if event_type in key or event_type in info["name"].lower():
            matched = key
            break
    
    if not matched:
        print(f"\nUnknown event type: {args.type}")
        print("\nAvailable event types:")
        for key, info in ECONOMIC_EVENTS.items():
            print(f"  - {key}: {info['name']}")
        return
    
    info = ECONOMIC_EVENTS[matched]
    
    print(f"\n=== {info['name'].upper()} ===\n")
    print(f"Impact Level: {info['impact']}")
    print(f"Frequency: {info['frequency']}")
    print(f"Typical Reaction: {info['typical_reaction']}")
    
    # Get historical reactions
    hist = get_historical_reactions(matched, 5)
    
    if hist.get("reactions"):
        print(f"\nHistorical Market Reactions (SPY):")
        print(f"  Avg Absolute Move: {hist['stats']['avg_absolute_move']}%")
        print(f"  Direction Bias: {hist['stats']['avg_direction']:+.2f}%")
        
        if hist['stats'].get('high_volatility'):
            print("  >>> HIGH VOLATILITY EVENT")
        
        print(f"\nRecent History:")
        for r in hist["reactions"]:
            direction = "+" if not r['spy_change'].startswith('-') else ""
            print(f"  {r['date']}: {r['actual']} vs {r['estimate']} -> SPY {r['spy_change']} ({r['beat']})")
    
    # Check if upcoming
    calendar = analyze_calendar()
    upcoming = [e for e in calendar["events"] if e["type"] == matched]
    
    if upcoming:
        print(f"\nNext {info['name']}:")
        next_ev = upcoming[0]
        print(f"  Date: {next_ev['date']} at {next_ev['time']}")
        print(f"  Estimate: {next_ev['estimate']} | Prior: {next_ev['prior']}")
        print(f"  Countdown: {next_ev['countdown']['countdown_str']}")
    
    print()


def cmd_history(args):
    """Show historical market reactions for an event type."""
    event_type = args.type.lower().replace("-", "_").replace(" ", "_")
    
    # Find matching event type
    matched = None
    for key in ECONOMIC_EVENTS.keys():
        if event_type in key:
            matched = key
            break
    
    if not matched:
        print(f"\nUnknown event type: {args.type}")
        print("Use: cpi, nfp, fed_meeting, ppi, gdp, retail_sales, pmi_manufacturing")
        return
    
    hist = get_historical_reactions(matched, 10)
    info = ECONOMIC_EVENTS[matched]
    
    print(f"\n=== HISTORICAL REACTIONS: {info['name'].upper()} ===\n")
    
    if not hist.get("reactions"):
        print("No historical data available for this event type.")
        return
    
    print(f"Statistics:")
    print(f"  Average Absolute Move: {hist['stats']['avg_absolute_move']}%")
    print(f"  Average Direction: {hist['stats']['avg_direction']:+.2f}%")
    
    if hist['stats'].get('tends_positive'):
        print("  Tendency: BULLISH (SPY tends to rise)")
    elif hist['stats'].get('tends_negative'):
        print("  Tendency: BEARISH (SPY tends to fall)")
    else:
        print("  Tendency: NEUTRAL (no consistent direction)")
    
    if hist['stats'].get('high_volatility'):
        print("  Volatility: HIGH (>1% average move)")
    
    print(f"\nRecent Events:")
    print(f"{'Date':<12} {'Actual':<15} {'Estimate':<15} {'SPY':<10} {'Result':<8}")
    print("-" * 60)
    
    for r in hist["reactions"]:
        print(f"{r['date']:<12} {r['actual']:<15} {r['estimate']:<15} {r['spy_change']:<10} {r['beat']:<8}")
    
    print()


def cmd_risk(args):
    """Show current event risk assessment."""
    calendar = analyze_calendar()
    
    print("\n=== EVENT RISK ASSESSMENT ===\n")
    
    risk_color = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}.get(calendar["risk_level"], "")
    
    print(f"Current Risk Level: {risk_color}")
    print(f"High-Impact Events Soon: {calendar['high_impact_soon']}")
    
    # Find imminent high-impact events
    imminent = [
        e for e in calendar["events"]
        if e["impact"] == "HIGH" and e["countdown"]["status"] in ["IMMINENT", "TODAY", "SOON"]
    ]
    
    if imminent:
        print("\n>>> IMMINENT HIGH-IMPACT EVENTS:")
        for e in imminent:
            print(f"    - {e['name']} in {e['countdown']['countdown_str']}")
            print(f"      Est: {e['estimate']} | Prior: {e['prior']}")
    else:
        print("\nNo imminent high-impact events.")
    
    # Trading recommendations
    print("\nTrading Considerations:")
    if calendar["risk_level"] == "HIGH":
        print("  - Consider reducing position sizes")
        print("  - Avoid initiating new positions before events")
        print("  - Review stop-loss levels")
        print("  - Be prepared for volatility")
    elif calendar["risk_level"] == "MEDIUM":
        print("  - Monitor positions closely")
        print("  - Have exit strategies ready")
    else:
        print("  - Normal trading conditions")
        print("  - Standard risk management applies")
    
    print()


def cmd_export(args):
    """Export calendar to JSON."""
    output = args.output if args.output else None
    
    file_path = export_to_json(output)
    print(f"\nExported to: {file_path}")


def cmd_list_types(args):
    """List all economic event types."""
    print("\n=== ECONOMIC EVENT TYPES ===\n")
    
    for key, info in ECONOMIC_EVENTS.items():
        print(f"{key}")
        print(f"  Name: {info['name']}")
        print(f"  Impact: {info['impact']}")
        print(f"  Frequency: {info['frequency']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Macro Economic Calendar - Track economic events and market impact",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cli.py today              # Today's events
    python cli.py week               # This week's events
    python cli.py upcoming           # All upcoming events
    python cli.py event cpi          # Details on CPI
    python cli.py event fed          # Details on Fed meetings
    python cli.py history nfp        # Historical NFP reactions
    python cli.py risk               # Event risk assessment
    python cli.py types              # List all event types
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # today
    p_today = subparsers.add_parser("today", help="Show today's events")
    p_today.set_defaults(func=cmd_today)
    
    # week
    p_week = subparsers.add_parser("week", help="Show this week's events")
    p_week.set_defaults(func=cmd_week)
    
    # upcoming
    p_upcoming = subparsers.add_parser("upcoming", help="Show all upcoming events")
    p_upcoming.set_defaults(func=cmd_upcoming)
    
    # event
    p_event = subparsers.add_parser("event", help="Details on specific event type")
    p_event.add_argument("type", help="Event type (cpi, nfp, fed, gdp, ppi, etc.)")
    p_event.set_defaults(func=cmd_event)
    
    # history
    p_history = subparsers.add_parser("history", help="Historical market reactions")
    p_history.add_argument("type", help="Event type")
    p_history.set_defaults(func=cmd_history)
    
    # risk
    p_risk = subparsers.add_parser("risk", help="Event risk assessment")
    p_risk.set_defaults(func=cmd_risk)
    
    # export
    p_export = subparsers.add_parser("export", help="Export to JSON")
    p_export.add_argument("-o", "--output", help="Output file path")
    p_export.set_defaults(func=cmd_export)
    
    # types
    p_types = subparsers.add_parser("types", help="List all event types")
    p_types.set_defaults(func=cmd_list_types)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default to upcoming
        cmd_upcoming(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
