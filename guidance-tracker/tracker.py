#!/usr/bin/env python3
"""
Guidance vs Actuals Tracker
Track management guidance revisions and compare to actual results.
Identify sandbagging patterns and score management credibility.

Author: PM3
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import pandas as pd
import numpy as np

# Configuration
DATA_DIR = Path(__file__).parent
GUIDANCE_CACHE = DATA_DIR / "guidance_data.json"
HISTORY_FILE = DATA_DIR / "guidance_history.json"

# Companies to track (can be expanded)
DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "JPM", "BAC", "WFC",
    "EWBC", "SCHW", "GS", "MS", "C"
]


def load_cache():
    """Load cached guidance data."""
    if GUIDANCE_CACHE.exists():
        with open(GUIDANCE_CACHE) as f:
            return json.load(f)
    return {"companies": {}, "last_updated": None}


def save_cache(data):
    """Save guidance data to cache."""
    data["last_updated"] = datetime.now().isoformat()
    with open(GUIDANCE_CACHE, "w") as f:
        json.dump(data, f, indent=2)


def load_history():
    """Load historical guidance tracking."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {"records": []}


def save_history(history):
    """Save historical records."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_earnings_data(ticker):
    """Fetch earnings data including estimates and actuals."""
    try:
        stock = yf.Ticker(ticker)
        
        # Get earnings history (actuals vs estimates)
        earnings_hist = stock.earnings_history
        
        # Get upcoming earnings
        calendar = stock.calendar
        
        # Get analyst estimates
        earnings_estimate = stock.earnings_estimate
        revenue_estimate = stock.revenue_estimate
        
        info = stock.info
        
        return {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "earnings_history": earnings_hist.to_dict() if earnings_hist is not None and not earnings_hist.empty else {},
            "calendar": calendar if calendar is not None else {},
            "earnings_estimate": earnings_estimate.to_dict() if earnings_estimate is not None and not earnings_estimate.empty else {},
            "revenue_estimate": revenue_estimate.to_dict() if revenue_estimate is not None and not revenue_estimate.empty else {},
            "forward_eps": info.get("forwardEps"),
            "trailing_eps": info.get("trailingEps"),
            "fetch_time": datetime.now().isoformat()
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def calculate_guidance_accuracy(earnings_history):
    """
    Calculate management guidance accuracy metrics.
    
    Returns:
        dict with beat_rate, avg_surprise, sandbagging_score, credibility_score
    """
    if not earnings_history:
        return None
    
    try:
        # Convert to usable format
        df = pd.DataFrame(earnings_history)
        
        if df.empty or 'epsActual' not in df.columns or 'epsEstimate' not in df.columns:
            return None
        
        # Filter valid rows
        df = df.dropna(subset=['epsActual', 'epsEstimate'])
        
        if len(df) == 0:
            return None
        
        # Calculate surprise percentages
        df['surprise'] = df['epsActual'] - df['epsEstimate']
        df['surprise_pct'] = np.where(
            df['epsEstimate'] != 0,
            (df['surprise'] / abs(df['epsEstimate'])) * 100,
            0
        )
        
        # Calculate metrics
        beats = (df['epsActual'] > df['epsEstimate']).sum()
        misses = (df['epsActual'] < df['epsEstimate']).sum()
        meets = (df['epsActual'] == df['epsEstimate']).sum()
        total = len(df)
        
        beat_rate = (beats / total * 100) if total > 0 else 0
        avg_surprise = df['surprise_pct'].mean()
        
        # Sandbagging detection: consistently beating by small amounts
        # True sandbagging = beats often but by small margins (lowball guidance)
        small_beats = ((df['surprise_pct'] > 0) & (df['surprise_pct'] < 10)).sum()
        sandbagging_score = (small_beats / total * 100) if total > 0 else 0
        
        # Credibility score (0-100)
        # High credibility = accurate guidance (close to actuals)
        # Penalize both big misses AND big beats (sandbagging)
        accuracy_penalty = abs(df['surprise_pct']).mean()
        credibility_score = max(0, 100 - accuracy_penalty * 2)
        
        # Consistency score (standard deviation of surprises)
        consistency = 100 - min(100, df['surprise_pct'].std() * 5)
        
        return {
            "total_quarters": total,
            "beats": int(beats),
            "misses": int(misses),
            "meets": int(meets),
            "beat_rate": round(beat_rate, 1),
            "avg_surprise_pct": round(avg_surprise, 2),
            "sandbagging_score": round(sandbagging_score, 1),
            "credibility_score": round(credibility_score, 1),
            "consistency_score": round(consistency, 1),
            "last_4q_surprises": df['surprise_pct'].tail(4).tolist() if len(df) >= 4 else df['surprise_pct'].tolist()
        }
    except Exception as e:
        return {"error": str(e)}


def analyze_guidance_patterns(ticker):
    """
    Perform detailed guidance pattern analysis for a ticker.
    Identifies sandbagging, volatility, and trend patterns.
    """
    data = get_earnings_data(ticker)
    
    if "error" in data:
        return data
    
    accuracy = calculate_guidance_accuracy(data.get("earnings_history", {}))
    
    # Determine pattern type
    pattern = "Unknown"
    alerts = []
    
    if accuracy:
        if accuracy.get("beat_rate", 0) > 80:
            pattern = "Consistent Beater"
            if accuracy.get("sandbagging_score", 0) > 50:
                pattern = "Likely Sandbagging"
                alerts.append("⚠️ High sandbagging probability - management may be lowballing guidance")
        elif accuracy.get("beat_rate", 0) < 40:
            pattern = "Frequent Misser"
            alerts.append("🚨 Company frequently misses guidance - management credibility concern")
        elif accuracy.get("credibility_score", 0) > 80:
            pattern = "Highly Credible"
        else:
            pattern = "Mixed Track Record"
        
        # Additional alerts
        if accuracy.get("consistency_score", 100) < 50:
            alerts.append("⚠️ Inconsistent results - high variance between quarters")
        
        avg_surprise = accuracy.get("avg_surprise_pct", 0)
        if avg_surprise > 15:
            alerts.append("📈 Large average beat - potential alpha in post-earnings drift")
        elif avg_surprise < -5:
            alerts.append("📉 Tends to miss - be cautious going into earnings")
    
    return {
        "ticker": ticker,
        "company_name": data.get("company_name", ticker),
        "sector": data.get("sector", "Unknown"),
        "pattern": pattern,
        "accuracy_metrics": accuracy,
        "alerts": alerts,
        "forward_eps": data.get("forward_eps"),
        "trailing_eps": data.get("trailing_eps"),
        "analysis_time": datetime.now().isoformat()
    }


def track_watchlist(tickers=None):
    """Track guidance accuracy for entire watchlist."""
    tickers = tickers or DEFAULT_WATCHLIST
    
    results = []
    for ticker in tickers:
        print(f"Analyzing {ticker}...")
        analysis = analyze_guidance_patterns(ticker)
        results.append(analysis)
    
    # Sort by credibility score
    results.sort(
        key=lambda x: x.get("accuracy_metrics", {}).get("credibility_score", 0) if x.get("accuracy_metrics") else 0,
        reverse=True
    )
    
    return results


def generate_report(results, output_file=None):
    """Generate a formatted report of guidance analysis."""
    output_file = output_file or (DATA_DIR / "guidance_report.txt")
    
    lines = [
        "=" * 70,
        "GUIDANCE VS ACTUALS TRACKER REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        ""
    ]
    
    # Summary stats
    valid_results = [r for r in results if r.get("accuracy_metrics") and "error" not in r.get("accuracy_metrics", {})]
    
    if valid_results:
        avg_beat_rate = np.mean([r["accuracy_metrics"]["beat_rate"] for r in valid_results])
        avg_credibility = np.mean([r["accuracy_metrics"]["credibility_score"] for r in valid_results])
        
        lines.extend([
            "PORTFOLIO SUMMARY",
            "-" * 40,
            f"Companies Analyzed: {len(valid_results)}",
            f"Avg Beat Rate: {avg_beat_rate:.1f}%",
            f"Avg Credibility Score: {avg_credibility:.1f}/100",
            ""
        ])
    
    # Detailed results
    lines.extend([
        "INDIVIDUAL COMPANY ANALYSIS",
        "-" * 40,
        ""
    ])
    
    for r in results:
        lines.append(f"📊 {r['ticker']} - {r.get('company_name', 'N/A')}")
        lines.append(f"   Sector: {r.get('sector', 'Unknown')}")
        lines.append(f"   Pattern: {r.get('pattern', 'Unknown')}")
        
        if r.get("accuracy_metrics") and "error" not in r.get("accuracy_metrics", {}):
            m = r["accuracy_metrics"]
            lines.append(f"   Beat Rate: {m['beat_rate']}% ({m['beats']}/{m['total_quarters']})")
            lines.append(f"   Avg Surprise: {m['avg_surprise_pct']:+.2f}%")
            lines.append(f"   Credibility Score: {m['credibility_score']}/100")
            lines.append(f"   Sandbagging Score: {m['sandbagging_score']}/100")
        
        if r.get("alerts"):
            for alert in r["alerts"]:
                lines.append(f"   {alert}")
        
        lines.append("")
    
    # Alerts section
    all_alerts = [(r["ticker"], alert) for r in results for alert in r.get("alerts", [])]
    if all_alerts:
        lines.extend([
            "⚠️ ALERTS SUMMARY",
            "-" * 40
        ])
        for ticker, alert in all_alerts:
            lines.append(f"   [{ticker}] {alert}")
        lines.append("")
    
    report = "\n".join(lines)
    
    with open(output_file, "w") as f:
        f.write(report)
    
    return report


def export_to_json(results, output_file=None):
    """Export results to JSON."""
    output_file = output_file or (DATA_DIR / "guidance_analysis.json")
    
    with open(output_file, "w") as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "companies": results
        }, f, indent=2, default=str)
    
    return str(output_file)


def export_to_excel(results, output_file=None):
    """Export results to Excel."""
    output_file = output_file or (DATA_DIR / "guidance_analysis.xlsx")
    
    # Flatten data for Excel
    rows = []
    for r in results:
        row = {
            "Ticker": r["ticker"],
            "Company": r.get("company_name", ""),
            "Sector": r.get("sector", ""),
            "Pattern": r.get("pattern", ""),
            "Forward EPS": r.get("forward_eps"),
            "Trailing EPS": r.get("trailing_eps")
        }
        
        if r.get("accuracy_metrics") and "error" not in r.get("accuracy_metrics", {}):
            m = r["accuracy_metrics"]
            row.update({
                "Total Quarters": m.get("total_quarters"),
                "Beats": m.get("beats"),
                "Misses": m.get("misses"),
                "Beat Rate %": m.get("beat_rate"),
                "Avg Surprise %": m.get("avg_surprise_pct"),
                "Credibility Score": m.get("credibility_score"),
                "Sandbagging Score": m.get("sandbagging_score"),
                "Consistency Score": m.get("consistency_score")
            })
        
        row["Alerts"] = " | ".join(r.get("alerts", []))
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_excel(output_file, index=False, sheet_name="Guidance Analysis")
    
    return str(output_file)


if __name__ == "__main__":
    import sys
    
    # Get tickers from command line or use defaults
    tickers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_WATCHLIST
    
    print("=" * 50)
    print("GUIDANCE VS ACTUALS TRACKER")
    print("=" * 50)
    print()
    
    # Run analysis
    results = track_watchlist(tickers)
    
    # Generate outputs
    report = generate_report(results)
    print(report)
    
    json_file = export_to_json(results)
    print(f"\n📄 JSON exported to: {json_file}")
    
    try:
        excel_file = export_to_excel(results)
        print(f"📊 Excel exported to: {excel_file}")
    except Exception as e:
        print(f"⚠️ Excel export failed (openpyxl required): {e}")
    
    print("\n✅ Analysis complete!")
