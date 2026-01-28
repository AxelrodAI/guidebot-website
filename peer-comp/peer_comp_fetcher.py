#!/usr/bin/env python3
"""
Peer Comparison Data Fetcher
Fetches peer stock data and generates comparison tables.

Usage:
    python peer_comp_fetcher.py AAPL              # Auto-find sector peers
    python peer_comp_fetcher.py AAPL MSFT GOOG   # Specific peers
    python peer_comp_fetcher.py AAPL --export    # Export to Excel
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

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
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "-q"])
    import pandas as pd

OUTPUT_FILE = Path(__file__).parent / 'peer_comp.json'

# Sector -> Common peers mapping
SECTOR_PEERS = {
    'Technology': ['AAPL', 'MSFT', 'GOOG', 'META', 'NVDA', 'AMZN', 'CRM', 'ORCL', 'ADBE', 'INTC', 'AMD', 'CSCO'],
    'Financial Services': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC', 'TFC', 'SCHW', 'BLK', 'AXP'],
    'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT', 'DHR', 'BMY', 'AMGN', 'GILD'],
    'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'NKE', 'MCD', 'SBUX', 'LOW', 'TJX', 'BKNG', 'GM', 'F', 'ABNB'],
    'Consumer Defensive': ['PG', 'KO', 'PEP', 'WMT', 'COST', 'PM', 'MO', 'CL', 'MDLZ', 'KHC', 'GIS', 'K'],
    'Industrials': ['UPS', 'HON', 'UNP', 'CAT', 'RTX', 'BA', 'DE', 'LMT', 'GE', 'MMM', 'EMR', 'ITW'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'VLO', 'PSX', 'OXY', 'KMI', 'WMB'],
    'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'EXC', 'XEL', 'PEG', 'WEC', 'ES', 'ED'],
    'Real Estate': ['AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'WELL', 'DLR', 'AVB', 'EQR', 'VTR'],
    'Materials': ['LIN', 'APD', 'SHW', 'ECL', 'FCX', 'NEM', 'NUE', 'VMC', 'MLM', 'DOW', 'DD', 'PPG'],
    'Communication Services': ['GOOG', 'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR', 'EA', 'ATVI', 'WBD'],
}


def get_stock_data(ticker: str) -> dict:
    """Fetch comprehensive stock data for peer comparison."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Basic info
        data = {
            'ticker': ticker,
            'name': info.get('shortName', info.get('longName', ticker)),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'change': info.get('regularMarketChangePercent', 0),
            'marketCap': info.get('marketCap', 0),
            'ev': info.get('enterpriseValue', 0),
            'avgVolume': info.get('averageVolume', 0),
            'week52Low': info.get('fiftyTwoWeekLow', 0),
            'week52High': info.get('fiftyTwoWeekHigh', 0),
        }
        
        # Valuation metrics
        data['pe'] = info.get('trailingPE', 0) or 0
        data['forwardPE'] = info.get('forwardPE', 0) or 0
        data['evEbitda'] = info.get('enterpriseToEbitda', 0) or 0
        data['evSales'] = info.get('enterpriseToRevenue', 0) or 0
        data['priceToSales'] = info.get('priceToSalesTrailing12Months', 0) or 0
        data['peg'] = info.get('pegRatio', 0) or 0
        data['priceToBook'] = info.get('priceToBook', 0) or 0
        
        # Growth metrics
        data['revenueGrowth'] = (info.get('revenueGrowth', 0) or 0) * 100
        data['epsGrowth'] = (info.get('earningsGrowth', 0) or 0) * 100
        
        # Get FCF growth from financials if available
        try:
            cf = stock.cashflow
            if cf is not None and 'Free Cash Flow' in cf.index:
                fcf = cf.loc['Free Cash Flow']
                if len(fcf) >= 2 and fcf.iloc[1] != 0:
                    data['fcfGrowth'] = ((fcf.iloc[0] - fcf.iloc[1]) / abs(fcf.iloc[1])) * 100
                else:
                    data['fcfGrowth'] = 0
            else:
                data['fcfGrowth'] = 0
        except:
            data['fcfGrowth'] = 0
        
        # Profitability metrics
        data['grossMargin'] = (info.get('grossMargins', 0) or 0) * 100
        data['operatingMargin'] = (info.get('operatingMargins', 0) or 0) * 100
        data['netMargin'] = (info.get('profitMargins', 0) or 0) * 100
        
        # Return metrics
        data['roe'] = (info.get('returnOnEquity', 0) or 0) * 100
        data['roa'] = (info.get('returnOnAssets', 0) or 0) * 100
        
        # ROIC calculation (approximate)
        try:
            ni = info.get('netIncomeToCommon', 0)
            total_debt = info.get('totalDebt', 0)
            total_equity = info.get('totalStockholderEquity', info.get('bookValue', 0) * info.get('sharesOutstanding', 1))
            invested_capital = total_debt + total_equity
            if invested_capital > 0:
                data['roic'] = (ni / invested_capital) * 100
            else:
                data['roic'] = 0
        except:
            data['roic'] = 0
        
        return data
        
    except Exception as e:
        print(f"  ⚠️ Error fetching {ticker}: {e}")
        return None


