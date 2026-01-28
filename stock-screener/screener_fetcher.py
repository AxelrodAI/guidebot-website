#!/usr/bin/env python3
"""
Stock Screener Data Fetcher
Fetches comprehensive stock data for screening universe.

Usage:
    python screener_fetcher.py                    # Fetch default universe
    python screener_fetcher.py --sp500           # S&P 500 stocks
    python screener_fetcher.py AAPL MSFT GOOG   # Specific tickers
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
    import yfinance as yf

try:
    import pandas as pd
except ImportError:
    print("Installing pandas...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "-q"])
    import pandas as pd

OUTPUT_FILE = Path(__file__).parent / 'stock_universe.json'

# Default screening universe (mix of sectors)
DEFAULT_UNIVERSE = [
    # Technology
    'AAPL', 'MSFT', 'GOOG', 'META', 'NVDA', 'AMZN', 'CRM', 'ORCL', 'ADBE', 'INTC', 
    'AMD', 'CSCO', 'AVGO', 'TXN', 'QCOM', 'IBM', 'NOW', 'INTU', 'AMAT', 'MU',
    # Financial
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC', 'SCHW', 'BLK',
    'V', 'MA', 'AXP', 'COF', 'SPGI', 'ICE', 'CME', 'MCO', 'CB', 'TRV',
    # Healthcare
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT', 'DHR', 'BMY',
    'AMGN', 'GILD', 'CVS', 'CI', 'HUM', 'MDT', 'ISRG', 'SYK', 'ZTS', 'VRTX',
    # Consumer
    'PG', 'KO', 'PEP', 'WMT', 'COST', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT',
    'LOW', 'TJX', 'DG', 'DLTR', 'ROST', 'ORLY', 'AZO', 'CMG', 'YUM', 'DPZ',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'VLO', 'PSX', 'OXY',
    # Industrials
    'UNP', 'UPS', 'HON', 'CAT', 'RTX', 'BA', 'DE', 'LMT', 'GE', 'MMM',
    # Communication
    'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR',
    # Other
    'BRK-B', 'TSLA', 'NEE', 'DUK', 'SO',
]


def fetch_stock_data(ticker: str) -> dict:
    """Fetch comprehensive stock data for screening."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Basic info
        data = {
            'ticker': ticker,
            'name': info.get('shortName', info.get('longName', ticker)),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'price': info.get('currentPrice', info.get('regularMarketPrice', 0)) or 0,
            'marketCap': info.get('marketCap', 0) or 0,
        }
        
        # Valuation metrics
        data['pe'] = info.get('trailingPE', 0) or 0
        data['forwardPE'] = info.get('forwardPE', 0) or 0
        data['peg'] = info.get('pegRatio', 0) or 0
        data['priceToBook'] = info.get('priceToBook', 0) or 0
        data['priceToSales'] = info.get('priceToSalesTrailing12Months', 0) or 0
        data['evToEbitda'] = info.get('enterpriseToEbitda', 0) or 0
        data['evToRevenue'] = info.get('enterpriseToRevenue', 0) or 0
        
        # Growth metrics
        data['revenueGrowth'] = (info.get('revenueGrowth', 0) or 0) * 100
        data['epsGrowth'] = (info.get('earningsGrowth', 0) or 0) * 100
        data['earningsQuarterlyGrowth'] = (info.get('earningsQuarterlyGrowth', 0) or 0) * 100
        
        # Profitability
        data['grossMargin'] = (info.get('grossMargins', 0) or 0) * 100
        data['operatingMargin'] = (info.get('operatingMargins', 0) or 0) * 100
        data['netMargin'] = (info.get('profitMargins', 0) or 0) * 100
        data['ebitdaMargin'] = (info.get('ebitdaMargins', 0) or 0) * 100
        
        # Returns
        data['roe'] = (info.get('returnOnEquity', 0) or 0) * 100
        data['roa'] = (info.get('returnOnAssets', 0) or 0) * 100
        
        # Income
        data['dividendYield'] = (info.get('dividendYield', 0) or 0) * 100
        data['payoutRatio'] = (info.get('payoutRatio', 0) or 0) * 100
        
        # Balance Sheet
        data['debtToEquity'] = info.get('debtToEquity', 0) or 0
        data['currentRatio'] = info.get('currentRatio', 0) or 0
        data['quickRatio'] = info.get('quickRatio', 0) or 0
        
        # Size
        data['beta'] = info.get('beta', 0) or 0
        data['avgVolume'] = info.get('averageVolume', 0) or 0
        data['sharesOutstanding'] = info.get('sharesOutstanding', 0) or 0
        
        # Technical (simple)
        data['fiftyTwoWeekHigh'] = info.get('fiftyTwoWeekHigh', 0) or 0
        data['fiftyTwoWeekLow'] = info.get('fiftyTwoWeekLow', 0) or 0
        data['fiftyDayAverage'] = info.get('fiftyDayAverage', 0) or 0
        data['twoHundredDayAverage'] = info.get('twoHundredDayAverage', 0) or 0
        
        # Calculate RSI approximation from recent price vs 50MA
        if data['fiftyDayAverage'] > 0 and data['price'] > 0:
            ratio = data['price'] / data['fiftyDayAverage']
            # Rough RSI approximation (not exact)
            data['rsi'] = min(100, max(0, 50 + (ratio - 1) * 100))
        else:
            data['rsi'] = 50
        
        return data
        
    except Exception as e:
        print(f"  ⚠️ Error fetching {ticker}: {e}")
        return None


def main():
    # Parse arguments
    if '--sp500' in sys.argv:
        # Fetch S&P 500 list (simplified - top 100)
        print("Fetching S&P 500 universe (top 100)...")
        tickers = DEFAULT_UNIVERSE[:100]
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        tickers = [t.upper() for t in sys.argv[1:] if not t.startswith('--')]
    else:
        tickers = DEFAULT_UNIVERSE
    
    print(f"📊 Stock Screener Data Fetcher")
    print(f"   Fetching {len(tickers)} stocks...")
    print()
    
    stocks = []
    errors = []
    
    # Use thread pool for parallel fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_stock_data, t): t for t in tickers}
        
        for i, future in enumerate(as_completed(futures), 1):
            ticker = futures[future]
            try:
                data = future.result()
                if data:
                    stocks.append(data)
                    print(f"  [{i}/{len(tickers)}] {ticker} ✅")
                else:
                    errors.append(ticker)
                    print(f"  [{i}/{len(tickers)}] {ticker} ❌")
            except Exception as e:
                errors.append(ticker)
                print(f"  [{i}/{len(tickers)}] {ticker} ❌ {e}")
    
    # Sort by market cap
    stocks.sort(key=lambda x: x['marketCap'], reverse=True)
    
    # Prepare output
    output = {
        'lastUpdated': datetime.now().isoformat(),
        'stockCount': len(stocks),
        'errors': errors,
        'stocks': stocks,
    }
    
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"✅ Complete! {len(stocks)} stocks saved to {OUTPUT_FILE}")
    
    if errors:
        print(f"⚠️  Errors: {', '.join(errors)}")
    
    # Print sector breakdown
    sectors = {}
    for s in stocks:
        sector = s.get('sector', 'Unknown')
        sectors[sector] = sectors.get(sector, 0) + 1
    
    print()
    print("📊 Sector Breakdown:")
    for sector, count in sorted(sectors.items(), key=lambda x: -x[1]):
        print(f"   {sector}: {count}")


if __name__ == '__main__':
    main()
