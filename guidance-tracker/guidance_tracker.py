#!/usr/bin/env python3
"""
Guidance vs Actuals Tracker
Tracks management guidance revisions, compares to actual results,
identifies sandbagging patterns, and scores management credibility.

Usage:
    python guidance_tracker.py                    # Update all tickers
    python guidance_tracker.py AAPL MSFT GOOGL   # Update specific tickers
    python guidance_tracker.py --analyze AAPL    # Detailed analysis for one ticker
"""

import sys
# Fix Windows encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import json
import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

# Try importing yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("Warning: yfinance not installed. Run: pip install yfinance")

# Default watchlist
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "BAC", "WFC", "GS", "MS",
    "UNH", "JNJ", "PFE", "MRK", "ABBV",
    "XOM", "CVX", "COP",
    "HD", "WMT", "COST", "TGT",
    "DIS", "NFLX", "CMCSA"
]

# Sector mapping
SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology", "AMZN": "Consumer",
    "META": "Technology", "NVDA": "Technology", "TSLA": "Consumer",
    "JPM": "Financial", "BAC": "Financial", "WFC": "Financial", "GS": "Financial", "MS": "Financial",
    "UNH": "Healthcare", "JNJ": "Healthcare", "PFE": "Healthcare", "MRK": "Healthcare", "ABBV": "Healthcare",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
    "HD": "Consumer", "WMT": "Consumer", "COST": "Consumer", "TGT": "Consumer",
    "DIS": "Consumer", "NFLX": "Technology", "CMCSA": "Consumer"
}


def get_guidance_data(ticker):
    """
    Fetch earnings and guidance data for a ticker.
    Returns quarterly data comparing guidance to actuals.
    """
    if not HAS_YFINANCE:
        return None
    
    try:
        stock = yf.Ticker(ticker)
        
        # Get earnings history
        earnings = stock.earnings_history
        if earnings is None or earnings.empty:
            print(f"  No earnings history for {ticker}")
            return None
        
        # Get company info
        info = stock.info
        company_name = info.get('longName', info.get('shortName', ticker))
        sector = SECTOR_MAP.get(ticker, info.get('sector', 'Other'))
        
        quarters = []
        beat_count = 0
        total_quarters = 0
        
        # Process last 8 quarters of data
        recent_earnings = earnings.tail(8).iloc[::-1]  # Most recent first
        
        for idx, row in recent_earnings.iterrows():
            eps_estimate = row.get('epsEstimate', 0)
            eps_actual = row.get('epsActual', 0)
            
            if eps_estimate and eps_actual:
                quarter_date = idx
                if hasattr(quarter_date, 'strftime'):
                    q_str = f"Q{(quarter_date.month-1)//3 + 1} {quarter_date.year}"
                else:
                    q_str = str(quarter_date)[:7]
                
                quarters.append({
                    "q": q_str,
                    "epsGuide": round(float(eps_estimate), 2),
                    "epsActual": round(float(eps_actual), 2),
                    "revGuide": 0,  # Revenue guidance often not available via yfinance
                    "revActual": 0
                })
                
                if eps_actual > eps_estimate:
                    beat_count += 1
                total_quarters += 1
        
        if total_quarters == 0:
            print(f"  No valid quarters for {ticker}")
            return None
        
        beat_rate = round((beat_count / total_quarters) * 100)
        
        # Calculate credibility score
        # Based on: accuracy of guidance (lower variance = higher credibility)
        variances = []
        for q in quarters:
            if q['epsGuide'] > 0:
                var = abs((q['epsActual'] - q['epsGuide']) / q['epsGuide'])
                variances.append(var)
        
        if variances:
            avg_variance = sum(variances) / len(variances)
            # Credibility: 100 - (avg_variance * 100), capped at 0-100
            credibility = max(0, min(100, round(100 - (avg_variance * 200))))
        else:
            credibility = 50
        
        # Determine pattern
        if beat_rate >= 80:
            pattern = "sandbagger"
        elif beat_rate <= 25:
            pattern = "optimistic"
        elif avg_variance > 0.15:
            pattern = "volatile"
        else:
            pattern = "accurate"
        
        return {
            "ticker": ticker,
            "name": company_name,
            "sector": sector,
            "quarters": quarters[:4],  # Keep last 4 quarters
            "beatRate": beat_rate,
            "credibilityScore": credibility,
            "pattern": pattern
        }
        
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return None


def calculate_credibility_score(company_data):
    """
    Calculate management credibility score (0-100) based on:
    - Consistency of guidance accuracy
    - Magnitude of beats/misses
    - Trend in guidance quality
    """
    quarters = company_data.get('quarters', [])
    if not quarters:
        return 50
    
    variances = []
    directions = []  # 1 = beat, -1 = miss
    
    for q in quarters:
        if q['epsGuide'] > 0:
            variance = (q['epsActual'] - q['epsGuide']) / q['epsGuide']
            variances.append(abs(variance))
            directions.append(1 if variance > 0 else -1)
    
    if not variances:
        return 50
    
    # Base score from average variance (lower = better)
    avg_var = sum(variances) / len(variances)
    base_score = max(0, 100 - (avg_var * 200))
    
    # Penalty for inconsistency
    if len(variances) > 1:
        variance_of_variances = sum((v - avg_var) ** 2 for v in variances) / len(variances)
        consistency_penalty = min(20, variance_of_variances * 1000)
    else:
        consistency_penalty = 0
    
    # Penalty for consistent same-direction (sandbagging/optimism)
    if len(directions) >= 3:
        same_direction = all(d == directions[0] for d in directions)
        if same_direction:
            consistency_penalty += 10
    
    final_score = max(0, min(100, round(base_score - consistency_penalty)))
    return final_score


