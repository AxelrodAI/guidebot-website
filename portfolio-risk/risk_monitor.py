#!/usr/bin/env python3
"""
Portfolio Risk Monitor - Track concentration, correlation, volatility
Built by PM3 | Backend/CLI Pipeline

Monitor portfolio risk metrics to identify overconcentration, correlation clustering,
and volatility spikes before they become problems.
"""

import argparse
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
import random

# Fix Windows console encoding for emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Data storage
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Risk thresholds
RISK_THRESHOLDS = {
    "single_position_max": 0.25,       # 25% max single position
    "sector_max": 0.40,                # 40% max sector exposure
    "correlation_warning": 0.70,       # High correlation threshold
    "volatility_spike_pct": 50,        # 50% increase from baseline
    "concentration_hhi_warning": 1500, # HHI above this is concentrated
    "beta_max": 1.5,                   # Portfolio beta warning
    "var_confidence": 0.95,            # VaR confidence level
}

# Sector classification
SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology", "AMZN": "Consumer Discretionary",
    "META": "Technology", "NVDA": "Technology", "TSLA": "Consumer Discretionary", "AMD": "Technology",
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials", "MS": "Financials", "C": "Financials",
    "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare", "MRK": "Healthcare", "ABBV": "Healthcare",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    "PG": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples", "WMT": "Consumer Staples",
    "DIS": "Communication Services", "NFLX": "Communication Services", "CMCSA": "Communication Services",
    "CAT": "Industrials", "HON": "Industrials", "UPS": "Industrials", "BA": "Industrials",
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities",
    "AMT": "Real Estate", "PLD": "Real Estate", "CCI": "Real Estate",
    "LIN": "Materials", "APD": "Materials", "FCX": "Materials",
}


def load_portfolio() -> dict:
    """Load portfolio from data file or create sample."""
    portfolio_file = DATA_DIR / "portfolio.json"
    
    if portfolio_file.exists():
        with open(portfolio_file) as f:
            return json.load(f)
    
    # Sample portfolio
    sample = {
        "name": "Sample Portfolio",
        "created_at": datetime.now().isoformat(),
        "positions": [
            {"ticker": "AAPL", "shares": 100, "cost_basis": 150.00},
            {"ticker": "MSFT", "shares": 50, "cost_basis": 280.00},
            {"ticker": "GOOGL", "shares": 20, "cost_basis": 140.00},
            {"ticker": "NVDA", "shares": 30, "cost_basis": 450.00},
            {"ticker": "JPM", "shares": 40, "cost_basis": 150.00},
            {"ticker": "JNJ", "shares": 25, "cost_basis": 160.00},
            {"ticker": "XOM", "shares": 60, "cost_basis": 95.00},
            {"ticker": "PG", "shares": 35, "cost_basis": 150.00},
        ]
    }
    
    save_portfolio(sample)
    return sample


def save_portfolio(portfolio: dict):
    """Save portfolio to data file."""
    portfolio_file = DATA_DIR / "portfolio.json"
    portfolio["updated_at"] = datetime.now().isoformat()
    with open(portfolio_file, 'w') as f:
        json.dump(portfolio, f, indent=2)


def get_simulated_price(ticker: str) -> float:
    """Get simulated current price for a ticker."""
    # Base prices (roughly accurate as of late 2024)
    base_prices = {
        "AAPL": 180, "MSFT": 380, "GOOGL": 170, "AMZN": 185, "META": 500,
        "NVDA": 880, "TSLA": 250, "AMD": 140, "JPM": 195, "BAC": 35,
        "GS": 450, "MS": 95, "C": 55, "JNJ": 155, "UNH": 540,
        "PFE": 28, "MRK": 120, "ABBV": 175, "XOM": 105, "CVX": 145,
        "COP": 115, "SLB": 50, "PG": 165, "KO": 60, "PEP": 170,
        "WMT": 165, "DIS": 110, "NFLX": 480, "CMCSA": 42, "CAT": 340,
        "HON": 210, "UPS": 140, "BA": 210, "NEE": 75, "DUK": 100,
        "SO": 80, "AMT": 200, "PLD": 130, "CCI": 110, "LIN": 440,
        "APD": 280, "FCX": 42,
    }
    
    base = base_prices.get(ticker, 100)
    # Add some random variation (+/- 5%)
    return base * (1 + random.uniform(-0.05, 0.05))


