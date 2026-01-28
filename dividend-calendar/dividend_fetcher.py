#!/usr/bin/env python3
"""
Dividend Calendar Data Fetcher
Fetches dividend data using yfinance and calculates sustainability metrics.

Usage:
    python dividend_fetcher.py                    # Fetch all stocks
    python dividend_fetcher.py --tickers AAPL MSFT  # Fetch specific tickers
    python dividend_fetcher.py --watchlist        # Fetch from watchlist.txt
    python dividend_fetcher.py --excel            # Also export to Excel
"""

import yfinance as yf
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import io

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Default dividend stocks to track
DEFAULT_TICKERS = [
    # Dividend Aristocrats / Kings
    'JNJ', 'PG', 'KO', 'PEP', 'MCD', 'MMM', 'ABT', 'CL', 'EMR', 'GPC',
    # High Yield
    'VZ', 'T', 'MO', 'PM', 'IBM', 'CVX', 'XOM',
    # REITs
    'O', 'VICI', 'STAG', 'NNN', 'WPC',
    # Tech Dividend Payers
    'MSFT', 'AAPL', 'AVGO', 'TXN', 'QCOM',
    # Financials
    'JPM', 'BAC', 'WFC', 'GS', 'BLK',
    # Healthcare
    'ABBV', 'PFE', 'MRK', 'BMY', 'LLY',
    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP',
    # Industrials
    'CAT', 'HON', 'UPS', 'LMT', 'RTX'
]

SECTOR_MAP = {
    'Technology': ['MSFT', 'AAPL', 'AVGO', 'TXN', 'QCOM', 'IBM'],
    'Healthcare': ['JNJ', 'ABBV', 'PFE', 'MRK', 'BMY', 'LLY', 'ABT'],
    'Consumer': ['PG', 'KO', 'PEP', 'MCD', 'CL', 'MO', 'PM'],
    'Financial': ['JPM', 'BAC', 'WFC', 'GS', 'BLK'],
    'Energy': ['CVX', 'XOM'],
    'Communication': ['VZ', 'T'],
    'Industrial': ['MMM', 'EMR', 'CAT', 'HON', 'UPS', 'LMT', 'RTX', 'GPC'],
    'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP'],
    'Real Estate': ['O', 'VICI', 'STAG', 'NNN', 'WPC']
}

# Dividend Kings/Aristocrats years of consecutive increases
DIVIDEND_STREAKS = {
    'PG': 68, 'KO': 62, 'JNJ': 62, 'CL': 61, 'MMM': 65, 'EMR': 67,
    'GPC': 68, 'ABT': 52, 'PEP': 52, 'MCD': 48, 'CVX': 37, 'XOM': 42,
    'O': 30, 'ABBV': 12, 'MSFT': 22, 'AAPL': 12, 'IBM': 28, 'VZ': 18
}


def get_sector(ticker):
    """Get sector for a ticker"""
    for sector, tickers in SECTOR_MAP.items():
        if ticker in tickers:
            return sector
    return 'Other'


def calculate_sustainability(payout_ratio, dgr5y, years_growth, debt_to_equity=None):
    """
    Calculate dividend sustainability score (0-100)
    
    Factors:
    - Payout ratio (lower is better, <60% ideal)
    - Dividend growth rate (positive is good)
    - Years of consecutive growth
    - Debt levels (if available)
    """
    score = 50  # Base score
    
    # Payout ratio factor (-20 to +20)
    if payout_ratio < 40:
        score += 20
    elif payout_ratio < 60:
        score += 10
    elif payout_ratio < 80:
        score += 0
    elif payout_ratio < 100:
        score -= 15
    else:
        score -= 25
    
    # Growth rate factor (-10 to +15)
    if dgr5y > 10:
        score += 15
    elif dgr5y > 5:
        score += 10
    elif dgr5y > 0:
        score += 5
    elif dgr5y > -5:
        score -= 5
    else:
        score -= 15
    
    # Consecutive years factor (0 to +15)
    if years_growth >= 50:
        score += 15
    elif years_growth >= 25:
        score += 12
    elif years_growth >= 10:
        score += 8
    elif years_growth >= 5:
        score += 4
    
    return max(0, min(100, score))


