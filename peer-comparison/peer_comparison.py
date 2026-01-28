#!/usr/bin/env python3
"""
Peer Comparison Generator
Auto-build relative valuation tables with percentile rankings.
Compare P/E, EV/EBITDA, P/S, margins across sector peers.

Uses Yahoo Finance API for data.
"""

import json
import os
from datetime import datetime
from typing import Optional
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'yfinance', 'pandas', 'numpy'])
    import yfinance as yf
    import pandas as pd
    import numpy as np

# Cache and output paths
SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / "peer_cache.json"
PEER_GROUPS_FILE = SCRIPT_DIR / "peer_groups.json"

# Industry to sector mapping for dynamic peer finding
SECTOR_ETFS = {
    "Technology": ["XLK", "VGT", "FTEC"],
    "Healthcare": ["XLV", "VHT", "FHLC"],
    "Financial Services": ["XLF", "VFH", "FNCL"],
    "Consumer Cyclical": ["XLY", "VCR", "FDIS"],
    "Consumer Defensive": ["XLP", "VDC", "FSTA"],
    "Energy": ["XLE", "VDE", "FENY"],
    "Industrials": ["XLI", "VIS", "FIDU"],
    "Basic Materials": ["XLB", "VAW", "FMAT"],
    "Utilities": ["XLU", "VPU", "FUTY"],
    "Real Estate": ["XLRE", "VNQ", "FREL"],
    "Communication Services": ["XLC", "VOX", "FCOM"]
}

# Key valuation metrics to compare
METRICS = {
    "pe_ratio": {"name": "P/E Ratio", "key": "trailingPE", "higher_better": False},
    "forward_pe": {"name": "Forward P/E", "key": "forwardPE", "higher_better": False},
    "peg_ratio": {"name": "PEG Ratio", "key": "pegRatio", "higher_better": False},
    "ps_ratio": {"name": "P/S Ratio", "key": "priceToSalesTrailing12Months", "higher_better": False},
    "pb_ratio": {"name": "P/B Ratio", "key": "priceToBook", "higher_better": False},
    "ev_ebitda": {"name": "EV/EBITDA", "key": "enterpriseToEbitda", "higher_better": False},
    "ev_revenue": {"name": "EV/Revenue", "key": "enterpriseToRevenue", "higher_better": False},
    "profit_margin": {"name": "Profit Margin", "key": "profitMargins", "higher_better": True, "pct": True},
    "operating_margin": {"name": "Operating Margin", "key": "operatingMargins", "higher_better": True, "pct": True},
    "gross_margin": {"name": "Gross Margin", "key": "grossMargins", "higher_better": True, "pct": True},
    "roe": {"name": "ROE", "key": "returnOnEquity", "higher_better": True, "pct": True},
    "roa": {"name": "ROA", "key": "returnOnAssets", "higher_better": True, "pct": True},
    "debt_equity": {"name": "Debt/Equity", "key": "debtToEquity", "higher_better": False},
    "current_ratio": {"name": "Current Ratio", "key": "currentRatio", "higher_better": True},
    "revenue_growth": {"name": "Revenue Growth", "key": "revenueGrowth", "higher_better": True, "pct": True},
    "earnings_growth": {"name": "Earnings Growth", "key": "earningsGrowth", "higher_better": True, "pct": True},
}


