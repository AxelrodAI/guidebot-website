#!/usr/bin/env python3
"""
Price Alert System - Multi-asset alerts with complex conditions
Built by PM3 | Backend/CLI Pipeline

Monitor stocks, crypto, forex with customizable alert conditions.
Supports price thresholds, percent changes, volume spikes, and compound rules.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import random
import uuid

# Fix Windows console encoding for emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Data storage
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Asset types and sample data
ASSET_TYPES = {
    "stock": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "BAC", "XOM"],
    "crypto": ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK"],
    "forex": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"],
    "commodity": ["GOLD", "SILVER", "OIL", "NATGAS", "COPPER"],
}

# Base prices for simulation
BASE_PRICES = {
    # Stocks
    "AAPL": 180, "MSFT": 380, "GOOGL": 170, "AMZN": 185, "META": 500,
    "NVDA": 880, "TSLA": 250, "JPM": 195, "BAC": 35, "XOM": 105,
    # Crypto
    "BTC": 97000, "ETH": 3400, "SOL": 240, "BNB": 680, "XRP": 3.10,
    "ADA": 1.05, "DOGE": 0.35, "AVAX": 35, "DOT": 7.5, "LINK": 22,
    # Forex
    "EUR/USD": 1.08, "GBP/USD": 1.26, "USD/JPY": 156.5,
    "USD/CHF": 0.90, "AUD/USD": 0.62, "USD/CAD": 1.44,
    # Commodities
    "GOLD": 2650, "SILVER": 30.5, "OIL": 72, "NATGAS": 3.2, "COPPER": 4.1,
}

# Alert condition types
CONDITION_TYPES = [
    "price_above",      # Price crosses above threshold
    "price_below",      # Price crosses below threshold
    "pct_change_up",    # % change from reference price
    "pct_change_down",  # % change from reference price
    "volume_spike",     # Volume exceeds multiple of average
    "moving_avg_cross", # Price crosses moving average
]


def get_asset_type(symbol: str) -> str:
    """Determine asset type from symbol."""
    symbol = symbol.upper()
    for atype, symbols in ASSET_TYPES.items():
        if symbol in symbols:
            return atype
    return "stock"  # Default


def get_current_price(symbol: str) -> dict:
    """Get simulated current price and market data."""
    symbol = symbol.upper()
    base_price = BASE_PRICES.get(symbol, 100)
    
    # Add random variation (+/- 3%)
    price = base_price * (1 + random.uniform(-0.03, 0.03))
    
    # Simulated daily change
    change_pct = random.uniform(-5, 5)
    prev_close = price / (1 + change_pct / 100)
    
    # Simulated volume (millions)
    avg_volume = random.uniform(5, 50)
    volume = avg_volume * (1 + random.uniform(-0.5, 1.5))
    
    return {
        "symbol": symbol,
        "price": round(price, 4 if "/" in symbol or symbol in ["XRP", "ADA", "DOGE"] else 2),
        "prev_close": round(prev_close, 4 if "/" in symbol else 2),
        "change": round(price - prev_close, 4 if "/" in symbol else 2),
        "change_pct": round(change_pct, 2),
        "volume_millions": round(volume, 2),
        "avg_volume_millions": round(avg_volume, 2),
        "volume_ratio": round(volume / avg_volume, 2),
        "high_24h": round(price * 1.02, 4 if "/" in symbol else 2),
        "low_24h": round(price * 0.98, 4 if "/" in symbol else 2),
        "timestamp": datetime.now().isoformat(),
        "asset_type": get_asset_type(symbol),
    }


def load_alerts() -> dict:
    """Load alerts from data file."""
    alerts_file = DATA_DIR / "alerts.json"
    
    if alerts_file.exists():
        with open(alerts_file) as f:
            return json.load(f)
    
    return {"alerts": [], "history": []}


def save_alerts(data: dict):
    """Save alerts to data file."""
    alerts_file = DATA_DIR / "alerts.json"
    with open(alerts_file, 'w') as f:
        json.dump(data, f, indent=2)


def create_alert(
    symbol: str,
    condition: str,
    threshold: float,
    note: str = None,
    repeat: bool = False,
    expiry_hours: int = None
) -> dict:
    """Create a new price alert."""
    data = load_alerts()
    current = get_current_price(symbol)
    
    alert = {
        "id": str(uuid.uuid4())[:8],
        "symbol": symbol.upper(),
        "asset_type": current["asset_type"],
        "condition": condition,
        "threshold": threshold,
        "reference_price": current["price"],
        "note": note,
        "repeat": repeat,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=expiry_hours)).isoformat() if expiry_hours else None,
        "status": "active",
        "triggered_count": 0,
    }
    
    data["alerts"].append(alert)
    save_alerts(data)
    
    return alert


def create_compound_alert(
    alerts: list,
    operator: str = "AND",
    note: str = None
) -> dict:
    """Create a compound alert with multiple conditions."""
    data = load_alerts()
    
    compound = {
        "id": str(uuid.uuid4())[:8],
        "type": "compound",
        "operator": operator,  # AND / OR
        "conditions": alerts,
        "note": note,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "triggered_count": 0,
    }
    
    data["alerts"].append(compound)
    save_alerts(data)
    
    return compound


def check_condition(alert: dict, market_data: dict) -> tuple:
    """Check if a single condition is met. Returns (triggered, message)."""
    condition = alert["condition"]
    threshold = alert["threshold"]
    price = market_data["price"]
    ref_price = alert.get("reference_price", price)
    
    if condition == "price_above":
        if price >= threshold:
            return True, f"Price ${price:,.2f} crossed above ${threshold:,.2f}"
        return False, None
    
    elif condition == "price_below":
        if price <= threshold:
            return True, f"Price ${price:,.2f} crossed below ${threshold:,.2f}"
        return False, None
    
    elif condition == "pct_change_up":
        pct_change = ((price - ref_price) / ref_price) * 100
        if pct_change >= threshold:
            return True, f"Price up {pct_change:.1f}% from ${ref_price:,.2f}"
        return False, None
    
    elif condition == "pct_change_down":
        pct_change = ((ref_price - price) / ref_price) * 100
        if pct_change >= threshold:
            return True, f"Price down {pct_change:.1f}% from ${ref_price:,.2f}"
        return False, None
    
    elif condition == "volume_spike":
        if market_data["volume_ratio"] >= threshold:
            return True, f"Volume {market_data['volume_ratio']:.1f}x above average"
        return False, None
    
    elif condition == "moving_avg_cross":
        # Simplified: compare to threshold as a "moving average"
        if price > threshold and ref_price <= threshold:
            return True, f"Price ${price:,.2f} crossed above MA ${threshold:,.2f}"
        return False, None
    
    return False, None


def check_alerts() -> list:
    """Check all active alerts against current prices."""
    data = load_alerts()
    triggered = []
    now = datetime.now()
    
    for alert in data["alerts"]:
        if alert["status"] != "active":
            continue
        
        # Check expiry
        if alert.get("expires_at"):
            expiry = datetime.fromisoformat(alert["expires_at"])
            if now > expiry:
                alert["status"] = "expired"
                continue
        
        # Handle compound alerts
        if alert.get("type") == "compound":
            results = []
            for sub_alert in alert["conditions"]:
                market = get_current_price(sub_alert["symbol"])
                is_triggered, msg = check_condition(sub_alert, market)
                results.append((is_triggered, sub_alert["symbol"], msg))
            
            if alert["operator"] == "AND":
                all_triggered = all(r[0] for r in results)
                if all_triggered:
                    alert["triggered_count"] += 1
                    alert["last_triggered"] = now.isoformat()
                    if not alert.get("repeat"):
                        alert["status"] = "triggered"
                    triggered.append({
                        "alert": alert,
                        "type": "compound",
                        "messages": [r[2] for r in results if r[2]]
                    })
            else:  # OR
                any_triggered = any(r[0] for r in results)
                if any_triggered:
                    alert["triggered_count"] += 1
                    alert["last_triggered"] = now.isoformat()
                    if not alert.get("repeat"):
                        alert["status"] = "triggered"
                    triggered.append({
                        "alert": alert,
                        "type": "compound",
                        "messages": [r[2] for r in results if r[0] and r[2]]
                    })
        else:
            # Simple alert
            market = get_current_price(alert["symbol"])
            is_triggered, message = check_condition(alert, market)
            
            if is_triggered:
                alert["triggered_count"] += 1
                alert["last_triggered"] = now.isoformat()
                if not alert.get("repeat"):
                    alert["status"] = "triggered"
                
                triggered.append({
                    "alert": alert,
                    "market": market,
                    "message": message
                })
                
                # Add to history
                data["history"].append({
                    "alert_id": alert["id"],
                    "symbol": alert["symbol"],
                    "condition": alert["condition"],
                    "triggered_at": now.isoformat(),
                    "price": market["price"],
                    "message": message
                })
    
    # Keep history manageable (last 1000)
    data["history"] = data["history"][-1000:]
    
    save_alerts(data)
    return triggered


def list_alerts(status: str = None, symbol: str = None) -> list:
    """List alerts with optional filters."""
    data = load_alerts()
    alerts = data["alerts"]
    
    if status:
        alerts = [a for a in alerts if a["status"] == status]
    
    if symbol:
        symbol = symbol.upper()
        alerts = [a for a in alerts if a.get("symbol") == symbol or 
                  any(c.get("symbol") == symbol for c in a.get("conditions", []))]
    
    return alerts


def delete_alert(alert_id: str) -> bool:
    """Delete an alert by ID."""
    data = load_alerts()
    
    for i, alert in enumerate(data["alerts"]):
        if alert["id"] == alert_id:
            data["alerts"].pop(i)
            save_alerts(data)
            return True
    
    return False


def get_history(symbol: str = None, limit: int = 20) -> list:
    """Get alert trigger history."""
    data = load_alerts()
    history = data.get("history", [])
    
    if symbol:
        symbol = symbol.upper()
        history = [h for h in history if h.get("symbol") == symbol]
    
    return history[-limit:]


def get_quote(symbol: str) -> dict:
    """Get current quote for a symbol."""
    return get_current_price(symbol)


def get_watchlist() -> list:
    """Get unique symbols from active alerts."""
    data = load_alerts()
    symbols = set()
    
    for alert in data["alerts"]:
        if alert["status"] == "active":
            if alert.get("symbol"):
                symbols.add(alert["symbol"])
            for cond in alert.get("conditions", []):
                if cond.get("symbol"):
                    symbols.add(cond["symbol"])
    
    return sorted(list(symbols))


def format_condition(condition: str, threshold: float) -> str:
    """Format condition for display."""
    conditions_display = {
        "price_above": f"Price > ${threshold:,.2f}",
        "price_below": f"Price < ${threshold:,.2f}",
        "pct_change_up": f"Up {threshold}%",
        "pct_change_down": f"Down {threshold}%",
        "volume_spike": f"Volume > {threshold}x avg",
        "moving_avg_cross": f"Cross above MA ${threshold:,.2f}",
    }
    return conditions_display.get(condition, f"{condition}: {threshold}")


def main():
    parser = argparse.ArgumentParser(
        description="Price Alert System - Multi-asset alerts with complex conditions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s quote AAPL                    Get current quote
  %(prog)s quote BTC                     Get crypto quote
  %(prog)s set AAPL price_above 200      Alert when AAPL > $200
  %(prog)s set NVDA pct_change_down 10   Alert on 10%% drop
  %(prog)s set ETH volume_spike 2        Alert on 2x volume
  %(prog)s list                          List all alerts
  %(prog)s list --active                 List active alerts
  %(prog)s check                         Check and trigger alerts
  %(prog)s delete abc123                 Delete alert by ID
  %(prog)s history                       View trigger history
  %(prog)s watchlist                     View watched symbols

Conditions:
  price_above      Price crosses above threshold
  price_below      Price crosses below threshold
  pct_change_up    % increase from creation price
  pct_change_down  % decrease from creation price
  volume_spike     Volume exceeds multiple of average
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # quote command
    quote_parser = subparsers.add_parser("quote", help="Get current quote")
    quote_parser.add_argument("symbol", help="Symbol (AAPL, BTC, EUR/USD, etc)")
    quote_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # set command
    set_parser = subparsers.add_parser("set", help="Create price alert")
    set_parser.add_argument("symbol", help="Symbol to monitor")
    set_parser.add_argument("condition", choices=CONDITION_TYPES, help="Alert condition")
    set_parser.add_argument("threshold", type=float, help="Threshold value")
    set_parser.add_argument("-n", "--note", help="Alert note")
    set_parser.add_argument("-r", "--repeat", action="store_true", help="Repeat alert")
    set_parser.add_argument("-e", "--expires", type=int, help="Expiry in hours")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List alerts")
    list_parser.add_argument("--active", action="store_true", help="Active only")
    list_parser.add_argument("-s", "--symbol", help="Filter by symbol")
    list_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # check command
    check_parser = subparsers.add_parser("check", help="Check and trigger alerts")
    check_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete alert")
    delete_parser.add_argument("alert_id", help="Alert ID to delete")
    
    # history command
    history_parser = subparsers.add_parser("history", help="View trigger history")
    history_parser.add_argument("-s", "--symbol", help="Filter by symbol")
    history_parser.add_argument("-l", "--limit", type=int, default=20, help="Number of entries")
    history_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # watchlist command
    subparsers.add_parser("watchlist", help="View watched symbols")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "quote":
        quote = get_quote(args.symbol)
        
        if args.json:
            print(json.dumps(quote, indent=2))
        else:
            change_emoji = "📈" if quote["change"] >= 0 else "📉"
            asset_emoji = {"stock": "📊", "crypto": "🪙", "forex": "💱", "commodity": "🛢️"}.get(quote["asset_type"], "📊")
            
            print(f"\n{asset_emoji} {quote['symbol']} ({quote['asset_type'].upper()})")
            print(f"   Price: ${quote['price']:,.4f}" if "/" in quote["symbol"] or quote["price"] < 10 else f"   Price: ${quote['price']:,.2f}")
            print(f"   {change_emoji} Change: {quote['change']:+,.4f} ({quote['change_pct']:+.2f}%)")
            print(f"   24h Range: ${quote['low_24h']:,.2f} - ${quote['high_24h']:,.2f}")
            print(f"   Volume: {quote['volume_millions']:.1f}M ({quote['volume_ratio']:.1f}x avg)")
    
    elif args.command == "set":
        alert = create_alert(
            symbol=args.symbol,
            condition=args.condition,
            threshold=args.threshold,
            note=args.note,
            repeat=args.repeat,
            expiry_hours=args.expires
        )
        
        cond_str = format_condition(args.condition, args.threshold)
        print(f"✅ Alert created: {alert['symbol']} - {cond_str}")
        print(f"   ID: {alert['id']}")
        print(f"   Reference: ${alert['reference_price']:,.2f}")
        if alert["expires_at"]:
            print(f"   Expires: {alert['expires_at'][:16]}")
        if args.repeat:
            print(f"   Mode: Repeating")
    
    elif args.command == "list":
        status = "active" if args.active else None
        alerts = list_alerts(status=status, symbol=args.symbol)
        
        if args.json:
            print(json.dumps(alerts, indent=2))
        else:
            if not alerts:
                print("No alerts found.")
            else:
                print(f"\n📋 PRICE ALERTS ({len(alerts)})\n")
                
                for alert in alerts:
                    if alert.get("type") == "compound":
                        status_emoji = "🟢" if alert["status"] == "active" else "🔴" if alert["status"] == "triggered" else "⚪"
                        print(f"{status_emoji} [{alert['id']}] COMPOUND ({alert['operator']})")
                        for cond in alert["conditions"]:
                            cond_str = format_condition(cond["condition"], cond["threshold"])
                            print(f"      {cond['symbol']}: {cond_str}")
                    else:
                        status_emoji = "🟢" if alert["status"] == "active" else "🔴" if alert["status"] == "triggered" else "⚪"
                        cond_str = format_condition(alert["condition"], alert["threshold"])
                        repeat_flag = " 🔄" if alert.get("repeat") else ""
                        print(f"{status_emoji} [{alert['id']}] {alert['symbol']}: {cond_str}{repeat_flag}")
                        if alert.get("note"):
                            print(f"      Note: {alert['note']}")
                        if alert.get("triggered_count", 0) > 0:
                            print(f"      Triggered: {alert['triggered_count']}x")
    
    elif args.command == "check":
        triggered = check_alerts()
        
        if args.json:
            print(json.dumps(triggered, indent=2, default=str))
        else:
            if not triggered:
                print("✅ No alerts triggered")
            else:
                print(f"\n🚨 TRIGGERED ALERTS ({len(triggered)})\n")
                for t in triggered:
                    alert = t["alert"]
                    if t.get("type") == "compound":
                        print(f"🔔 COMPOUND ALERT [{alert['id']}]")
                        for msg in t["messages"]:
                            print(f"   • {msg}")
                    else:
                        market = t["market"]
                        print(f"🔔 {alert['symbol']} [{alert['id']}]")
                        print(f"   {t['message']}")
                        print(f"   Current: ${market['price']:,.2f} ({market['change_pct']:+.2f}%)")
                    if alert.get("note"):
                        print(f"   Note: {alert['note']}")
                    print()
    
    elif args.command == "delete":
        if delete_alert(args.alert_id):
            print(f"✅ Alert {args.alert_id} deleted")
        else:
            print(f"❌ Alert {args.alert_id} not found")
    
    elif args.command == "history":
        history = get_history(symbol=args.symbol, limit=args.limit)
        
        if args.json:
            print(json.dumps(history, indent=2))
        else:
            if not history:
                print("No trigger history.")
            else:
                print(f"\n📜 TRIGGER HISTORY\n")
                for h in reversed(history):
                    dt = datetime.fromisoformat(h["triggered_at"]).strftime("%m/%d %H:%M")
                    print(f"   {dt} | {h['symbol']}: {h['message']}")
    
    elif args.command == "watchlist":
        symbols = get_watchlist()
        
        if not symbols:
            print("No symbols being watched.")
        else:
            print(f"\n👁️ WATCHLIST ({len(symbols)} symbols)\n")
            for symbol in symbols:
                quote = get_quote(symbol)
                change_emoji = "📈" if quote["change"] >= 0 else "📉"
                print(f"   {symbol:10} ${quote['price']:>10,.2f}  {change_emoji} {quote['change_pct']:+.2f}%")


if __name__ == "__main__":
    main()
