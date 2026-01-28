#!/usr/bin/env python3
"""
Correlation Matrix Monitor
Track rolling correlations between portfolio assets and benchmarks.
Alert on correlation regime changes, identify diversification breakdowns.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os

# Cache settings
CACHE_FILE = os.path.join(os.path.dirname(__file__), "correlation_cache.json")
CACHE_DURATION_HOURS = 4


def load_cache() -> Dict:
    """Load cached data."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"data": {}, "timestamp": None}


def save_cache(cache: Dict):
    """Save cache to disk."""
    cache["timestamp"] = datetime.now().isoformat()
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, default=str)


def is_cache_valid(cache: Dict) -> bool:
    """Check if cache is still valid."""
    if not cache.get("timestamp"):
        return False
    cached_time = datetime.fromisoformat(cache["timestamp"])
    return (datetime.now() - cached_time).total_seconds() < CACHE_DURATION_HOURS * 3600


def get_price_data(tickers: List[str], days: int = 252, cache: Optional[Dict] = None) -> pd.DataFrame:
    """Fetch historical price data for tickers."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 30)  # Extra buffer for rolling calcs
    
    cache_key = f"prices_{','.join(sorted(tickers))}_{days}"
    
    if cache and cache_key in cache.get("data", {}) and is_cache_valid(cache):
        try:
            df = pd.DataFrame(cache["data"][cache_key])
            df.index = pd.to_datetime(df.index)
            return df
        except:
            pass  # Cache invalid, fetch fresh
    
    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        if 'Adj Close' in data.columns:
            prices = data['Adj Close']
        else:
            prices = data['Close'] if len(tickers) > 1 else data[['Close']].rename(columns={'Close': tickers[0]})
        
        if isinstance(prices, pd.Series):
            prices = prices.to_frame(name=tickers[0])
        
        prices = prices.dropna(how='all')
        
        # Cache with string index for JSON serialization
        if cache is not None and not prices.empty:
            cache_df = prices.copy()
            cache_df.index = cache_df.index.astype(str)
            cache.setdefault("data", {})[cache_key] = cache_df.to_dict()
            save_cache(cache)
        
        return prices
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()


def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily returns from prices."""
    return prices.pct_change().dropna()


