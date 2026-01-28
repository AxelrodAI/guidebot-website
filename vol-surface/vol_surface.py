#!/usr/bin/env python3
"""
Volatility Surface Monitor
Track implied volatility across strikes and expirations.
Monitor put/call skew, term structure, IV percentiles.

Author: PM3
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import pandas as pd
import numpy as np

# Configuration
DATA_DIR = Path(__file__).parent
VOL_CACHE = DATA_DIR / "vol_data.json"
HISTORY_FILE = DATA_DIR / "vol_history.json"

# Default watchlist for vol monitoring
DEFAULT_WATCHLIST = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "META", "GOOGL", "AMZN"]


def load_cache():
    """Load cached vol data."""
    if VOL_CACHE.exists():
        with open(VOL_CACHE) as f:
            return json.load(f)
    return {"tickers": {}, "last_updated": None}


def save_cache(data):
    """Save vol data to cache."""
    data["last_updated"] = datetime.now().isoformat()
    with open(VOL_CACHE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_option_chain(ticker):
    """
    Fetch options chain for a ticker.
    Returns IV data for calls and puts across expirations.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Get current price
        info = stock.info
        current_price = info.get("regularMarketPrice") or info.get("previousClose")
        
        if not current_price:
            return {"ticker": ticker, "error": "Could not get current price"}
        
        # Get available expirations
        expirations = stock.options
        
        if not expirations:
            return {"ticker": ticker, "error": "No options available"}
        
        # Collect IV data for each expiration
        expirations_data = []
        
        for exp in expirations[:8]:  # Limit to 8 nearest expirations
            try:
                opt = stock.option_chain(exp)
                
                # Get ATM strikes (closest to current price)
                calls = opt.calls
                puts = opt.puts
                
                if calls.empty or puts.empty:
                    continue
                
                # Find ATM strike
                atm_strike = min(calls['strike'].tolist(), key=lambda x: abs(x - current_price))
                
                # Get ATM call and put IV
                atm_call = calls[calls['strike'] == atm_strike].iloc[0] if not calls[calls['strike'] == atm_strike].empty else None
                atm_put = puts[puts['strike'] == atm_strike].iloc[0] if not puts[puts['strike'] == atm_strike].empty else None
                
                atm_call_iv = float(atm_call['impliedVolatility']) * 100 if atm_call is not None else None
                atm_put_iv = float(atm_put['impliedVolatility']) * 100 if atm_put is not None else None
                
                # Calculate put/call skew (25 delta approximation)
                otm_put_strike = current_price * 0.95
                otm_call_strike = current_price * 1.05
                
                otm_put = puts[puts['strike'] <= otm_put_strike].iloc[-1] if not puts[puts['strike'] <= otm_put_strike].empty else None
                otm_call = calls[calls['strike'] >= otm_call_strike].iloc[0] if not calls[calls['strike'] >= otm_call_strike].empty else None
                
                otm_put_iv = float(otm_put['impliedVolatility']) * 100 if otm_put is not None else None
                otm_call_iv = float(otm_call['impliedVolatility']) * 100 if otm_call is not None else None
                
                # Calculate skew (put IV - call IV)
                skew = (otm_put_iv - otm_call_iv) if otm_put_iv and otm_call_iv else None
                
                # Days to expiration
                exp_date = datetime.strptime(exp, "%Y-%m-%d")
                dte = (exp_date - datetime.now()).days
                
                expirations_data.append({
                    "expiration": exp,
                    "dte": dte,
                    "atm_strike": atm_strike,
                    "atm_call_iv": round(atm_call_iv, 2) if atm_call_iv else None,
                    "atm_put_iv": round(atm_put_iv, 2) if atm_put_iv else None,
                    "atm_avg_iv": round((atm_call_iv + atm_put_iv) / 2, 2) if atm_call_iv and atm_put_iv else None,
                    "otm_put_iv": round(otm_put_iv, 2) if otm_put_iv else None,
                    "otm_call_iv": round(otm_call_iv, 2) if otm_call_iv else None,
                    "skew": round(skew, 2) if skew else None,
                    "call_volume": int(calls['volume'].sum()) if 'volume' in calls.columns else 0,
                    "put_volume": int(puts['volume'].sum()) if 'volume' in puts.columns else 0,
                    "call_oi": int(calls['openInterest'].sum()) if 'openInterest' in calls.columns else 0,
                    "put_oi": int(puts['openInterest'].sum()) if 'openInterest' in puts.columns else 0,
                })
            except Exception as e:
                continue
        
        if not expirations_data:
            return {"ticker": ticker, "error": "Could not process options data"}
        
        # Calculate term structure metrics
        ivs = [e["atm_avg_iv"] for e in expirations_data if e["atm_avg_iv"]]
        
        term_structure = "UNKNOWN"
        if len(ivs) >= 2:
            if ivs[0] > ivs[-1]:
                term_structure = "INVERTED"  # Near-term IV higher (often before events)
            elif ivs[0] < ivs[-1]:
                term_structure = "CONTANGO"  # Normal - longer term IV higher
            else:
                term_structure = "FLAT"
        
        # Calculate IV percentile (would need historical data in production)
        current_iv = ivs[0] if ivs else None
        
        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "current_iv": round(current_iv, 2) if current_iv else None,
            "term_structure": term_structure,
            "expirations": expirations_data,
            "total_call_volume": sum(e.get("call_volume", 0) for e in expirations_data),
            "total_put_volume": sum(e.get("put_volume", 0) for e in expirations_data),
            "put_call_ratio": round(sum(e.get("put_volume", 0) for e in expirations_data) / 
                                   max(1, sum(e.get("call_volume", 0) for e in expirations_data)), 2),
            "fetch_time": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def analyze_vol_surface(ticker):
    """
    Perform comprehensive vol surface analysis.
    """
    data = get_option_chain(ticker)
    
    if "error" in data:
        return data
    
    alerts = []
    analysis = {
        "ticker": ticker,
        "current_price": data["current_price"],
        "current_iv": data["current_iv"],
        "term_structure": data["term_structure"],
        "put_call_ratio": data["put_call_ratio"],
        "expirations": data["expirations"],
        "alerts": []
    }
    
    # Check for inverted term structure (often precedes moves)
    if data["term_structure"] == "INVERTED":
        alerts.append({
            "type": "INVERTED_TERM_STRUCTURE",
            "message": "Near-term IV higher than far-term - possible event or move expected",
            "severity": "HIGH"
        })
    
    # Check for extreme skew
    for exp in data["expirations"][:3]:  # Check near-term expirations
        if exp["skew"] and exp["skew"] > 10:
            alerts.append({
                "type": "HIGH_PUT_SKEW",
                "message": f"High put skew ({exp['skew']:.1f}) for {exp['expiration']} - hedging demand elevated",
                "severity": "MEDIUM"
            })
        elif exp["skew"] and exp["skew"] < -5:
            alerts.append({
                "type": "CALL_SKEW",
                "message": f"Unusual call skew ({exp['skew']:.1f}) for {exp['expiration']} - bullish speculation",
                "severity": "MEDIUM"
            })
    
    # Check put/call ratio
    if data["put_call_ratio"] > 1.5:
        alerts.append({
            "type": "HIGH_PUT_CALL_RATIO",
            "message": f"Elevated put/call ratio ({data['put_call_ratio']:.2f}) - bearish sentiment or hedging",
            "severity": "MEDIUM"
        })
    elif data["put_call_ratio"] < 0.5:
        alerts.append({
            "type": "LOW_PUT_CALL_RATIO",
            "message": f"Low put/call ratio ({data['put_call_ratio']:.2f}) - bullish sentiment",
            "severity": "LOW"
        })
    
    # Check IV levels (rough percentiles)
    if data["current_iv"]:
        if data["current_iv"] > 50:
            alerts.append({
                "type": "HIGH_IV",
                "message": f"Elevated IV ({data['current_iv']:.1f}%) - premium selling may be attractive",
                "severity": "HIGH" if data["current_iv"] > 70 else "MEDIUM"
            })
        elif data["current_iv"] < 15:
            alerts.append({
                "type": "LOW_IV",
                "message": f"Low IV ({data['current_iv']:.1f}%) - options are cheap, breakout possible",
                "severity": "LOW"
            })
    
    analysis["alerts"] = alerts
    analysis["alert_count"] = len(alerts)
    analysis["analysis_time"] = datetime.now().isoformat()
    
    return analysis


