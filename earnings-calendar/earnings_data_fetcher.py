#!/usr/bin/env python3
"""
Earnings Calendar Data Fetcher
Fetches earnings dates and historical data from Yahoo Finance using yfinance.
Outputs to earnings_calendar.json for the dashboard.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system("pip install yfinance")
    import yfinance as yf

# Configuration
OUTPUT_FILE = Path(__file__).parent / "earnings_calendar.json"
CACHE_HOURS = 6  # Refresh data every 6 hours

# Default watchlist - major companies by sector
TICKERS = {
    # Technology
    "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
    "MSFT": {"name": "Microsoft Corp", "sector": "Technology"},
    "NVDA": {"name": "NVIDIA Corp", "sector": "Technology"},
    "AVGO": {"name": "Broadcom Inc.", "sector": "Technology"},
    "ORCL": {"name": "Oracle Corp", "sector": "Technology"},
    "CRM": {"name": "Salesforce Inc.", "sector": "Technology"},
    "AMD": {"name": "AMD", "sector": "Technology"},
    "INTC": {"name": "Intel Corp", "sector": "Technology"},
    "CSCO": {"name": "Cisco Systems", "sector": "Technology"},
    "IBM": {"name": "IBM", "sector": "Technology"},
    
    # Financials
    "JPM": {"name": "JPMorgan Chase", "sector": "Financials"},
    "BAC": {"name": "Bank of America", "sector": "Financials"},
    "GS": {"name": "Goldman Sachs", "sector": "Financials"},
    "MS": {"name": "Morgan Stanley", "sector": "Financials"},
    "WFC": {"name": "Wells Fargo", "sector": "Financials"},
    "C": {"name": "Citigroup", "sector": "Financials"},
    "BLK": {"name": "BlackRock", "sector": "Financials"},
    "SCHW": {"name": "Charles Schwab", "sector": "Financials"},
    
    # Healthcare
    "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare"},
    "UNH": {"name": "UnitedHealth", "sector": "Healthcare"},
    "PFE": {"name": "Pfizer Inc.", "sector": "Healthcare"},
    "ABBV": {"name": "AbbVie Inc.", "sector": "Healthcare"},
    "MRK": {"name": "Merck & Co.", "sector": "Healthcare"},
    "LLY": {"name": "Eli Lilly", "sector": "Healthcare"},
    
    # Consumer
    "AMZN": {"name": "Amazon.com", "sector": "Consumer"},
    "WMT": {"name": "Walmart Inc.", "sector": "Consumer"},
    "HD": {"name": "Home Depot", "sector": "Consumer"},
    "COST": {"name": "Costco", "sector": "Consumer"},
    "TGT": {"name": "Target Corp", "sector": "Consumer"},
    "NKE": {"name": "Nike Inc.", "sector": "Consumer"},
    "MCD": {"name": "McDonald's", "sector": "Consumer"},
    "SBUX": {"name": "Starbucks", "sector": "Consumer"},
    
    # Communication
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Communication"},
    "META": {"name": "Meta Platforms", "sector": "Communication"},
    "DIS": {"name": "Walt Disney", "sector": "Communication"},
    "NFLX": {"name": "Netflix Inc.", "sector": "Communication"},
    "CMCSA": {"name": "Comcast Corp", "sector": "Communication"},
    "VZ": {"name": "Verizon", "sector": "Communication"},
    "T": {"name": "AT&T", "sector": "Communication"},
    
    # Industrials
    "CAT": {"name": "Caterpillar", "sector": "Industrials"},
    "BA": {"name": "Boeing Co", "sector": "Industrials"},
    "HON": {"name": "Honeywell", "sector": "Industrials"},
    "UPS": {"name": "UPS", "sector": "Industrials"},
    "RTX": {"name": "RTX Corp", "sector": "Industrials"},
    "DE": {"name": "Deere & Co", "sector": "Industrials"},
    
    # Energy
    "XOM": {"name": "Exxon Mobil", "sector": "Energy"},
    "CVX": {"name": "Chevron Corp", "sector": "Energy"},
    "COP": {"name": "ConocoPhillips", "sector": "Energy"},
    "SLB": {"name": "Schlumberger", "sector": "Energy"},
    
    # Materials
    "LIN": {"name": "Linde plc", "sector": "Materials"},
    "APD": {"name": "Air Products", "sector": "Materials"},
    "FCX": {"name": "Freeport-McMoRan", "sector": "Materials"},
    
    # Utilities
    "NEE": {"name": "NextEra Energy", "sector": "Utilities"},
    "DUK": {"name": "Duke Energy", "sector": "Utilities"},
    "SO": {"name": "Southern Co", "sector": "Utilities"},
    
    # Real Estate
    "AMT": {"name": "American Tower", "sector": "Real Estate"},
    "PLD": {"name": "Prologis", "sector": "Real Estate"},
    "EQIX": {"name": "Equinix", "sector": "Real Estate"},
}


def should_refresh():
    """Check if we need to refresh the data."""
    if not OUTPUT_FILE.exists():
        return True
    
    modified = datetime.fromtimestamp(OUTPUT_FILE.stat().st_mtime)
    return datetime.now() - modified > timedelta(hours=CACHE_HOURS)


def calculate_beat_rate(earnings_history):
    """Calculate historical beat rate from earnings history."""
    if not earnings_history or len(earnings_history) == 0:
        return 70  # Default beat rate
    
    beats = 0
    total = 0
    
    for record in earnings_history:
        if 'epsActual' in record and 'epsEstimate' in record:
            if record['epsEstimate'] is not None and record['epsActual'] is not None:
                total += 1
                if record['epsActual'] > record['epsEstimate']:
                    beats += 1
    
    if total == 0:
        return 70  # Default
    
    return round((beats / total) * 100)


def get_earnings_data(ticker, info):
    """Fetch earnings data for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar
        earnings_dates = stock.earnings_dates
        
        # Get next earnings date
        earnings_date = None
        time = "TBD"
        
        if calendar is not None and not calendar.empty:
            if 'Earnings Date' in calendar.index:
                ed = calendar.loc['Earnings Date']
                if hasattr(ed, 'iloc'):
                    earnings_date = ed.iloc[0] if len(ed) > 0 else None
                else:
                    earnings_date = ed
        
        # Try to get from earnings_dates DataFrame
        if earnings_date is None and earnings_dates is not None and not earnings_dates.empty:
            future_dates = earnings_dates.index[earnings_dates.index >= datetime.now()]
            if len(future_dates) > 0:
                earnings_date = future_dates[0]
        
        if earnings_date is None:
            return None
        
        # Convert to string date
        if hasattr(earnings_date, 'strftime'):
            date_str = earnings_date.strftime('%Y-%m-%d')
            # Determine BMO/AMC based on hour (if available)
            if hasattr(earnings_date, 'hour'):
                time = "BMO" if earnings_date.hour < 12 else "AMC"
            else:
                time = "AMC" if ticker[0] in "AEIOU" else "BMO"  # Arbitrary fallback
        else:
            date_str = str(earnings_date).split()[0]
            time = "AMC"
        
        # Get expected EPS from calendar
        expected_eps = None
        if calendar is not None and not calendar.empty:
            if 'Earnings Average' in calendar.index:
                expected_eps = calendar.loc['Earnings Average']
                if hasattr(expected_eps, 'iloc'):
                    expected_eps = expected_eps.iloc[0] if len(expected_eps) > 0 else None
        
        if expected_eps is None:
            expected_eps = 1.50  # Default
        
        # Build history from earnings_dates
        history = []
        if earnings_dates is not None and not earnings_dates.empty:
            past_dates = earnings_dates.index[earnings_dates.index < datetime.now()]
            for ed in past_dates[:8]:  # Last 8 quarters
                try:
                    row = earnings_dates.loc[ed]
                    estimate = row.get('EPS Estimate', None)
                    actual = row.get('Reported EPS', None)
                    
                    if estimate is not None and actual is not None:
                        result = "BEAT" if actual > estimate else ("INLINE" if abs(actual - estimate) < 0.01 else "MISS")
                        # Price move is not easily available, so we estimate
                        surprise_pct = ((actual - estimate) / abs(estimate)) * 100 if estimate != 0 else 0
                        price_move = round(surprise_pct * 0.5, 1)  # Rough estimate
                        
                        history.append({
                            "date": ed.strftime('%Y-%m-%d'),
                            "estimate": round(float(estimate), 2),
                            "actual": round(float(actual), 2),
                            "result": result,
                            "priceMove": price_move
                        })
                except Exception:
                    continue
        
        # Calculate beat rate
        beat_rate = calculate_beat_rate([
            {"epsEstimate": h["estimate"], "epsActual": h["actual"]} 
            for h in history
        ])
        
        return {
            "ticker": ticker,
            "name": info["name"],
            "sector": info["sector"],
            "date": date_str,
            "time": time,
            "expectedEPS": round(float(expected_eps), 2) if expected_eps else 1.50,
            "beatRate": beat_rate,
            "history": history[:8]  # Keep last 8 quarters
        }
        
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def fetch_all_earnings():
    """Fetch earnings data for all tickers."""
    earnings_data = []
    total = len(TICKERS)
    
    print(f"Fetching earnings data for {total} tickers...")
    
    for i, (ticker, info) in enumerate(TICKERS.items(), 1):
        print(f"[{i}/{total}] Fetching {ticker}...", end=" ")
        data = get_earnings_data(ticker, info)
        if data:
            earnings_data.append(data)
            print(f"✓ {data['date']} ({data['time']})")
        else:
            print("✗ No earnings date found")
    
    return earnings_data


def main():
    """Main entry point."""
    print("=" * 50)
    print("Earnings Calendar Data Fetcher")
    print("=" * 50)
    
    if not should_refresh():
        print(f"\nData is fresh (cached within {CACHE_HOURS} hours).")
        print(f"To force refresh, delete: {OUTPUT_FILE}")
        return
    
    print("\nFetching fresh earnings data from Yahoo Finance...")
    earnings_data = fetch_all_earnings()
    
    # Sort by date
    earnings_data.sort(key=lambda x: x["date"])
    
    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(earnings_data, f, indent=2)
    
    print(f"\n✓ Saved {len(earnings_data)} earnings records to {OUTPUT_FILE}")
    print(f"  Next refresh after: {datetime.now() + timedelta(hours=CACHE_HOURS)}")


if __name__ == "__main__":
    main()