def load_cache() -> dict:
    """Load cached stock data."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {"stocks": {}, "lastUpdated": None}


def save_cache(cache: dict):
    """Save stock data cache."""
    cache["lastUpdated"] = datetime.now().isoformat()
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def load_peer_groups() -> dict:
    """Load custom peer groups."""
    if PEER_GROUPS_FILE.exists():
        with open(PEER_GROUPS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_peer_groups(groups: dict):
    """Save custom peer groups."""
    with open(PEER_GROUPS_FILE, "w") as f:
        json.dump(groups, f, indent=2)


def get_stock_info(ticker: str, cache: dict, force_refresh: bool = False) -> Optional[dict]:
    """Get stock info from cache or Yahoo Finance."""
    ticker = ticker.upper()
    
    # Check cache (valid for 24 hours)
    if not force_refresh and ticker in cache.get("stocks", {}):
        cached = cache["stocks"][ticker]
        cached_time = datetime.fromisoformat(cached.get("cachedAt", "2000-01-01"))
        if (datetime.now() - cached_time).total_seconds() < 86400:  # 24 hours
            return cached.get("data")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or "shortName" not in info:
            return None
        
        # Extract key data
        data = {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "marketCap": info.get("marketCap"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        }
        
        # Extract all metrics
        for metric_id, metric_info in METRICS.items():
            value = info.get(metric_info["key"])
            if value is not None and not (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
                data[metric_id] = value
        
        # Cache it
        if "stocks" not in cache:
            cache["stocks"] = {}
        cache["stocks"][ticker] = {
            "data": data,
            "cachedAt": datetime.now().isoformat()
        }
        
        return data
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return None


def find_peers_by_industry(ticker: str, cache: dict, max_peers: int = 10) -> list[str]:
    """Find peer companies in the same industry."""
    info = get_stock_info(ticker, cache)
    if not info:
        return []
    
    industry = info.get("industry", "")
    sector = info.get("sector", "")
    
    # Common industry peer mappings (pre-defined for popular stocks)
    INDUSTRY_PEERS = {
        "Software - Infrastructure": ["MSFT", "ORCL", "CRM", "NOW", "ADBE", "INTU", "WDAY", "SNOW", "PANW", "CRWD"],
        "Semiconductors": ["NVDA", "AMD", "INTC", "AVGO", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC"],
        "Internet Content & Information": ["GOOGL", "META", "SNAP", "PINS", "TWTR", "SPOT", "NFLX"],
        "Consumer Electronics": ["AAPL", "SONY", "HPQ", "DELL", "LOGI"],
        "Auto Manufacturers": ["TSLA", "F", "GM", "TM", "HMC", "RIVN", "LCID", "NIO", "XPEV", "LI"],
        "Internet Retail": ["AMZN", "BABA", "JD", "PDD", "MELI", "SE", "SHOP", "ETSY", "EBAY", "W"],
        "Banks - Diversified": ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "SCHW"],
        "Drug Manufacturers": ["JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "AMGN", "GILD", "REGN", "VRTX"],
        "Oil & Gas Integrated": ["XOM", "CVX", "SHEL", "TTE", "BP", "COP", "EOG", "SLB", "OXY", "PSX"],
    }
    
    # Check if we have pre-defined peers
    if industry in INDUSTRY_PEERS:
        peers = [p for p in INDUSTRY_PEERS[industry] if p != ticker.upper()][:max_peers]
        return peers
    
    # Fall back to scanning cached stocks for same industry
    peers = []
    for cached_ticker, cached_data in cache.get("stocks", {}).items():
        if cached_ticker == ticker.upper():
            continue
        cached_info = cached_data.get("data", {})
        if cached_info.get("industry") == industry:
            peers.append(cached_ticker)
            if len(peers) >= max_peers:
                break
    
    return peers


def get_peer_group(ticker: str, cache: dict, custom_peers: list[str] = None) -> list[str]:
    """Get peer group for a ticker (custom or auto-detected)."""
    peer_groups = load_peer_groups()
    ticker = ticker.upper()
    
    if custom_peers:
        return [p.upper() for p in custom_peers]
    
    if ticker in peer_groups:
        return peer_groups[ticker]
    
    return find_peers_by_industry(ticker, cache)


def calculate_percentile(value: float, values: list[float], higher_better: bool) -> int:
    """Calculate percentile rank for a value."""
    if not values or value is None:
        return None
    
    values = [v for v in values if v is not None]
    if not values:
        return None
    
    count_below = sum(1 for v in values if v < value)
    percentile = int((count_below / len(values)) * 100)
    
    # Invert for metrics where lower is better
    if not higher_better:
        percentile = 100 - percentile
    
    return percentile


def build_comparison_table(ticker: str, peers: list[str], cache: dict, 
                          metrics: list[str] = None) -> dict:
    """Build a full comparison table for a ticker vs peers."""
    ticker = ticker.upper()
    all_tickers = [ticker] + [p.upper() for p in peers]
    
    if metrics is None:
        metrics = ["pe_ratio", "forward_pe", "ps_ratio", "ev_ebitda", 
                  "profit_margin", "roe", "revenue_growth"]
    
    # Fetch all stock data
    print(f"Fetching data for {len(all_tickers)} stocks...")
    stock_data = {}
    for t in all_tickers:
        data = get_stock_info(t, cache)
        if data:
            stock_data[t] = data
            print(f"  [OK] {t}: {data.get('name', t)}")
        else:
            print(f"  [--] {t}: Failed to fetch")
    
    save_cache(cache)
    
    if ticker not in stock_data:
        return {"error": f"Could not fetch data for {ticker}"}
    
    # Build comparison data
    comparison = {
        "target": ticker,
        "targetName": stock_data[ticker].get("name", ticker),
        "sector": stock_data[ticker].get("sector"),
        "industry": stock_data[ticker].get("industry"),
        "peerCount": len([t for t in all_tickers if t in stock_data]) - 1,
        "generatedAt": datetime.now().isoformat(),
        "metrics": {},
        "stocks": {}
    }
    
    # Calculate metrics and percentiles
    for metric_id in metrics:
        if metric_id not in METRICS:
            continue
        
        metric_info = METRICS[metric_id]
        metric_name = metric_info["name"]
        higher_better = metric_info.get("higher_better", False)
        is_pct = metric_info.get("pct", False)
        
        # Collect all values for percentile calculation
        all_values = []
        for t in all_tickers:
            if t in stock_data and metric_id in stock_data[t]:
                all_values.append(stock_data[t][metric_id])
        
        # Build metric comparison
        metric_comparison = {
            "name": metric_name,
            "higherBetter": higher_better,
            "isPercent": is_pct,
            "values": {}
        }
        
        for t in all_tickers:
            if t not in stock_data:
                continue
            
            value = stock_data[t].get(metric_id)
            percentile = calculate_percentile(value, all_values, higher_better) if value is not None else None
            
            metric_comparison["values"][t] = {
                "value": value,
                "percentile": percentile,
                "formatted": format_value(value, is_pct) if value is not None else "N/A"
            }
        
        # Calculate peer average (excluding target)
        peer_values = [stock_data[t].get(metric_id) for t in peers if t in stock_data and metric_id in stock_data[t]]
        peer_avg = np.mean([v for v in peer_values if v is not None]) if peer_values else None
        metric_comparison["peerAverage"] = format_value(peer_avg, is_pct) if peer_avg is not None else "N/A"
        
        # Premium/discount to peers
        target_value = stock_data[ticker].get(metric_id)
        if target_value is not None and peer_avg is not None and peer_avg != 0:
            premium = ((target_value / peer_avg) - 1) * 100
            metric_comparison["premiumDiscount"] = round(premium, 1)
        
        comparison["metrics"][metric_id] = metric_comparison
    
    # Add full stock data
    for t in all_tickers:
        if t in stock_data:
            comparison["stocks"][t] = stock_data[t]
    
    return comparison


def format_value(value: float, is_pct: bool = False) -> str:
    """Format a value for display."""
    if value is None:
        return "N/A"
    if is_pct:
        return f"{value * 100:.1f}%"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value) >= 100:
        return f"{value:.1f}"
    return f"{value:.2f}"


def format_market_cap(value: float) -> str:
    """Format market cap in human readable form."""
    if value is None:
        return "N/A"
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    if value >= 1e9:
        return f"${value/1e9:.1f}B"
    if value >= 1e6:
        return f"${value/1e6:.0f}M"
    return f"${value:,.0f}"


def print_comparison_table(comparison: dict):
    """Print a formatted comparison table."""
    if "error" in comparison:
        print(f"Error: {comparison['error']}")
        return
    
    target = comparison["target"]
    print(f"\n{'='*80}")
    print(f"PEER COMPARISON: {target} - {comparison.get('targetName', target)}")
    print(f"Sector: {comparison.get('sector', 'N/A')} | Industry: {comparison.get('industry', 'N/A')}")
    print(f"Peers: {comparison.get('peerCount', 0)} companies")
    print(f"{'='*80}\n")
    
    stocks = comparison.get("stocks", {})
    tickers = [target] + [t for t in stocks.keys() if t != target]
    
    # Print header
    header = f"{'Metric':<20}"
    for t in tickers[:8]:  # Limit to 8 columns
        marker = "*" if t == target else ""
        header += f"{t + marker:>10}"
    header += f"{'Peer Avg':>10}"
    print(header)
    print("-" * len(header))
    
    # Print metrics
    for metric_id, metric_data in comparison.get("metrics", {}).items():
        row = f"{metric_data['name']:<20}"
        values = metric_data.get("values", {})
        
        for t in tickers[:8]:
            if t in values:
                val_info = values[t]
                formatted = val_info.get("formatted", "N/A")
                pctl = val_info.get("percentile")
                if pctl is not None:
                    row += f"{formatted:>7}({pctl:2d})"
                else:
                    row += f"{formatted:>10}"
            else:
                row += f"{'N/A':>10}"
        
        row += f"{metric_data.get('peerAverage', 'N/A'):>10}"
        print(row)
    
    print()
    
    # Print market caps
    print(f"{'Market Cap':<20}", end="")
    for t in tickers[:8]:
        if t in stocks:
            mcap = format_market_cap(stocks[t].get("marketCap"))
            print(f"{mcap:>10}", end="")
    print()
    
    # Print premium/discount summary
    print(f"\n{'='*80}")
    print("VALUATION SUMMARY (vs Peer Average)")
    print("-" * 40)
    
    for metric_id, metric_data in comparison.get("metrics", {}).items():
        prem_disc = metric_data.get("premiumDiscount")
        if prem_disc is not None:
            indicator = "[+]" if prem_disc > 0 else "[-]" if prem_disc < 0 else "[=]"
            sign = "+" if prem_disc > 0 else ""
            print(f"  {metric_data['name']:<18}: {indicator} {sign}{prem_disc:.1f}% vs peers")


def create_custom_peer_group(name: str, tickers: list[str]):
    """Create or update a custom peer group."""
    peer_groups = load_peer_groups()
    peer_groups[name.upper()] = [t.upper() for t in tickers]
    save_peer_groups(peer_groups)
    print(f"[OK] Created peer group '{name}' with {len(tickers)} stocks")


def list_peer_groups():
    """List all custom peer groups."""
    groups = load_peer_groups()
    if not groups:
        print("No custom peer groups defined.")
        return
    
    print("\nCustom Peer Groups:")
    print("-" * 40)
    for name, tickers in groups.items():
        print(f"  {name}: {', '.join(tickers)}")


def export_comparison(comparison: dict, output_path: str = None):
    """Export comparison to JSON file."""
    if output_path is None:
        target = comparison.get("target", "comparison")
        output_path = SCRIPT_DIR / f"comparison_{target}_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(output_path, "w") as f:
        json.dump(comparison, f, indent=2)
    
    print(f"[OK] Exported to {output_path}")
    return str(output_path)


# Example usage
if __name__ == "__main__":
    cache = load_cache()
    
    # Example: Compare NVDA to semiconductor peers
    comparison = build_comparison_table(
        "NVDA",
        ["AMD", "INTC", "AVGO", "QCOM", "TXN", "MU"],
        cache,
        metrics=["pe_ratio", "forward_pe", "ps_ratio", "ev_ebitda", "profit_margin", "roe", "revenue_growth"]
    )
    
    print_comparison_table(comparison)
    export_comparison(comparison)