def scan_watchlist(tickers=None):
    """Scan entire watchlist for vol opportunities."""
    tickers = tickers or DEFAULT_WATCHLIST
    
    results = []
    for ticker in tickers:
        print(f"Scanning {ticker}...")
        analysis = analyze_vol_surface(ticker)
        results.append(analysis)
    
    # Sort by alert count
    results.sort(key=lambda x: x.get("alert_count", 0), reverse=True)
    
    return results


def generate_vol_report(results):
    """Generate formatted vol surface report."""
    lines = [
        "=" * 70,
        "VOLATILITY SURFACE MONITOR REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        ""
    ]
    
    # Summary
    valid_results = [r for r in results if "error" not in r]
    alert_count = sum(r.get("alert_count", 0) for r in valid_results)
    
    lines.extend([
        f"Tickers Scanned: {len(results)}",
        f"Total Alerts: {alert_count}",
        "",
        "-" * 70,
        "VOL SURFACE SUMMARY",
        "-" * 70,
        f"{'Ticker':<8} {'Price':<10} {'IV%':<8} {'Term':<12} {'P/C Ratio':<10} {'Alerts':<6}",
        "-" * 70
    ])
    
    for r in valid_results:
        ticker = r["ticker"]
        price = f"${r['current_price']:.2f}" if r.get("current_price") else "N/A"
        iv = f"{r['current_iv']:.1f}%" if r.get("current_iv") else "N/A"
        term = r.get("term_structure", "N/A")
        pcr = f"{r['put_call_ratio']:.2f}" if r.get("put_call_ratio") else "N/A"
        alerts = str(r.get("alert_count", 0))
        
        lines.append(f"{ticker:<8} {price:<10} {iv:<8} {term:<12} {pcr:<10} {alerts:<6}")
    
    # Alerts section
    all_alerts = []
    for r in valid_results:
        for alert in r.get("alerts", []):
            all_alerts.append((r["ticker"], alert))
    
    if all_alerts:
        lines.extend([
            "",
            "-" * 70,
            "ALERTS",
            "-" * 70
        ])
        
        for ticker, alert in all_alerts:
            severity = {"HIGH": "[!!!]", "MEDIUM": "[!!]", "LOW": "[!]"}.get(alert["severity"], "")
            lines.append(f"{severity} [{ticker}] {alert['message']}")
    
    # Term structure breakdown
    inverted = [r["ticker"] for r in valid_results if r.get("term_structure") == "INVERTED"]
    if inverted:
        lines.extend([
            "",
            ">>> INVERTED TERM STRUCTURE (watch for near-term moves):",
            f"    {', '.join(inverted)}"
        ])
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def get_vol_smile(ticker, expiration=None):
    """
    Get volatility smile for a specific expiration.
    Shows IV across strikes.
    """
    try:
        stock = yf.Ticker(ticker)
        
        info = stock.info
        current_price = info.get("regularMarketPrice") or info.get("previousClose")
        
        expirations = stock.options
        if not expirations:
            return {"error": "No options available"}
        
        # Use specified expiration or first available
        exp = expiration if expiration in expirations else expirations[0]
        
        opt = stock.option_chain(exp)
        calls = opt.calls
        puts = opt.puts
        
        # Merge calls and puts
        smile_data = []
        
        for _, row in calls.iterrows():
            strike = row['strike']
            call_iv = row['impliedVolatility'] * 100 if pd.notna(row['impliedVolatility']) else None
            
            # Find matching put
            put_row = puts[puts['strike'] == strike]
            put_iv = put_row.iloc[0]['impliedVolatility'] * 100 if not put_row.empty and pd.notna(put_row.iloc[0]['impliedVolatility']) else None
            
            moneyness = (strike / current_price - 1) * 100  # % OTM/ITM
            
            smile_data.append({
                "strike": strike,
                "moneyness": round(moneyness, 1),
                "call_iv": round(call_iv, 2) if call_iv else None,
                "put_iv": round(put_iv, 2) if put_iv else None,
                "avg_iv": round((call_iv + put_iv) / 2, 2) if call_iv and put_iv else None
            })
        
        return {
            "ticker": ticker,
            "expiration": exp,
            "current_price": round(current_price, 2),
            "smile": sorted(smile_data, key=lambda x: x["strike"])
        }
    
    except Exception as e:
        return {"error": str(e)}


def export_to_json(results, output_file=None):
    """Export analysis to JSON."""
    output_file = output_file or (DATA_DIR / "vol_analysis.json")
    
    with open(output_file, "w") as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "results": results
        }, f, indent=2, default=str)
    
    return str(output_file)


if __name__ == "__main__":
    import sys
    
    tickers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_WATCHLIST
    
    print("Scanning volatility surfaces...")
    print()
    
    results = scan_watchlist(tickers)
    report = generate_vol_report(results)
    
    print(report)
    
    json_file = export_to_json(results)
    print(f"\nExported to: {json_file}")