def get_simulated_volatility(ticker: str) -> float:
    """Get simulated annualized volatility for a ticker."""
    # Rough historical volatilities
    vol_map = {
        "AAPL": 0.28, "MSFT": 0.25, "GOOGL": 0.30, "AMZN": 0.35, "META": 0.40,
        "NVDA": 0.55, "TSLA": 0.65, "AMD": 0.50, "JPM": 0.25, "BAC": 0.30,
        "GS": 0.30, "JNJ": 0.15, "UNH": 0.22, "XOM": 0.25, "CVX": 0.25,
        "PG": 0.15, "KO": 0.15, "DIS": 0.30, "NFLX": 0.45, "CAT": 0.25,
    }
    base_vol = vol_map.get(ticker, 0.25)
    return base_vol * (1 + random.uniform(-0.1, 0.1))


def get_simulated_beta(ticker: str) -> float:
    """Get simulated beta for a ticker."""
    beta_map = {
        "AAPL": 1.25, "MSFT": 1.10, "GOOGL": 1.15, "AMZN": 1.30, "META": 1.35,
        "NVDA": 1.80, "TSLA": 2.00, "AMD": 1.70, "JPM": 1.15, "BAC": 1.35,
        "GS": 1.30, "JNJ": 0.60, "UNH": 0.85, "XOM": 0.90, "CVX": 0.95,
        "PG": 0.45, "KO": 0.55, "DIS": 1.20, "NFLX": 1.40, "CAT": 1.10,
    }
    base_beta = beta_map.get(ticker, 1.0)
    return base_beta * (1 + random.uniform(-0.05, 0.05))


def get_simulated_correlation(ticker1: str, ticker2: str) -> float:
    """Get simulated correlation between two tickers."""
    sector1 = SECTOR_MAP.get(ticker1, "Other")
    sector2 = SECTOR_MAP.get(ticker2, "Other")
    
    if ticker1 == ticker2:
        return 1.0
    
    # Same sector = higher correlation
    if sector1 == sector2:
        base = 0.65 + random.uniform(0, 0.25)
    # Different sectors
    else:
        base = 0.30 + random.uniform(-0.20, 0.30)
    
    return min(0.95, max(-0.30, base))


def calculate_position_values(portfolio: dict) -> list:
    """Calculate current values for all positions."""
    positions = []
    
    for pos in portfolio["positions"]:
        ticker = pos["ticker"]
        shares = pos["shares"]
        cost_basis = pos["cost_basis"]
        current_price = get_simulated_price(ticker)
        
        market_value = shares * current_price
        cost_value = shares * cost_basis
        gain_loss = market_value - cost_value
        gain_loss_pct = (gain_loss / cost_value) * 100
        
        positions.append({
            "ticker": ticker,
            "shares": shares,
            "cost_basis": cost_basis,
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "cost_value": round(cost_value, 2),
            "gain_loss": round(gain_loss, 2),
            "gain_loss_pct": round(gain_loss_pct, 2),
            "sector": SECTOR_MAP.get(ticker, "Other"),
            "volatility": get_simulated_volatility(ticker),
            "beta": get_simulated_beta(ticker),
        })
    
    return positions


