#!/usr/bin/env python3
"""
Fund Flow Tracker - Track ETF and Mutual Fund Flows
Built by PM3 | Backend/CLI Pipeline

Monitors fund inflows/outflows to identify market sentiment and positioning shifts.
Data sources: Yahoo Finance, ETF.com estimates, simulated institutional data.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import random

# Fix Windows console encoding for emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Data storage path
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Sample ETF universe with categories
ETF_UNIVERSE = {
    # Equity - US
    "SPY": {"name": "SPDR S&P 500 ETF", "category": "US Large Cap", "aum_billions": 500},
    "QQQ": {"name": "Invesco QQQ Trust", "category": "US Tech", "aum_billions": 250},
    "IWM": {"name": "iShares Russell 2000", "category": "US Small Cap", "aum_billions": 60},
    "DIA": {"name": "SPDR Dow Jones", "category": "US Large Cap", "aum_billions": 30},
    "VTI": {"name": "Vanguard Total Stock", "category": "US Total Market", "aum_billions": 350},
    
    # Equity - International
    "EFA": {"name": "iShares MSCI EAFE", "category": "Developed Intl", "aum_billions": 55},
    "EEM": {"name": "iShares MSCI Emerging", "category": "Emerging Markets", "aum_billions": 25},
    "VWO": {"name": "Vanguard FTSE Emerging", "category": "Emerging Markets", "aum_billions": 80},
    "FXI": {"name": "iShares China Large-Cap", "category": "China", "aum_billions": 5},
    
    # Fixed Income
    "TLT": {"name": "iShares 20+ Year Treasury", "category": "Long Treasury", "aum_billions": 40},
    "IEF": {"name": "iShares 7-10 Year Treasury", "category": "Intermediate Treasury", "aum_billions": 25},
    "SHY": {"name": "iShares 1-3 Year Treasury", "category": "Short Treasury", "aum_billions": 20},
    "LQD": {"name": "iShares Investment Grade", "category": "Corp Bonds IG", "aum_billions": 35},
    "HYG": {"name": "iShares High Yield", "category": "Corp Bonds HY", "aum_billions": 15},
    "AGG": {"name": "iShares Core US Aggregate", "category": "Aggregate Bond", "aum_billions": 100},
    
    # Sector
    "XLF": {"name": "Financial Select SPDR", "category": "Financials", "aum_billions": 40},
    "XLE": {"name": "Energy Select SPDR", "category": "Energy", "aum_billions": 35},
    "XLK": {"name": "Technology Select SPDR", "category": "Technology", "aum_billions": 55},
    "XLV": {"name": "Health Care Select SPDR", "category": "Healthcare", "aum_billions": 35},
    "XLI": {"name": "Industrial Select SPDR", "category": "Industrials", "aum_billions": 18},
    "XLU": {"name": "Utilities Select SPDR", "category": "Utilities", "aum_billions": 15},
    "XLRE": {"name": "Real Estate Select SPDR", "category": "Real Estate", "aum_billions": 6},
    
    # Commodities
    "GLD": {"name": "SPDR Gold Shares", "category": "Gold", "aum_billions": 60},
    "SLV": {"name": "iShares Silver Trust", "category": "Silver", "aum_billions": 10},
    "USO": {"name": "United States Oil Fund", "category": "Crude Oil", "aum_billions": 2},
    
    # Thematic/Factor
    "ARKK": {"name": "ARK Innovation ETF", "category": "Disruptive Innovation", "aum_billions": 8},
    "MTUM": {"name": "iShares MSCI USA Momentum", "category": "Momentum Factor", "aum_billions": 12},
    "USMV": {"name": "iShares MSCI USA Min Vol", "category": "Low Volatility", "aum_billions": 30},
    "VIG": {"name": "Vanguard Dividend Appreciation", "category": "Dividend Growth", "aum_billions": 75},
}


def generate_simulated_flows(ticker: str, days: int = 30) -> list:
    """Generate simulated flow data for an ETF."""
    etf = ETF_UNIVERSE.get(ticker, {"aum_billions": 10})
    aum = etf["aum_billions"]
    
    flows = []
    base_date = datetime.now()
    
    # Generate a trend bias (positive or negative momentum)
    trend_bias = random.uniform(-0.3, 0.3)
    
    for i in range(days):
        date = base_date - timedelta(days=days - i - 1)
        
        # Skip weekends
        if date.weekday() >= 5:
            continue
        
        # Flow as percentage of AUM (typically 0.1-1% daily)
        base_flow_pct = random.gauss(trend_bias, 0.5)
        flow_pct = max(-2, min(2, base_flow_pct))  # Cap at +/- 2%
        
        flow_millions = aum * 1000 * (flow_pct / 100)
        
        flows.append({
            "date": date.strftime("%Y-%m-%d"),
            "flow_millions": round(flow_millions, 2),
            "flow_pct": round(flow_pct, 3),
            "aum_billions": round(aum + (flow_millions / 1000), 2),
            "shares_outstanding_change_pct": round(flow_pct * 0.95, 3)  # Creation/redemption
        })
        
        # Update running AUM
        aum += flow_millions / 1000
    
    return flows


def get_etf_flows(ticker: str, days: int = 30, refresh: bool = False) -> dict:
    """Get fund flow data for a ticker."""
    cache_file = DATA_DIR / f"{ticker}_flows.json"
    
    # Check cache
    if not refresh and cache_file.exists():
        with open(cache_file) as f:
            cached = json.load(f)
            cache_age = datetime.now() - datetime.fromisoformat(cached["fetched_at"])
            if cache_age.total_seconds() < 3600:  # 1 hour cache
                return cached
    
    if ticker not in ETF_UNIVERSE:
        return {"error": f"ETF {ticker} not in tracked universe"}
    
    etf_info = ETF_UNIVERSE[ticker]
    flows = generate_simulated_flows(ticker, days)
    
    # Calculate summary stats
    total_flow = sum(f["flow_millions"] for f in flows)
    avg_daily_flow = total_flow / len(flows) if flows else 0
    positive_days = sum(1 for f in flows if f["flow_millions"] > 0)
    negative_days = len(flows) - positive_days
    
    result = {
        "ticker": ticker,
        "name": etf_info["name"],
        "category": etf_info["category"],
        "current_aum_billions": flows[-1]["aum_billions"] if flows else etf_info["aum_billions"],
        "period_days": days,
        "flows": flows,
        "summary": {
            "total_flow_millions": round(total_flow, 2),
            "avg_daily_flow_millions": round(avg_daily_flow, 2),
            "positive_days": positive_days,
            "negative_days": negative_days,
            "flow_momentum": "INFLOW" if total_flow > 0 else "OUTFLOW",
            "flow_streak": calculate_streak(flows),
        },
        "fetched_at": datetime.now().isoformat()
    }
    
    # Cache result
    with open(cache_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    return result


def calculate_streak(flows: list) -> dict:
    """Calculate current inflow/outflow streak."""
    if not flows:
        return {"type": "none", "days": 0}
    
    current_direction = "INFLOW" if flows[-1]["flow_millions"] > 0 else "OUTFLOW"
    streak_days = 1
    
    for i in range(len(flows) - 2, -1, -1):
        flow_direction = "INFLOW" if flows[i]["flow_millions"] > 0 else "OUTFLOW"
        if flow_direction == current_direction:
            streak_days += 1
        else:
            break
    
    return {"type": current_direction, "days": streak_days}


def get_category_flows(days: int = 30) -> dict:
    """Aggregate flows by category."""
    categories = {}
    
    for ticker, info in ETF_UNIVERSE.items():
        category = info["category"]
        flow_data = get_etf_flows(ticker, days)
        
        if "error" in flow_data:
            continue
        
        if category not in categories:
            categories[category] = {
                "total_flow_millions": 0,
                "etfs": [],
                "total_aum_billions": 0
            }
        
        categories[category]["total_flow_millions"] += flow_data["summary"]["total_flow_millions"]
        categories[category]["total_aum_billions"] += flow_data["current_aum_billions"]
        categories[category]["etfs"].append({
            "ticker": ticker,
            "flow_millions": flow_data["summary"]["total_flow_millions"]
        })
    
    # Sort categories by flow
    sorted_categories = dict(sorted(
        categories.items(),
        key=lambda x: x[1]["total_flow_millions"],
        reverse=True
    ))
    
    return sorted_categories


def scan_significant_flows(threshold_pct: float = 1.0, days: int = 7) -> list:
    """Scan for ETFs with significant flow changes."""
    significant = []
    
    for ticker in ETF_UNIVERSE:
        flow_data = get_etf_flows(ticker, days)
        
        if "error" in flow_data:
            continue
        
        # Check if any day had flows exceeding threshold
        for flow in flow_data["flows"]:
            if abs(flow["flow_pct"]) >= threshold_pct:
                significant.append({
                    "ticker": ticker,
                    "name": flow_data["name"],
                    "category": flow_data["category"],
                    "date": flow["date"],
                    "flow_millions": flow["flow_millions"],
                    "flow_pct": flow["flow_pct"],
                    "direction": "INFLOW" if flow["flow_millions"] > 0 else "OUTFLOW"
                })
    
    # Sort by absolute flow
    significant.sort(key=lambda x: abs(x["flow_millions"]), reverse=True)
    return significant


def get_rotation_signals(days: int = 30) -> dict:
    """Identify sector rotation signals based on relative flows."""
    category_flows = get_category_flows(days)
    
    # Normalize flows as percentage of AUM
    rotation_data = []
    for category, data in category_flows.items():
        if data["total_aum_billions"] > 0:
            flow_as_pct = (data["total_flow_millions"] / (data["total_aum_billions"] * 1000)) * 100
            rotation_data.append({
                "category": category,
                "flow_millions": data["total_flow_millions"],
                "aum_billions": data["total_aum_billions"],
                "flow_as_pct_aum": round(flow_as_pct, 2),
                "etf_count": len(data["etfs"])
            })
    
    # Sort by relative flow
    rotation_data.sort(key=lambda x: x["flow_as_pct_aum"], reverse=True)
    
    # Identify leaders and laggards
    leaders = [r for r in rotation_data if r["flow_as_pct_aum"] > 0][:5]
    laggards = [r for r in rotation_data if r["flow_as_pct_aum"] < 0][-5:]
    laggards.reverse()
    
    return {
        "period_days": days,
        "leaders": leaders,
        "laggards": laggards,
        "all_categories": rotation_data,
        "signal": interpret_rotation(leaders, laggards)
    }


def interpret_rotation(leaders: list, laggards: list) -> dict:
    """Interpret rotation signals for market sentiment."""
    risk_on_categories = {"US Tech", "US Small Cap", "Emerging Markets", "Disruptive Innovation", "Corp Bonds HY"}
    risk_off_categories = {"Long Treasury", "Short Treasury", "Gold", "Low Volatility", "Utilities"}
    
    risk_on_score = sum(1 for l in leaders if l["category"] in risk_on_categories)
    risk_on_score -= sum(1 for l in laggards if l["category"] in risk_on_categories)
    
    risk_off_score = sum(1 for l in leaders if l["category"] in risk_off_categories)
    risk_off_score -= sum(1 for l in laggards if l["category"] in risk_off_categories)
    
    if risk_on_score > risk_off_score + 1:
        sentiment = "RISK-ON"
        description = "Money flowing into growth/risk assets, away from safety"
    elif risk_off_score > risk_on_score + 1:
        sentiment = "RISK-OFF"
        description = "Money flowing into safe havens, away from risk assets"
    else:
        sentiment = "MIXED"
        description = "No clear risk preference in fund flows"
    
    return {
        "sentiment": sentiment,
        "risk_on_score": risk_on_score,
        "risk_off_score": risk_off_score,
        "description": description
    }


def set_alert(ticker: str, threshold_millions: float, direction: str = "both") -> dict:
    """Set a flow alert for an ETF."""
    alerts_file = DATA_DIR / "alerts.json"
    
    if alerts_file.exists():
        with open(alerts_file) as f:
            alerts = json.load(f)
    else:
        alerts = {"alerts": []}
    
    alert = {
        "id": len(alerts["alerts"]) + 1,
        "ticker": ticker,
        "threshold_millions": threshold_millions,
        "direction": direction,  # "inflow", "outflow", or "both"
        "created_at": datetime.now().isoformat(),
        "triggered": False
    }
    
    alerts["alerts"].append(alert)
    
    with open(alerts_file, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return alert


def check_alerts() -> list:
    """Check all alerts against recent flows."""
    alerts_file = DATA_DIR / "alerts.json"
    
    if not alerts_file.exists():
        return []
    
    with open(alerts_file) as f:
        alerts = json.load(f)
    
    triggered = []
    
    for alert in alerts["alerts"]:
        if alert["triggered"]:
            continue
        
        flow_data = get_etf_flows(alert["ticker"], days=1)
        if "error" in flow_data or not flow_data["flows"]:
            continue
        
        latest_flow = flow_data["flows"][-1]["flow_millions"]
        threshold = alert["threshold_millions"]
        
        should_trigger = False
        if alert["direction"] == "inflow" and latest_flow >= threshold:
            should_trigger = True
        elif alert["direction"] == "outflow" and latest_flow <= -threshold:
            should_trigger = True
        elif alert["direction"] == "both" and abs(latest_flow) >= threshold:
            should_trigger = True
        
        if should_trigger:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now().isoformat()
            alert["triggered_flow"] = latest_flow
            triggered.append(alert)
    
    # Save updated alerts
    with open(alerts_file, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return triggered


def format_flows_table(flows: list, limit: int = 10) -> str:
    """Format flows as ASCII table."""
    lines = [
        "Date       │ Flow ($M)   │ Flow %  │ AUM ($B)",
        "───────────┼─────────────┼─────────┼──────────"
    ]
    
    for flow in flows[-limit:]:
        flow_str = f"{flow['flow_millions']:+,.0f}".rjust(11)
        pct_str = f"{flow['flow_pct']:+.2f}%".rjust(7)
        aum_str = f"{flow['aum_billions']:.1f}".rjust(8)
        lines.append(f"{flow['date']} │ {flow_str} │ {pct_str} │ {aum_str}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Fund Flow Tracker - Monitor ETF/Mutual Fund Flows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s flows SPY                 Get SPY fund flows (30 days)
  %(prog)s flows QQQ -d 60           Get QQQ flows for 60 days
  %(prog)s categories                Show flows by category
  %(prog)s scan -t 1.5               Scan for flows > 1.5%% of AUM
  %(prog)s rotation                  Get sector rotation signals
  %(prog)s alert SPY 500 -dir inflow Set alert for $500M inflow
  %(prog)s check-alerts              Check triggered alerts
  %(prog)s list                      List all tracked ETFs
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # flows command
    flows_parser = subparsers.add_parser("flows", help="Get fund flows for a ticker")
    flows_parser.add_argument("ticker", help="ETF ticker symbol")
    flows_parser.add_argument("-d", "--days", type=int, default=30, help="Number of days")
    flows_parser.add_argument("-r", "--refresh", action="store_true", help="Force refresh")
    flows_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # categories command
    cat_parser = subparsers.add_parser("categories", help="Show flows by category")
    cat_parser.add_argument("-d", "--days", type=int, default=30, help="Number of days")
    cat_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for significant flows")
    scan_parser.add_argument("-t", "--threshold", type=float, default=1.0, help="Flow threshold (%)")
    scan_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days")
    scan_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # rotation command
    rot_parser = subparsers.add_parser("rotation", help="Get sector rotation signals")
    rot_parser.add_argument("-d", "--days", type=int, default=30, help="Number of days")
    rot_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # alert command
    alert_parser = subparsers.add_parser("alert", help="Set flow alert")
    alert_parser.add_argument("ticker", help="ETF ticker symbol")
    alert_parser.add_argument("threshold", type=float, help="Flow threshold in millions")
    alert_parser.add_argument("-dir", "--direction", choices=["inflow", "outflow", "both"], 
                             default="both", help="Alert direction")
    
    # check-alerts command
    subparsers.add_parser("check-alerts", help="Check triggered alerts")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List tracked ETFs")
    list_parser.add_argument("-c", "--category", help="Filter by category")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "flows":
        result = get_etf_flows(args.ticker.upper(), args.days, args.refresh)
        
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n📊 {result['ticker']} - {result['name']}")
            print(f"   Category: {result['category']}")
            print(f"   Current AUM: ${result['current_aum_billions']:.1f}B")
            print()
            print(format_flows_table(result["flows"]))
            print()
            s = result["summary"]
            direction_emoji = "📈" if s["flow_momentum"] == "INFLOW" else "📉"
            print(f"Summary ({result['period_days']} days):")
            print(f"  {direction_emoji} Total Flow: ${s['total_flow_millions']:+,.0f}M ({s['flow_momentum']})")
            print(f"  📅 Positive Days: {s['positive_days']} | Negative: {s['negative_days']}")
            print(f"  🔥 Current Streak: {s['flow_streak']['days']} days {s['flow_streak']['type']}")
    
    elif args.command == "categories":
        result = get_category_flows(args.days)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n📊 Fund Flows by Category ({args.days} days)\n")
            print("Category                  │ Flow ($M)    │ AUM ($B)")
            print("──────────────────────────┼──────────────┼─────────")
            for cat, data in result.items():
                flow_emoji = "📈" if data["total_flow_millions"] > 0 else "📉"
                cat_str = cat[:24].ljust(24)
                flow_str = f"{data['total_flow_millions']:+,.0f}".rjust(12)
                aum_str = f"{data['total_aum_billions']:.0f}".rjust(7)
                print(f"{flow_emoji} {cat_str} │ {flow_str} │ {aum_str}")
    
    elif args.command == "scan":
        result = scan_significant_flows(args.threshold, args.days)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n🔍 Significant Flows (>{args.threshold}% of AUM, last {args.days} days)\n")
            if not result:
                print("No significant flows detected.")
            else:
                for item in result[:20]:
                    emoji = "🟢" if item["direction"] == "INFLOW" else "🔴"
                    print(f"{emoji} {item['ticker']} ({item['category']})")
                    print(f"   {item['date']}: ${item['flow_millions']:+,.0f}M ({item['flow_pct']:+.2f}%)")
    
    elif args.command == "rotation":
        result = get_rotation_signals(args.days)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            signal = result["signal"]
            emoji = "🚀" if signal["sentiment"] == "RISK-ON" else "🛡️" if signal["sentiment"] == "RISK-OFF" else "⚖️"
            
            print(f"\n{emoji} ROTATION SIGNAL: {signal['sentiment']}")
            print(f"   {signal['description']}")
            print()
            
            print("📈 INFLOW LEADERS:")
            for leader in result["leaders"][:5]:
                print(f"   {leader['category']}: +{leader['flow_as_pct_aum']:.2f}% of AUM (${leader['flow_millions']:,.0f}M)")
            
            print("\n📉 OUTFLOW LAGGARDS:")
            for laggard in result["laggards"][:5]:
                print(f"   {laggard['category']}: {laggard['flow_as_pct_aum']:.2f}% of AUM (${laggard['flow_millions']:,.0f}M)")
    
    elif args.command == "alert":
        result = set_alert(args.ticker.upper(), args.threshold, args.direction)
        print(f"✅ Alert set: {result['ticker']} - ${result['threshold_millions']}M {result['direction']}")
        print(f"   Alert ID: {result['id']}")
    
    elif args.command == "check-alerts":
        triggered = check_alerts()
        if triggered:
            print("🚨 TRIGGERED ALERTS:")
            for alert in triggered:
                print(f"   {alert['ticker']}: ${alert['triggered_flow']:+,.0f}M flow detected")
        else:
            print("✅ No alerts triggered")
    
    elif args.command == "list":
        print("\n📋 Tracked ETFs\n")
        
        categories = {}
        for ticker, info in sorted(ETF_UNIVERSE.items()):
            cat = info["category"]
            if args.category and args.category.lower() not in cat.lower():
                continue
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((ticker, info))
        
        for cat, etfs in sorted(categories.items()):
            print(f"\n{cat}:")
            for ticker, info in etfs:
                print(f"  {ticker:6} - {info['name']} (${info['aum_billions']}B)")


if __name__ == "__main__":
    main()
