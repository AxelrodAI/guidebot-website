#!/usr/bin/env python3
"""
Short Interest Data Fetcher
Fetches short interest data from Yahoo Finance and FINRA sources.

Usage:
    python short_interest_fetcher.py [tickers...]
    python short_interest_fetcher.py              # Uses default watchlist
    python short_interest_fetcher.py AAPL TSLA   # Specific tickers
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
    import yfinance as yf

# Default watchlist - high short interest and meme stocks
DEFAULT_WATCHLIST = [
    'EWBC',   # East West Bancorp
    'GME',    # GameStop
    'AMC',    # AMC Entertainment
    'CVNA',   # Carvana
    'UPST',   # Upstart
    'RIVN',   # Rivian
    'NKLA',   # Nikola
    'COIN',   # Coinbase
    'PLTR',   # Palantir
    'SOFI',   # SoFi
    'MSTR',   # MicroStrategy
    'LCID',   # Lucid
    'BYND',   # Beyond Meat
    'SPCE',   # Virgin Galactic
    'TSLA',   # Tesla
    'BBBY',   # Bed Bath & Beyond
    'HOOD',   # Robinhood
    'SNOW',   # Snowflake
    'CRWD',   # CrowdStrike
    'DASH',   # DoorDash
]

# Threshold list stocks - updated periodically
# Source: https://www.nyse.com/regulation/threshold-securities
THRESHOLD_LIST = ['GME', 'AMC', 'UPST', 'NKLA', 'BBBY', 'BYND', 'SPCE']

OUTPUT_FILE = Path(__file__).parent / 'short_interest.json'


def get_sector(ticker_info):
    """Extract sector from Yahoo Finance info."""
    sector = ticker_info.get('sector', 'Unknown')
    # Map to simpler categories
    sector_map = {
        'Financial Services': 'Financial',
        'Consumer Cyclical': 'Consumer',
        'Consumer Defensive': 'Consumer',
        'Communication Services': 'Technology',
        'Basic Materials': 'Materials',
    }
    return sector_map.get(sector, sector)


def fetch_short_interest(ticker: str, prev_data: dict = None) -> dict:
    """Fetch short interest data for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract short interest data
        shares_short = info.get('sharesShort', 0) or 0
        shares_float = info.get('floatShares', 0) or 1  # Avoid div by zero
        shares_outstanding = info.get('sharesOutstanding', 0) or 1
        avg_volume = info.get('averageVolume', 0) or 1
        prev_shares_short = info.get('sharesShortPriorMonth', shares_short)
        short_percent_float = info.get('shortPercentOfFloat', 0) or 0
        
        # Calculate SI % if not provided
        if short_percent_float == 0 and shares_float > 0:
            short_percent_float = (shares_short / shares_float) * 100
        else:
            short_percent_float *= 100  # Convert from decimal
        
        # Days to cover
        dtc = info.get('shortRatio', 0) or 0
        if dtc == 0 and avg_volume > 0:
            dtc = shares_short / avg_volume
        
        # Week-over-week change calculation
        # Use prior month data as proxy, or calculate from cached data
        si_change = 0
        if prev_data and ticker in prev_data:
            prev_si = prev_data[ticker].get('si_percent', short_percent_float)
            si_change = short_percent_float - prev_si
        elif prev_shares_short > 0 and shares_float > 0:
            prev_si_pct = (prev_shares_short / shares_float) * 100
            si_change = short_percent_float - prev_si_pct
        
        # Check threshold list
        on_threshold = ticker in THRESHOLD_LIST
        
        return {
            'ticker': ticker,
            'company': info.get('shortName', info.get('longName', ticker)),
            'sector': get_sector(info),
            'si_percent': round(short_percent_float, 2),
            'si_change': round(si_change, 2),
            'dtc': round(dtc, 2),
            'shares_short': shares_short,
            'shares_float': shares_float,
            'avg_volume': avg_volume,
            'threshold': on_threshold,
            'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'market_cap': info.get('marketCap', 0),
            'last_updated': datetime.now().isoformat(),
        }
        
    except Exception as e:
        print(f"  ⚠️ Error fetching {ticker}: {e}")
        return None


def load_previous_data() -> dict:
    """Load previous data for WoW calculations."""
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, 'r') as f:
                data = json.load(f)
                return {h['ticker']: h for h in data.get('holdings', [])}
        except:
            pass
    return {}


def main():
    # Get tickers from args or use default
    if len(sys.argv) > 1:
        tickers = [t.upper() for t in sys.argv[1:]]
    else:
        tickers = DEFAULT_WATCHLIST
    
    print(f"📊 Short Interest Fetcher")
    print(f"   Fetching data for {len(tickers)} tickers...")
    print()
    
    # Load previous data for change calculations
    prev_data = load_previous_data()
    
    holdings = []
    errors = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"  [{i}/{len(tickers)}] {ticker}...", end=' ', flush=True)
        
        data = fetch_short_interest(ticker, prev_data)
        if data:
            holdings.append(data)
            si = data['si_percent']
            dtc = data['dtc']
            chg = data['si_change']
            chg_str = f"+{chg:.1f}%" if chg >= 0 else f"{chg:.1f}%"
            print(f"SI: {si:.1f}% | DTC: {dtc:.1f} | Chg: {chg_str}")
        else:
            errors.append(ticker)
            print("❌ Failed")
    
    # Sort by SI% descending
    holdings.sort(key=lambda x: x['si_percent'], reverse=True)
    
    # Prepare output
    output = {
        'lastUpdated': datetime.now().isoformat(),
        'totalHoldings': len(holdings),
        'highSI': len([h for h in holdings if h['si_percent'] >= 20]),
        'highDTC': len([h for h in holdings if h['dtc'] > 5]),
        'onThreshold': len([h for h in holdings if h['threshold']]),
        'holdings': holdings,
        'errors': errors,
    }
    
    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"✅ Complete! Saved to {OUTPUT_FILE}")
    print()
    print("📈 Summary:")
    print(f"   Total: {len(holdings)} holdings")
    print(f"   High SI (>20%): {output['highSI']}")
    print(f"   High DTC (>5): {output['highDTC']}")
    print(f"   On Threshold: {output['onThreshold']}")
    
    if errors:
        print(f"   ⚠️ Errors: {', '.join(errors)}")
    
    # Print top squeeze candidates
    print()
    print("🚀 Top Squeeze Candidates:")
    for h in holdings[:5]:
        score = calculate_squeeze_score(h)
        print(f"   {h['ticker']:6} | SI: {h['si_percent']:5.1f}% | DTC: {h['dtc']:4.1f} | Score: {score}")


def calculate_squeeze_score(h: dict) -> int:
    """Calculate squeeze potential score (0-100)."""
    score = 0
    
    si = h['si_percent']
    if si >= 30: score += 40
    elif si >= 20: score += 30
    elif si >= 15: score += 20
    elif si >= 10: score += 10
    
    dtc = h['dtc']
    if dtc >= 7: score += 30
    elif dtc >= 5: score += 20
    elif dtc >= 3: score += 10
    
    chg = h['si_change']
    if chg >= 5: score += 20
    elif chg >= 2: score += 10
    
    if h['threshold']: score += 10
    
    return min(score, 100)


if __name__ == '__main__':
    main()