def analyze_concentration(positions: list) -> dict:
    """Analyze portfolio concentration risk."""
    total_value = sum(p["market_value"] for p in positions)
    
    # Position-level concentration
    position_weights = []
    for pos in positions:
        weight = pos["market_value"] / total_value
        position_weights.append({
            "ticker": pos["ticker"],
            "weight": round(weight * 100, 2),
            "value": pos["market_value"],
            "overweight": weight > RISK_THRESHOLDS["single_position_max"]
        })
    
    # Sort by weight descending
    position_weights.sort(key=lambda x: x["weight"], reverse=True)
    
    # Calculate HHI (Herfindahl-Hirschman Index)
    hhi = sum((p["weight"] ** 2) for p in position_weights)
    
    # Sector concentration
    sector_values = {}
    for pos in positions:
        sector = pos["sector"]
        sector_values[sector] = sector_values.get(sector, 0) + pos["market_value"]
    
    sector_weights = []
    for sector, value in sector_values.items():
        weight = value / total_value
        sector_weights.append({
            "sector": sector,
            "weight": round(weight * 100, 2),
            "value": round(value, 2),
            "overweight": weight > RISK_THRESHOLDS["sector_max"]
        })
    
    sector_weights.sort(key=lambda x: x["weight"], reverse=True)
    
    # Top holdings concentration
    top_5_weight = sum(p["weight"] for p in position_weights[:5])
    
    return {
        "total_value": round(total_value, 2),
        "position_count": len(positions),
        "positions": position_weights,
        "sectors": sector_weights,
        "hhi": round(hhi, 2),
        "hhi_interpretation": "Concentrated" if hhi > RISK_THRESHOLDS["concentration_hhi_warning"] else "Diversified",
        "top_5_concentration": round(top_5_weight, 2),
        "warnings": [
            f"{p['ticker']} is {p['weight']:.1f}% (max {RISK_THRESHOLDS['single_position_max']*100:.0f}%)"
            for p in position_weights if p["overweight"]
        ] + [
            f"{s['sector']} sector is {s['weight']:.1f}% (max {RISK_THRESHOLDS['sector_max']*100:.0f}%)"
            for s in sector_weights if s["overweight"]
        ]
    }


def analyze_correlation(positions: list) -> dict:
    """Analyze portfolio correlation risk."""
    n = len(positions)
    correlations = []
    
    high_corr_pairs = []
    
    for i in range(n):
        for j in range(i + 1, n):
            ticker1 = positions[i]["ticker"]
            ticker2 = positions[j]["ticker"]
            corr = get_simulated_correlation(ticker1, ticker2)
            
            correlations.append({
                "pair": f"{ticker1}/{ticker2}",
                "correlation": round(corr, 3)
            })
            
            if corr >= RISK_THRESHOLDS["correlation_warning"]:
                high_corr_pairs.append({
                    "pair": f"{ticker1}/{ticker2}",
                    "correlation": round(corr, 3),
                    "sectors": f"{positions[i]['sector']}/{positions[j]['sector']}"
                })
    
    # Calculate average correlation
    avg_corr = sum(c["correlation"] for c in correlations) / len(correlations) if correlations else 0
    
    # Sort correlations
    correlations.sort(key=lambda x: x["correlation"], reverse=True)
    
    return {
        "average_correlation": round(avg_corr, 3),
        "high_correlation_pairs": high_corr_pairs,
        "correlation_risk": "High" if avg_corr > 0.5 else "Moderate" if avg_corr > 0.3 else "Low",
        "top_correlations": correlations[:10],
        "lowest_correlations": correlations[-5:],
        "warnings": [
            f"{p['pair']}: {p['correlation']:.2f} correlation ({p['sectors']})"
            for p in high_corr_pairs
        ]
    }


def analyze_volatility(positions: list) -> dict:
    """Analyze portfolio volatility risk."""
    total_value = sum(p["market_value"] for p in positions)
    
    # Weighted volatility (simplified - ignores correlation for portfolio vol)
    weighted_vol_sq = 0
    position_vols = []
    
    for pos in positions:
        weight = pos["market_value"] / total_value
        vol = pos["volatility"]
        position_vols.append({
            "ticker": pos["ticker"],
            "volatility": round(vol * 100, 2),
            "weight": round(weight * 100, 2),
            "contribution": round(weight * vol * 100, 2)
        })
        weighted_vol_sq += (weight * vol) ** 2
    
    # This is a simplified estimate (true portfolio vol requires full correlation matrix)
    portfolio_vol = math.sqrt(weighted_vol_sq) * 1.5  # Adjust for correlation
    
    # Calculate Value at Risk (95% confidence)
    daily_var = total_value * portfolio_vol / math.sqrt(252) * 1.65
    monthly_var = daily_var * math.sqrt(21)
    
    position_vols.sort(key=lambda x: x["volatility"], reverse=True)
    
    # Beta analysis
    weighted_beta = sum(
        (p["market_value"] / total_value) * p["beta"]
        for p in positions
    )
    
    return {
        "portfolio_volatility_annual": round(portfolio_vol * 100, 2),
        "portfolio_volatility_daily": round(portfolio_vol / math.sqrt(252) * 100, 2),
        "portfolio_beta": round(weighted_beta, 2),
        "var_95_daily": round(daily_var, 2),
        "var_95_monthly": round(monthly_var, 2),
        "position_volatilities": position_vols,
        "volatility_level": "High" if portfolio_vol > 0.30 else "Moderate" if portfolio_vol > 0.20 else "Low",
        "beta_risk": "Aggressive" if weighted_beta > RISK_THRESHOLDS["beta_max"] else "Moderate" if weighted_beta > 1.0 else "Defensive",
        "warnings": [
            f"Portfolio beta of {weighted_beta:.2f} exceeds {RISK_THRESHOLDS['beta_max']}"
        ] if weighted_beta > RISK_THRESHOLDS["beta_max"] else []
    }