def find_sector_peers(target_data: dict, max_peers: int = 10) -> list:
    """Find peers in the same sector."""
    sector = target_data.get('sector', 'Technology')
    
    # Get peers for this sector
    peer_tickers = SECTOR_PEERS.get(sector, SECTOR_PEERS['Technology'])
    
    # Remove target from peers
    peer_tickers = [t for t in peer_tickers if t != target_data['ticker']]
    
    return peer_tickers[:max_peers]


def calculate_ranks(data: list, metrics: list) -> list:
    """Calculate ranks for each metric."""
    for metric in metrics:
        # Determine if lower is better
        lower_better = metric in ['pe', 'forwardPE', 'evEbitda', 'evSales', 'priceToSales', 'peg', 'priceToBook']
        
        # Sort and assign ranks
        valid_data = [(i, d[metric]) for i, d in enumerate(data) if d.get(metric, 0) > 0]
        valid_data.sort(key=lambda x: x[1], reverse=not lower_better)
        
        for rank, (idx, _) in enumerate(valid_data, 1):
            data[idx][f'{metric}_rank'] = rank
    
    return data


def export_to_excel(data: list, target_ticker: str):
    """Export peer comparison to Excel with formatting."""
    df = pd.DataFrame(data)
    
    # Define metric groups
    valuation_cols = ['ticker', 'name', 'price', 'marketCap', 'pe', 'forwardPE', 'evEbitda', 'evSales', 'priceToSales', 'peg', 'priceToBook']
    growth_cols = ['ticker', 'name', 'revenueGrowth', 'epsGrowth', 'fcfGrowth']
    profitability_cols = ['ticker', 'name', 'grossMargin', 'operatingMargin', 'netMargin']
    returns_cols = ['ticker', 'name', 'roe', 'roic', 'roa']
    
    # Create Excel writer
    output_path = Path(__file__).parent / f'peer_comp_{target_ticker}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Full data
        df.to_excel(writer, sheet_name='All Data', index=False)
        
        # Valuation
        df[[c for c in valuation_cols if c in df.columns]].to_excel(writer, sheet_name='Valuation', index=False)
        
        # Growth
        df[[c for c in growth_cols if c in df.columns]].to_excel(writer, sheet_name='Growth', index=False)
        
        # Profitability
        df[[c for c in profitability_cols if c in df.columns]].to_excel(writer, sheet_name='Profitability', index=False)
        
        # Returns
        df[[c for c in returns_cols if c in df.columns]].to_excel(writer, sheet_name='Returns', index=False)
    
    print(f"📊 Excel exported to: {output_path}")
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python peer_comp_fetcher.py TICKER [PEER1 PEER2 ...] [--export]")
        print("Example: python peer_comp_fetcher.py AAPL")
        print("         python peer_comp_fetcher.py AAPL MSFT GOOG --export")
        return
    
    # Parse arguments
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    export = '--export' in sys.argv
    
    target_ticker = args[0].upper()
    custom_peers = [t.upper() for t in args[1:]] if len(args) > 1 else None
    
    print(f"📊 Peer Comparison Generator")
    print(f"   Target: {target_ticker}")
    print()
    
    # Fetch target stock
    print(f"  Fetching {target_ticker}...", end=' ', flush=True)
    target_data = get_stock_data(target_ticker)
    if not target_data:
        print("❌ Failed to fetch target stock")
        return
    print(f"✅ {target_data['name']} ({target_data['sector']})")
    
    # Get peers
    if custom_peers:
        peer_tickers = custom_peers
        print(f"\n  Using custom peers: {', '.join(peer_tickers)}")
    else:
        peer_tickers = find_sector_peers(target_data)
        print(f"\n  Auto-selected {len(peer_tickers)} sector peers")
    
    # Fetch peer data
    print()
    all_data = [target_data]
    
    for i, ticker in enumerate(peer_tickers, 1):
        print(f"  [{i}/{len(peer_tickers)}] {ticker}...", end=' ', flush=True)
        peer_data = get_stock_data(ticker)
        if peer_data:
            all_data.append(peer_data)
            print(f"✅ {peer_data['name']}")
        else:
            print("❌ Failed")
    
    # Calculate ranks
    metrics = ['pe', 'forwardPE', 'evEbitda', 'evSales', 'priceToSales', 'peg', 'priceToBook',
               'revenueGrowth', 'epsGrowth', 'fcfGrowth', 'grossMargin', 'operatingMargin', 
               'netMargin', 'roe', 'roic', 'roa']
    all_data = calculate_ranks(all_data, metrics)
    
    # Calculate averages (excluding target)
    peers_only = [d for d in all_data if d['ticker'] != target_ticker]
    avg_data = {'ticker': 'AVG', 'name': 'Peer Average'}
    for metric in metrics:
        values = [d[metric] for d in peers_only if d.get(metric, 0) > 0]
        avg_data[metric] = sum(values) / len(values) if values else 0
    
    # Save to JSON
    output = {
        'target': target_ticker,
        'lastUpdated': datetime.now().isoformat(),
        'peerCount': len(peers_only),
        'stocks': all_data,
        'averages': avg_data,
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Print summary
    print()
    print(f"✅ Complete! {len(all_data)} stocks analyzed")
    print(f"   Saved to: {OUTPUT_FILE}")
    
    # Print comparison summary
    print()
    print(f"📈 {target_ticker} vs Peer Averages:")
    print("-" * 50)
    
    key_metrics = [
        ('P/E', 'pe', True),
        ('EV/EBITDA', 'evEbitda', True),
        ('Revenue Growth', 'revenueGrowth', False),
        ('Net Margin', 'netMargin', False),
        ('ROE', 'roe', False),
    ]
    
    for label, key, lower_better in key_metrics:
        target_val = target_data.get(key, 0)
        avg_val = avg_data.get(key, 0)
        if avg_val > 0:
            diff = ((target_val - avg_val) / avg_val) * 100
            is_better = (diff < 0) if lower_better else (diff > 0)
            sign = '+' if diff >= 0 else ''
            indicator = '✅' if is_better else '⚠️'
            
            if key in ['revenueGrowth', 'netMargin', 'roe']:
                print(f"  {label:15} {target_val:>8.1f}% vs {avg_val:>8.1f}% ({sign}{diff:.1f}%) {indicator}")
            else:
                print(f"  {label:15} {target_val:>8.1f}x vs {avg_val:>8.1f}x ({sign}{diff:.1f}%) {indicator}")
    
    # Export to Excel if requested
    if export:
        print()
        export_to_excel(all_data, target_ticker)


if __name__ == '__main__':
    main()