def identify_pattern(company_data):
    """
    Identify guidance pattern:
    - sandbagger: Consistently beats (sandbagging)
    - accurate: Guidance close to actuals
    - volatile: Large swings in accuracy
    - optimistic: Consistently misses (over-promising)
    """
    beat_rate = company_data.get('beatRate', 50)
    credibility = company_data.get('credibilityScore', 50)
    quarters = company_data.get('quarters', [])
    
    if beat_rate >= 80:
        return "sandbagger"
    elif beat_rate <= 25:
        return "optimistic"
    
    # Check volatility
    if quarters:
        variances = []
        for q in quarters:
            if q['epsGuide'] > 0:
                var = abs((q['epsActual'] - q['epsGuide']) / q['epsGuide'])
                variances.append(var)
        
        if variances and len(variances) > 1:
            avg_var = sum(variances) / len(variances)
            if avg_var > 0.15:
                return "volatile"
    
    return "accurate"


def analyze_ticker(ticker):
    """Perform detailed analysis on a single ticker."""
    print(f"\n{'='*60}")
    print(f"DETAILED ANALYSIS: {ticker}")
    print(f"{'='*60}\n")
    
    data = get_guidance_data(ticker)
    if not data:
        print("Could not fetch data for this ticker.")
        return
    
    print(f"Company: {data['name']}")
    print(f"Sector: {data['sector']}")
    print(f"Beat Rate: {data['beatRate']}%")
    print(f"Credibility Score: {data['credibilityScore']}/100")
    print(f"Pattern: {data['pattern'].upper()}")
    
    print(f"\n{'─'*60}")
    print("QUARTERLY BREAKDOWN:")
    print(f"{'─'*60}")
    print(f"{'Quarter':<12} {'EPS Guide':>12} {'EPS Actual':>12} {'Variance':>12}")
    print(f"{'─'*60}")
    
    for q in data['quarters']:
        if q['epsGuide'] > 0:
            variance = ((q['epsActual'] - q['epsGuide']) / q['epsGuide']) * 100
            var_str = f"{'+' if variance >= 0 else ''}{variance:.1f}%"
        else:
            var_str = "N/A"
        
        print(f"{q['q']:<12} ${q['epsGuide']:>10.2f} ${q['epsActual']:>10.2f} {var_str:>12}")
    
    # Pattern analysis
    print(f"\n{'─'*60}")
    print("PATTERN ANALYSIS:")
    print(f"{'─'*60}")
    
    if data['pattern'] == 'sandbagger':
        print("⚠️  SANDBAGGING DETECTED")
        print("    This company consistently beats guidance.")
        print("    Management may be setting low bars to exceed expectations.")
        print("    Consider: Actual performance likely better than guidance suggests.")
    elif data['pattern'] == 'optimistic':
        print("🔴 OPTIMISTIC BIAS DETECTED")
        print("    This company consistently misses guidance.")
        print("    Management may be over-promising or facing execution issues.")
        print("    Consider: Be cautious with management projections.")
    elif data['pattern'] == 'volatile':
        print("📊 VOLATILE GUIDANCE")
        print("    Guidance accuracy varies significantly quarter to quarter.")
        print("    Business may have high uncertainty or poor visibility.")
        print("    Consider: Wider range of outcomes likely.")
    else:
        print("✅ ACCURATE GUIDANCE")
        print("    Management guidance is generally reliable.")
        print("    Company shows good forecasting ability.")
        print("    Consider: Guidance can be used as a reasonable baseline.")


def update_all_data(tickers=None):
    """Update guidance data for all tickers and save to JSON."""
    if tickers is None:
        tickers = DEFAULT_TICKERS
    
    print(f"Updating guidance data for {len(tickers)} tickers...")
    print(f"{'─'*50}")
    
    companies = []
    for ticker in tickers:
        print(f"Fetching {ticker}...", end=" ")
        data = get_guidance_data(ticker)
        if data:
            # Recalculate scores
            data['credibilityScore'] = calculate_credibility_score(data)
            data['pattern'] = identify_pattern(data)
            companies.append(data)
            print(f"✓ Beat: {data['beatRate']}% | Credibility: {data['credibilityScore']}")
        else:
            print("✗ No data")
    
    # Sort by beat rate descending
    companies.sort(key=lambda x: x['beatRate'], reverse=True)
    
    output = {
        "lastUpdated": datetime.now().isoformat(),
        "companies": companies
    }
    
    # Save to file
    output_path = Path(__file__).parent / "guidance_data.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'─'*50}")
    print(f"✓ Saved {len(companies)} companies to {output_path}")
    
    # Summary stats
    if companies:
        avg_beat = sum(c['beatRate'] for c in companies) / len(companies)
        avg_cred = sum(c['credibilityScore'] for c in companies) / len(companies)
        sandbaggers = len([c for c in companies if c['pattern'] == 'sandbagger'])
        
        print(f"\nSUMMARY:")
        print(f"  Average Beat Rate: {avg_beat:.1f}%")
        print(f"  Average Credibility: {avg_cred:.1f}")
        print(f"  Sandbaggers Identified: {sandbaggers}")
    
    return output


def main():
    parser = argparse.ArgumentParser(description='Guidance vs Actuals Tracker')
    parser.add_argument('tickers', nargs='*', help='Tickers to update (default: watchlist)')
    parser.add_argument('--analyze', '-a', type=str, help='Detailed analysis for one ticker')
    parser.add_argument('--output', '-o', type=str, help='Output JSON file path')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_ticker(args.analyze.upper())
    elif args.tickers:
        update_all_data([t.upper() for t in args.tickers])
    else:
        update_all_data()


if __name__ == "__main__":
    main()