def calculate_correlation_matrix(returns: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Calculate rolling correlation matrix (most recent window)."""
    if len(returns) < window:
        window = len(returns)
    recent_returns = returns.tail(window)
    return recent_returns.corr()


def calculate_rolling_correlation(returns: pd.DataFrame, asset1: str, asset2: str, window: int = 60) -> pd.Series:
    """Calculate rolling correlation between two assets."""
    if asset1 not in returns.columns or asset2 not in returns.columns:
        return pd.Series()
    return returns[asset1].rolling(window=window).corr(returns[asset2])


def detect_correlation_regime_change(rolling_corr: pd.Series, threshold: float = 0.3) -> List[Dict]:
    """Detect significant correlation regime changes."""
    changes = []
    
    if len(rolling_corr) < 20:
        return changes
    
    rolling_corr = rolling_corr.dropna()
    
    # Compare recent vs historical
    recent_corr = rolling_corr.tail(20).mean()
    historical_corr = rolling_corr.iloc[:-20].mean() if len(rolling_corr) > 40 else rolling_corr.mean()
    
    change = recent_corr - historical_corr
    
    if abs(change) >= threshold:
        changes.append({
            "type": "REGIME_CHANGE",
            "direction": "INCREASE" if change > 0 else "DECREASE",
            "magnitude": abs(change),
            "recent_corr": recent_corr,
            "historical_corr": historical_corr,
            "change": change
        })
    
    # Check for correlation breakdown (was high, now low or vice versa)
    if historical_corr > 0.6 and recent_corr < 0.3:
        changes.append({
            "type": "BREAKDOWN",
            "description": "Strong positive correlation has broken down",
            "recent_corr": recent_corr,
            "historical_corr": historical_corr
        })
    elif historical_corr < 0.3 and recent_corr > 0.6:
        changes.append({
            "type": "CONVERGENCE",
            "description": "Assets have become highly correlated",
            "recent_corr": recent_corr,
            "historical_corr": historical_corr
        })
    
    return changes


def analyze_diversification(corr_matrix: pd.DataFrame) -> Dict:
    """Analyze portfolio diversification based on correlation matrix."""
    # Get upper triangle (excluding diagonal)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    upper_corr = corr_matrix.where(mask)
    
    # Flatten and remove NaN
    correlations = upper_corr.values.flatten()
    correlations = correlations[~np.isnan(correlations)]
    
    if len(correlations) == 0:
        return {"status": "INSUFFICIENT_DATA"}
    
    avg_corr = np.mean(correlations)
    max_corr = np.max(correlations)
    min_corr = np.min(correlations)
    
    # Find highly correlated pairs
    high_corr_pairs = []
    for i, col1 in enumerate(corr_matrix.columns):
        for j, col2 in enumerate(corr_matrix.columns):
            if i < j:
                corr_val = corr_matrix.loc[col1, col2]
                if corr_val > 0.8:
                    high_corr_pairs.append({
                        "pair": [col1, col2],
                        "correlation": round(corr_val, 3)
                    })
    
    # Find negative correlations (hedges)
    hedges = []
    for i, col1 in enumerate(corr_matrix.columns):
        for j, col2 in enumerate(corr_matrix.columns):
            if i < j:
                corr_val = corr_matrix.loc[col1, col2]
                if corr_val < -0.2:
                    hedges.append({
                        "pair": [col1, col2],
                        "correlation": round(corr_val, 3)
                    })
    
    # Diversification score (lower avg correlation = better diversification)
    if avg_corr < 0.3:
        div_status = "EXCELLENT"
        div_score = 95
    elif avg_corr < 0.5:
        div_status = "GOOD"
        div_score = 75
    elif avg_corr < 0.7:
        div_status = "MODERATE"
        div_score = 50
    else:
        div_status = "POOR"
        div_score = 25
    
    return {
        "status": div_status,
        "score": div_score,
        "average_correlation": round(avg_corr, 3),
        "max_correlation": round(max_corr, 3),
        "min_correlation": round(min_corr, 3),
        "high_correlation_pairs": high_corr_pairs,
        "hedges": hedges,
        "num_pairs_analyzed": len(correlations)
    }


def get_benchmark_correlations(tickers: List[str], benchmarks: List[str] = None, 
                                window: int = 60, cache: Optional[Dict] = None) -> Dict:
    """Get correlation of portfolio assets vs benchmarks."""
    if benchmarks is None:
        benchmarks = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
    
    all_tickers = list(set(tickers + benchmarks))
    prices = get_price_data(all_tickers, days=window + 30, cache=cache)
    returns = calculate_returns(prices)
    
    results = {}
    
    for ticker in tickers:
        if ticker not in returns.columns:
            continue
        
        results[ticker] = {}
        for benchmark in benchmarks:
            if benchmark in returns.columns and ticker != benchmark:
                corr = returns[ticker].tail(window).corr(returns[benchmark].tail(window))
                results[ticker][benchmark] = round(corr, 3) if not np.isnan(corr) else None
    
    return results


def suggest_rebalancing(corr_matrix: pd.DataFrame, diversification: Dict) -> List[Dict]:
    """Suggest rebalancing actions based on correlation analysis."""
    suggestions = []
    
    # Flag highly correlated pairs
    for pair in diversification.get("high_correlation_pairs", []):
        suggestions.append({
            "type": "REDUCE_OVERLAP",
            "severity": "HIGH" if pair["correlation"] > 0.9 else "MEDIUM",
            "assets": pair["pair"],
            "correlation": pair["correlation"],
            "action": f"Consider reducing one of {pair['pair'][0]} or {pair['pair'][1]} - correlation {pair['correlation']:.2f}"
        })
    
    # Flag if no hedges exist
    if not diversification.get("hedges") and diversification.get("average_correlation", 0) > 0.5:
        suggestions.append({
            "type": "ADD_HEDGE",
            "severity": "MEDIUM",
            "action": "Consider adding negatively correlated assets (bonds, gold, inverse ETFs) to reduce portfolio risk"
        })
    
    # Flag poor diversification
    if diversification.get("status") == "POOR":
        suggestions.append({
            "type": "INCREASE_DIVERSIFICATION",
            "severity": "HIGH",
            "action": f"Portfolio has high average correlation ({diversification.get('average_correlation'):.2f}). Consider adding uncorrelated assets from different sectors/asset classes."
        })
    
    return suggestions


def generate_alerts(tickers: List[str], window: int = 60, cache: Optional[Dict] = None) -> List[Dict]:
    """Generate correlation alerts for portfolio."""
    alerts = []
    
    prices = get_price_data(tickers + ["SPY"], days=window + 60, cache=cache)
    returns = calculate_returns(prices)
    
    # Check correlation regime changes vs SPY
    for ticker in tickers:
        if ticker not in returns.columns or ticker == "SPY":
            continue
        
        rolling_corr = calculate_rolling_correlation(returns, ticker, "SPY", window=window)
        changes = detect_correlation_regime_change(rolling_corr)
        
        for change in changes:
            alert = {
                "ticker": ticker,
                "benchmark": "SPY",
                "time": datetime.now().isoformat(),
                **change
            }
            alerts.append(alert)
    
    # Check pairwise correlations within portfolio
    for i, ticker1 in enumerate(tickers):
        for ticker2 in tickers[i+1:]:
            if ticker1 not in returns.columns or ticker2 not in returns.columns:
                continue
            
            rolling_corr = calculate_rolling_correlation(returns, ticker1, ticker2, window=window)
            changes = detect_correlation_regime_change(rolling_corr, threshold=0.4)
            
            for change in changes:
                alert = {
                    "ticker": ticker1,
                    "benchmark": ticker2,
                    "time": datetime.now().isoformat(),
                    **change
                }
                alerts.append(alert)
    
    return alerts


def analyze_portfolio_correlations(tickers: List[str], window: int = 60, 
                                    refresh: bool = False) -> Dict:
    """Complete correlation analysis for a portfolio."""
    cache = load_cache() if not refresh else {"data": {}, "timestamp": None}
    
    # Add SPY as benchmark if not included
    all_tickers = list(set(tickers + ["SPY", "QQQ", "TLT"]))
    
    prices = get_price_data(all_tickers, days=window + 60, cache=cache)
    
    if prices.empty:
        return {"error": "Could not fetch price data"}
    
    returns = calculate_returns(prices)
    
    # Calculate correlation matrix for user's tickers
    user_returns = returns[[t for t in tickers if t in returns.columns]]
    corr_matrix = calculate_correlation_matrix(user_returns, window=window)
    
    # Analyze diversification
    diversification = analyze_diversification(corr_matrix)
    
    # Get benchmark correlations
    benchmark_corrs = get_benchmark_correlations(tickers, cache=cache)
    
    # Generate alerts
    alerts = generate_alerts(tickers, window=window, cache=cache)
    
    # Generate rebalancing suggestions
    suggestions = suggest_rebalancing(corr_matrix, diversification)
    
    save_cache(cache)
    
    return {
        "analyzed_at": datetime.now().isoformat(),
        "tickers": [t for t in tickers if t in returns.columns],
        "window_days": window,
        "correlation_matrix": corr_matrix.round(3).to_dict(),
        "diversification": diversification,
        "benchmark_correlations": benchmark_corrs,
        "alerts": alerts,
        "suggestions": suggestions
    }


def compare_correlation_periods(tickers: List[str], window1: int = 30, window2: int = 90) -> Dict:
    """Compare correlations over different time periods."""
    cache = load_cache()
    
    prices = get_price_data(tickers, days=max(window1, window2) + 30, cache=cache)
    returns = calculate_returns(prices)
    
    corr_short = calculate_correlation_matrix(returns, window=window1)
    corr_long = calculate_correlation_matrix(returns, window=window2)
    
    # Find biggest changes
    changes = []
    for i, col1 in enumerate(corr_short.columns):
        for j, col2 in enumerate(corr_short.columns):
            if i < j and col1 in corr_long.columns and col2 in corr_long.columns:
                short_val = corr_short.loc[col1, col2]
                long_val = corr_long.loc[col1, col2]
                diff = short_val - long_val
                
                if abs(diff) > 0.2:
                    changes.append({
                        "pair": [col1, col2],
                        f"corr_{window1}d": round(short_val, 3),
                        f"corr_{window2}d": round(long_val, 3),
                        "change": round(diff, 3),
                        "direction": "INCREASING" if diff > 0 else "DECREASING"
                    })
    
    changes.sort(key=lambda x: abs(x["change"]), reverse=True)
    
    save_cache(cache)
    
    return {
        "comparison": f"{window1}d vs {window2}d",
        f"correlation_matrix_{window1}d": corr_short.round(3).to_dict(),
        f"correlation_matrix_{window2}d": corr_long.round(3).to_dict(),
        "significant_changes": changes[:10]
    }


# Default watchlist for testing
DEFAULT_WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "XOM"]


if __name__ == "__main__":
    # Quick test
    result = analyze_portfolio_correlations(DEFAULT_WATCHLIST[:5], window=60)
    print(json.dumps(result, indent=2, default=str))