def generate_risk_report(portfolio: dict) -> dict:
    """Generate comprehensive risk report."""
    positions = calculate_position_values(portfolio)
    
    concentration = analyze_concentration(positions)
    correlation = analyze_correlation(positions)
    volatility = analyze_volatility(positions)
    
    # Aggregate all warnings
    all_warnings = (
        concentration["warnings"] +
        correlation["warnings"] +
        volatility["warnings"]
    )
    
    # Overall risk score (0-100)
    risk_factors = [
        concentration["hhi"] / 30,  # HHI contribution
        correlation["average_correlation"] * 50,  # Correlation contribution
        volatility["portfolio_volatility_annual"],  # Vol contribution
        volatility["portfolio_beta"] * 10,  # Beta contribution
    ]
    risk_score = min(100, sum(risk_factors))
    
    return {
        "portfolio_name": portfolio.get("name", "Portfolio"),
        "report_date": datetime.now().isoformat(),
        "summary": {
            "total_value": concentration["total_value"],
            "position_count": concentration["position_count"],
            "risk_score": round(risk_score, 1),
            "risk_level": "High" if risk_score > 70 else "Moderate" if risk_score > 40 else "Low",
        },
        "concentration": concentration,
        "correlation": correlation,
        "volatility": volatility,
        "warnings": all_warnings,
        "recommendations": generate_recommendations(concentration, correlation, volatility)
    }


def generate_recommendations(concentration: dict, correlation: dict, volatility: dict) -> list:
    """Generate risk mitigation recommendations."""
    recs = []
    
    # Concentration recommendations
    if concentration["hhi"] > RISK_THRESHOLDS["concentration_hhi_warning"]:
        recs.append({
            "area": "Concentration",
            "severity": "Medium",
            "recommendation": f"Portfolio HHI of {concentration['hhi']:.0f} indicates concentration. Consider diversifying into additional positions."
        })
    
    for pos in concentration["positions"][:3]:
        if pos["overweight"]:
            recs.append({
                "area": "Position Size",
                "severity": "High",
                "recommendation": f"Reduce {pos['ticker']} from {pos['weight']:.1f}% to under {RISK_THRESHOLDS['single_position_max']*100:.0f}%"
            })
    
    # Sector recommendations
    for sector in concentration["sectors"]:
        if sector["overweight"]:
            recs.append({
                "area": "Sector Exposure",
                "severity": "Medium",
                "recommendation": f"Reduce {sector['sector']} exposure from {sector['weight']:.1f}% to under {RISK_THRESHOLDS['sector_max']*100:.0f}%"
            })
    
    # Correlation recommendations
    if len(correlation["high_correlation_pairs"]) > 3:
        recs.append({
            "area": "Correlation",
            "severity": "Medium",
            "recommendation": "Multiple highly correlated positions detected. Consider adding uncorrelated assets like bonds or commodities."
        })
    
    # Volatility recommendations
    if volatility["volatility_level"] == "High":
        recs.append({
            "area": "Volatility",
            "severity": "Medium",
            "recommendation": f"Portfolio volatility of {volatility['portfolio_volatility_annual']:.1f}% is elevated. Consider adding low-volatility positions."
        })
    
    if volatility["beta_risk"] == "Aggressive":
        recs.append({
            "area": "Beta",
            "severity": "Medium",
            "recommendation": f"Portfolio beta of {volatility['portfolio_beta']:.2f} indicates high market sensitivity. Add defensive positions to reduce beta."
        })
    
    if not recs:
        recs.append({
            "area": "Overall",
            "severity": "Info",
            "recommendation": "Portfolio risk metrics are within acceptable ranges. Continue monitoring."
        })
    
    return recs