def fetch_stock_data(ticker):
    """Fetch dividend data for a single stock"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get basic info
        name = info.get('shortName', info.get('longName', ticker))
        dividend_rate = info.get('dividendRate', 0) or 0
        dividend_yield = info.get('dividendYield', 0) or 0
        payout_ratio = (info.get('payoutRatio', 0) or 0) * 100
        
        # Get ex-dividend date
        ex_div_date = info.get('exDividendDate')
        if ex_div_date:
            ex_div_date = datetime.fromtimestamp(ex_div_date).strftime('%Y-%m-%d')
        else:
            # Estimate next ex-date (monthly for REITs, quarterly for others)
            ex_div_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Get dividend history for growth calculation
        dividends = stock.dividends
        dgr5y = 0
        dividend_history = []
        
        if len(dividends) >= 8:
            # Get last 8 quarterly dividends
            recent = dividends.tail(8).tolist()
            dividend_history = [round(d, 4) for d in recent]
            
            # Calculate 5-year growth rate if we have enough data
            if len(dividends) >= 20:
                old_div = dividends.iloc[-20:-16].mean()
                new_div = dividends.iloc[-4:].mean()
                if old_div > 0:
                    dgr5y = round(((new_div / old_div) ** 0.2 - 1) * 100, 1)
        
        # Get years of consecutive growth
        years_growth = DIVIDEND_STREAKS.get(ticker, 0)
        
        # Calculate sustainability
        sustainability = calculate_sustainability(payout_ratio, dgr5y, years_growth)
        
        # Estimate pay date (usually 2-3 weeks after ex-date)
        pay_date = (datetime.strptime(ex_div_date, '%Y-%m-%d') + timedelta(days=21)).strftime('%Y-%m-%d')
        
        return {
            'ticker': ticker,
            'name': name[:30],  # Truncate long names
            'sector': get_sector(ticker),
            'yield': round(dividend_yield * 100, 2),
            'annualDiv': round(dividend_rate, 2),
            'exDate': ex_div_date,
            'payDate': pay_date,
            'dgr5y': dgr5y,
            'payoutRatio': round(payout_ratio, 1),
            'yearsGrowth': years_growth,
            'sustainability': sustainability,
            'dividendHistory': dividend_history if dividend_history else [dividend_rate / 4] * 8
        }
        
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def fetch_all_dividends(tickers, max_workers=10):
    """Fetch dividend data for multiple stocks in parallel"""
    stocks = []
    
    print(f"Fetching dividend data for {len(tickers)} stocks...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_stock_data, ticker): ticker for ticker in tickers}
        
        for i, future in enumerate(as_completed(futures)):
            ticker = futures[future]
            try:
                result = future.result()
                if result:
                    stocks.append(result)
                    print(f"  [{i+1}/{len(tickers)}] {ticker}: {result['yield']}% yield")
            except Exception as e:
                print(f"  [{i+1}/{len(tickers)}] {ticker}: FAILED - {e}")
    
    return stocks


def calculate_stats(stocks):
    """Calculate aggregate statistics"""
    if not stocks:
        return {}
    
    yields = [s['yield'] for s in stocks if s['yield'] > 0]
    
    return {
        'totalStocks': len(stocks),
        'avgYield': round(sum(yields) / len(yields), 2) if yields else 0,
        'sp500Yield': 1.4,  # Approximate S&P 500 yield
        'highYieldCount': len([s for s in stocks if s['yield'] >= 4]),
        'aristocratCount': len([s for s in stocks if s['yearsGrowth'] >= 25]),
        'atRiskCount': len([s for s in stocks if s['sustainability'] < 50])
    }


def save_json(stocks, output_path):
    """Save data to JSON file"""
    data = {
        'lastUpdated': datetime.now().isoformat(),
        'stats': calculate_stats(stocks),
        'stocks': stocks
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nSaved {len(stocks)} stocks to {output_path}")


def save_excel(stocks, output_path):
    """Save data to Excel file"""
    try:
        import pandas as pd
        
        df = pd.DataFrame(stocks)
        df = df[['ticker', 'name', 'sector', 'yield', 'annualDiv', 'exDate', 'payDate', 
                 'dgr5y', 'payoutRatio', 'yearsGrowth', 'sustainability']]
        
        # Sort by yield
        df = df.sort_values('yield', ascending=False)
        
        df.to_excel(output_path, index=False, sheet_name='Dividends')
        print(f"Saved Excel to {output_path}")
        
    except ImportError:
        print("pandas/openpyxl not installed - skipping Excel export")
        print("Install with: pip install pandas openpyxl")


def main():
    parser = argparse.ArgumentParser(description='Fetch dividend data')
    parser.add_argument('--tickers', nargs='+', help='Specific tickers to fetch')
    parser.add_argument('--watchlist', action='store_true', help='Load from watchlist.txt')
    parser.add_argument('--excel', action='store_true', help='Also export to Excel')
    parser.add_argument('--output', default='dividend_data.json', help='Output JSON file')
    args = parser.parse_args()
    
    # Determine tickers to fetch
    if args.tickers:
        tickers = [t.upper() for t in args.tickers]
    elif args.watchlist:
        watchlist_path = Path(__file__).parent / 'watchlist.txt'
        if watchlist_path.exists():
            tickers = [t.strip().upper() for t in watchlist_path.read_text().splitlines() if t.strip()]
        else:
            print("watchlist.txt not found, using defaults")
            tickers = DEFAULT_TICKERS
    else:
        tickers = DEFAULT_TICKERS
    
    # Fetch data
    stocks = fetch_all_dividends(tickers)
    
    # Sort by yield
    stocks.sort(key=lambda x: x['yield'], reverse=True)
    
    # Save outputs
    output_path = Path(__file__).parent / args.output
    save_json(stocks, output_path)
    
    if args.excel:
        excel_path = output_path.with_suffix('.xlsx')
        save_excel(stocks, excel_path)
    
    # Print summary
    stats = calculate_stats(stocks)
    print(f"\n📊 Summary:")
    print(f"   Total stocks: {stats['totalStocks']}")
    print(f"   Average yield: {stats['avgYield']}%")
    print(f"   High yield (>4%): {stats['highYieldCount']}")
    print(f"   Aristocrats (25+ yrs): {stats['aristocratCount']}")
    print(f"   At-risk (<50 score): {stats['atRiskCount']}")


if __name__ == '__main__':
    main()