def add_position(ticker: str, shares: int, cost_basis: float) -> dict:
    """Add a position to the portfolio."""
    portfolio = load_portfolio()
    
    # Check if position exists
    for pos in portfolio["positions"]:
        if pos["ticker"].upper() == ticker.upper():
            # Average into existing position
            old_shares = pos["shares"]
            old_cost = pos["cost_basis"]
            new_total_shares = old_shares + shares
            new_avg_cost = ((old_shares * old_cost) + (shares * cost_basis)) / new_total_shares
            pos["shares"] = new_total_shares
            pos["cost_basis"] = round(new_avg_cost, 2)
            save_portfolio(portfolio)
            return {"status": "updated", "position": pos}
    
    # Add new position
    new_pos = {
        "ticker": ticker.upper(),
        "shares": shares,
        "cost_basis": cost_basis
    }
    portfolio["positions"].append(new_pos)
    save_portfolio(portfolio)
    return {"status": "added", "position": new_pos}


def remove_position(ticker: str) -> dict:
    """Remove a position from the portfolio."""
    portfolio = load_portfolio()
    
    for i, pos in enumerate(portfolio["positions"]):
        if pos["ticker"].upper() == ticker.upper():
            removed = portfolio["positions"].pop(i)
            save_portfolio(portfolio)
            return {"status": "removed", "position": removed}
    
    return {"status": "not_found", "ticker": ticker}


def set_alert(metric: str, threshold: float, direction: str = "above") -> dict:
    """Set a risk alert."""
    alerts_file = DATA_DIR / "alerts.json"
    
    if alerts_file.exists():
        with open(alerts_file) as f:
            alerts = json.load(f)
    else:
        alerts = {"alerts": []}
    
    alert = {
        "id": len(alerts["alerts"]) + 1,
        "metric": metric,
        "threshold": threshold,
        "direction": direction,
        "created_at": datetime.now().isoformat(),
        "triggered": False
    }
    
    alerts["alerts"].append(alert)
    
    with open(alerts_file, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return alert


def check_alerts() -> list:
    """Check if any alerts are triggered."""
    alerts_file = DATA_DIR / "alerts.json"
    
    if not alerts_file.exists():
        return []
    
    with open(alerts_file) as f:
        alerts = json.load(f)
    
    portfolio = load_portfolio()
    report = generate_risk_report(portfolio)
    
    # Map metrics to values
    metric_values = {
        "risk_score": report["summary"]["risk_score"],
        "hhi": report["concentration"]["hhi"],
        "correlation": report["correlation"]["average_correlation"] * 100,
        "volatility": report["volatility"]["portfolio_volatility_annual"],
        "beta": report["volatility"]["portfolio_beta"],
        "var_daily": report["volatility"]["var_95_daily"],
    }
    
    triggered = []
    
    for alert in alerts["alerts"]:
        if alert["triggered"]:
            continue
        
        metric = alert["metric"]
        if metric not in metric_values:
            continue
        
        current_value = metric_values[metric]
        threshold = alert["threshold"]
        
        should_trigger = False
        if alert["direction"] == "above" and current_value > threshold:
            should_trigger = True
        elif alert["direction"] == "below" and current_value < threshold:
            should_trigger = True
        
        if should_trigger:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now().isoformat()
            alert["triggered_value"] = current_value
            triggered.append(alert)
    
    # Save updated alerts
    with open(alerts_file, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return triggered


def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Risk Monitor - Track concentration, correlation, volatility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s report                    Full risk report
  %(prog)s concentration             Concentration analysis
  %(prog)s correlation               Correlation analysis
  %(prog)s volatility                Volatility and VaR
  %(prog)s add AAPL 100 175.50       Add/update position
  %(prog)s remove TSLA               Remove position
  %(prog)s positions                 List positions
  %(prog)s alert risk_score 70       Alert if risk > 70
  %(prog)s check-alerts              Check triggered alerts
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # report command
    report_parser = subparsers.add_parser("report", help="Generate full risk report")
    report_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # concentration command
    conc_parser = subparsers.add_parser("concentration", help="Concentration analysis")
    conc_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # correlation command
    corr_parser = subparsers.add_parser("correlation", help="Correlation analysis")
    corr_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # volatility command
    vol_parser = subparsers.add_parser("volatility", help="Volatility analysis")
    vol_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # positions command
    pos_parser = subparsers.add_parser("positions", help="List positions")
    pos_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # add command
    add_parser = subparsers.add_parser("add", help="Add position")
    add_parser.add_argument("ticker", help="Stock ticker")
    add_parser.add_argument("shares", type=int, help="Number of shares")
    add_parser.add_argument("cost_basis", type=float, help="Cost basis per share")
    
    # remove command
    remove_parser = subparsers.add_parser("remove", help="Remove position")
    remove_parser.add_argument("ticker", help="Stock ticker")
    
    # alert command
    alert_parser = subparsers.add_parser("alert", help="Set risk alert")
    alert_parser.add_argument("metric", choices=["risk_score", "hhi", "correlation", "volatility", "beta", "var_daily"])
    alert_parser.add_argument("threshold", type=float, help="Alert threshold")
    alert_parser.add_argument("-d", "--direction", choices=["above", "below"], default="above")
    
    # check-alerts command
    subparsers.add_parser("check-alerts", help="Check triggered alerts")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    portfolio = load_portfolio()
    
    if args.command == "report":
        report = generate_risk_report(portfolio)
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            s = report["summary"]
            risk_emoji = "🔴" if s["risk_level"] == "High" else "🟡" if s["risk_level"] == "Moderate" else "🟢"
            
            print(f"\n{risk_emoji} PORTFOLIO RISK REPORT")
            print(f"   {report['portfolio_name']} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print()
            print(f"📊 Summary")
            print(f"   Total Value: ${s['total_value']:,.2f}")
            print(f"   Positions: {s['position_count']}")
            print(f"   Risk Score: {s['risk_score']:.0f}/100 ({s['risk_level']})")
            print()
            
            c = report["concentration"]
            print(f"📦 Concentration")
            print(f"   HHI: {c['hhi']:.0f} ({c['hhi_interpretation']})")
            print(f"   Top 5: {c['top_5_concentration']:.1f}% of portfolio")
            
            print("\n   Top Positions:")
            for pos in c["positions"][:5]:
                flag = "⚠️" if pos["overweight"] else "  "
                print(f"   {flag} {pos['ticker']}: {pos['weight']:.1f}% (${pos['value']:,.0f})")
            
            print("\n   Sector Breakdown:")
            for sec in c["sectors"][:5]:
                flag = "⚠️" if sec["overweight"] else "  "
                print(f"   {flag} {sec['sector']}: {sec['weight']:.1f}%")
            
            cr = report["correlation"]
            print(f"\n🔗 Correlation")
            print(f"   Average: {cr['average_correlation']:.2f} ({cr['correlation_risk']} risk)")
            print(f"   High-Correlation Pairs: {len(cr['high_correlation_pairs'])}")
            
            v = report["volatility"]
            print(f"\n📈 Volatility")
            print(f"   Annual: {v['portfolio_volatility_annual']:.1f}% ({v['volatility_level']})")
            print(f"   Daily: {v['portfolio_volatility_daily']:.2f}%")
            print(f"   Beta: {v['portfolio_beta']:.2f} ({v['beta_risk']})")
            print(f"   VaR (95%, Daily): ${v['var_95_daily']:,.0f}")
            print(f"   VaR (95%, Monthly): ${v['var_95_monthly']:,.0f}")
            
            if report["warnings"]:
                print(f"\n⚠️ WARNINGS ({len(report['warnings'])})")
                for w in report["warnings"][:5]:
                    print(f"   • {w}")
            
            print(f"\n💡 RECOMMENDATIONS")
            for rec in report["recommendations"][:5]:
                severity_emoji = "🔴" if rec["severity"] == "High" else "🟡" if rec["severity"] == "Medium" else "ℹ️"
                print(f"   {severity_emoji} [{rec['area']}] {rec['recommendation']}")
    
    elif args.command == "concentration":
        positions = calculate_position_values(portfolio)
        result = analyze_concentration(positions)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n📦 CONCENTRATION ANALYSIS")
            print(f"   Total Value: ${result['total_value']:,.2f}")
            print(f"   HHI: {result['hhi']:.0f} ({result['hhi_interpretation']})")
            print(f"   Top 5: {result['top_5_concentration']:.1f}%")
            print("\n   Positions by Weight:")
            for pos in result["positions"]:
                flag = "⚠️" if pos["overweight"] else "  "
                print(f"   {flag} {pos['ticker']:6} {pos['weight']:5.1f}%  ${pos['value']:>10,.0f}")
    
    elif args.command == "correlation":
        positions = calculate_position_values(portfolio)
        result = analyze_correlation(positions)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n🔗 CORRELATION ANALYSIS")
            print(f"   Average Correlation: {result['average_correlation']:.2f}")
            print(f"   Risk Level: {result['correlation_risk']}")
            print("\n   Highest Correlations:")
            for c in result["top_correlations"][:10]:
                flag = "⚠️" if c["correlation"] >= 0.7 else "  "
                print(f"   {flag} {c['pair']:15} {c['correlation']:.2f}")
            print("\n   Lowest Correlations (diversifiers):")
            for c in result["lowest_correlations"]:
                print(f"      {c['pair']:15} {c['correlation']:.2f}")
    
    elif args.command == "volatility":
        positions = calculate_position_values(portfolio)
        result = analyze_volatility(positions)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n📈 VOLATILITY ANALYSIS")
            print(f"   Portfolio Vol (Annual): {result['portfolio_volatility_annual']:.1f}%")
            print(f"   Portfolio Vol (Daily): {result['portfolio_volatility_daily']:.2f}%")
            print(f"   Level: {result['volatility_level']}")
            print(f"\n   Portfolio Beta: {result['portfolio_beta']:.2f} ({result['beta_risk']})")
            print(f"   VaR 95% (Daily): ${result['var_95_daily']:,.0f}")
            print(f"   VaR 95% (Monthly): ${result['var_95_monthly']:,.0f}")
            print("\n   Position Volatilities:")
            for v in result["position_volatilities"][:10]:
                print(f"      {v['ticker']:6} {v['volatility']:5.1f}% vol  {v['weight']:5.1f}% weight")
    
    elif args.command == "positions":
        positions = calculate_position_values(portfolio)
        
        if args.json:
            print(json.dumps(positions, indent=2))
        else:
            print(f"\n📋 PORTFOLIO POSITIONS\n")
            print("Ticker │ Shares │  Cost  │ Current │   Value   │  P&L  │ P&L %")
            print("───────┼────────┼────────┼─────────┼───────────┼───────┼──────")
            total_value = 0
            total_pl = 0
            for p in positions:
                pl_emoji = "📈" if p["gain_loss"] >= 0 else "📉"
                print(f"{p['ticker']:6} │ {p['shares']:6} │ ${p['cost_basis']:6.0f} │ ${p['current_price']:7.0f} │ ${p['market_value']:>9,.0f} │ {pl_emoji} {p['gain_loss']:+.0f} │ {p['gain_loss_pct']:+.1f}%")
                total_value += p["market_value"]
                total_pl += p["gain_loss"]
            print("───────┴────────┴────────┴─────────┴───────────┴───────┴──────")
            print(f"TOTAL                              ${total_value:>9,.0f}    {total_pl:+,.0f}")
    
    elif args.command == "add":
        result = add_position(args.ticker, args.shares, args.cost_basis)
        pos = result["position"]
        print(f"✅ Position {result['status']}: {pos['ticker']} - {pos['shares']} shares @ ${pos['cost_basis']:.2f}")
    
    elif args.command == "remove":
        result = remove_position(args.ticker)
        if result["status"] == "removed":
            print(f"✅ Removed {result['position']['ticker']} ({result['position']['shares']} shares)")
        else:
            print(f"❌ Position {args.ticker} not found")
    
    elif args.command == "alert":
        result = set_alert(args.metric, args.threshold, args.direction)
        print(f"✅ Alert set: {result['metric']} {result['direction']} {result['threshold']}")
        print(f"   Alert ID: {result['id']}")
    
    elif args.command == "check-alerts":
        triggered = check_alerts()
        if triggered:
            print("🚨 TRIGGERED ALERTS:")
            for alert in triggered:
                print(f"   {alert['metric']}: {alert['triggered_value']:.2f} (threshold: {alert['threshold']})")
        else:
            print("✅ No alerts triggered")


if __name__ == "__main__":
    main()
