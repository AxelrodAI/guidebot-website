#!/usr/bin/env python3
"""
Earnings Estimate Revision Tracker
Track sell-side estimate revisions, flag acceleration, compare whisper to consensus.

Uses Yahoo Finance for consensus estimates and historical data.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

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

# Paths
SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / "estimate_cache.json"
WATCHLIST_FILE = SCRIPT_DIR / "watchlist.json"
ALERTS_FILE = SCRIPT_DIR / "revision_alerts.json"
ACCURACY_FILE = SCRIPT_DIR / "analyst_accuracy.json"


@dataclass
class EstimateSnapshot:
    """Point-in-time snapshot of consensus estimates."""
    ticker: str
    timestamp: str
    current_quarter: dict  # EPS and Revenue estimates
    next_quarter: dict
    current_year: dict
    next_year: dict
    num_analysts: int
    recommendation: str
    target_price: float
    target_low: float
    target_high: float


@dataclass
class RevisionAlert:
    """Alert for significant estimate revision."""
    ticker: str
    timestamp: str
    alert_type: str  # 'upgrade', 'downgrade', 'acceleration', 'deceleration'
    metric: str  # 'eps', 'revenue'
    period: str  # 'Q1', 'FY2026', etc
    old_estimate: float
    new_estimate: float
    change_pct: float
    num_revisions_48h: int
    severity: str  # 'low', 'medium', 'high'


def load_cache() -> dict:
    """Load cached estimate data."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {"estimates": {}, "history": {}}


def save_cache(cache: dict):
    """Save estimate cache."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, default=str)


def load_watchlist() -> List[str]:
    """Load watchlist of tickers to monitor."""
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, "r") as f:
            data = json.load(f)
            return data.get("tickers", [])
    return []


def save_watchlist(tickers: List[str]):
    """Save watchlist."""
    with open(WATCHLIST_FILE, "w") as f:
        json.dump({"tickers": tickers, "lastUpdated": datetime.now().isoformat()}, f, indent=2)


def load_alerts() -> List[dict]:
    """Load revision alerts."""
    if ALERTS_FILE.exists():
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    return []


def save_alerts(alerts: List[dict]):
    """Save revision alerts."""
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2, default=str)


def get_earnings_estimates(ticker: str, cache: dict) -> Optional[EstimateSnapshot]:
    """Fetch earnings estimates for a ticker from Yahoo Finance."""
    ticker = ticker.upper()
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get analyst estimates
        try:
            earnings_estimate = stock.earnings_estimate
            revenue_estimate = stock.revenue_estimate
        except:
            earnings_estimate = None
            revenue_estimate = None
        
        # Build current quarter estimates
        current_q = {
            "eps_estimate": info.get("forwardEps"),
            "eps_low": None,
            "eps_high": None,
            "num_analysts": info.get("numberOfAnalystOpinions", 0)
        }
        
        # Get quarterly estimates if available
        if earnings_estimate is not None and not earnings_estimate.empty:
            try:
                if "0q" in earnings_estimate.columns:
                    current_q["eps_estimate"] = earnings_estimate.loc["avg", "0q"] if "avg" in earnings_estimate.index else None
                    current_q["eps_low"] = earnings_estimate.loc["low", "0q"] if "low" in earnings_estimate.index else None
                    current_q["eps_high"] = earnings_estimate.loc["high", "0q"] if "high" in earnings_estimate.index else None
                    current_q["num_analysts"] = int(earnings_estimate.loc["numberOfAnalysts", "0q"]) if "numberOfAnalysts" in earnings_estimate.index else 0
            except:
                pass
        
        next_q = {
            "eps_estimate": None,
            "eps_low": None,
            "eps_high": None,
            "num_analysts": 0
        }
        
        if earnings_estimate is not None and not earnings_estimate.empty:
            try:
                if "+1q" in earnings_estimate.columns:
                    next_q["eps_estimate"] = earnings_estimate.loc["avg", "+1q"] if "avg" in earnings_estimate.index else None
                    next_q["eps_low"] = earnings_estimate.loc["low", "+1q"] if "low" in earnings_estimate.index else None
                    next_q["eps_high"] = earnings_estimate.loc["high", "+1q"] if "high" in earnings_estimate.index else None
                    next_q["num_analysts"] = int(earnings_estimate.loc["numberOfAnalysts", "+1q"]) if "numberOfAnalysts" in earnings_estimate.index else 0
            except:
                pass
        
        # Revenue estimates
        current_q_rev = {}
        next_q_rev = {}
        
        if revenue_estimate is not None and not revenue_estimate.empty:
            try:
                if "0q" in revenue_estimate.columns:
                    current_q_rev["revenue_estimate"] = revenue_estimate.loc["avg", "0q"] if "avg" in revenue_estimate.index else None
                    current_q_rev["revenue_low"] = revenue_estimate.loc["low", "0q"] if "low" in revenue_estimate.index else None
                    current_q_rev["revenue_high"] = revenue_estimate.loc["high", "0q"] if "high" in revenue_estimate.index else None
                if "+1q" in revenue_estimate.columns:
                    next_q_rev["revenue_estimate"] = revenue_estimate.loc["avg", "+1q"] if "avg" in revenue_estimate.index else None
            except:
                pass
        
        # Merge EPS and revenue
        current_q.update(current_q_rev)
        next_q.update(next_q_rev)
        
        # Full year estimates
        current_y = {
            "eps_estimate": info.get("forwardEps"),
            "revenue_estimate": info.get("totalRevenue")
        }
        
        if earnings_estimate is not None and not earnings_estimate.empty:
            try:
                if "0y" in earnings_estimate.columns:
                    current_y["eps_estimate"] = earnings_estimate.loc["avg", "0y"] if "avg" in earnings_estimate.index else None
            except:
                pass
        
        next_y = {"eps_estimate": None, "revenue_estimate": None}
        
        if earnings_estimate is not None and not earnings_estimate.empty:
            try:
                if "+1y" in earnings_estimate.columns:
                    next_y["eps_estimate"] = earnings_estimate.loc["avg", "+1y"] if "avg" in earnings_estimate.index else None
            except:
                pass
        
        snapshot = EstimateSnapshot(
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            current_quarter=current_q,
            next_quarter=next_q,
            current_year=current_y,
            next_year=next_y,
            num_analysts=info.get("numberOfAnalystOpinions", 0),
            recommendation=info.get("recommendationKey", "N/A"),
            target_price=info.get("targetMeanPrice"),
            target_low=info.get("targetLowPrice"),
            target_high=info.get("targetHighPrice")
        )
        
        # Cache the snapshot
        if ticker not in cache["estimates"]:
            cache["estimates"][ticker] = []
        cache["estimates"][ticker].append(asdict(snapshot))
        
        # Keep only last 30 snapshots per ticker
        if len(cache["estimates"][ticker]) > 30:
            cache["estimates"][ticker] = cache["estimates"][ticker][-30:]
        
        return snapshot
        
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return None


def get_earnings_history(ticker: str, cache: dict) -> Optional[Dict]:
    """Get historical earnings (actual vs estimate) for accuracy tracking."""
    ticker = ticker.upper()
    
    try:
        stock = yf.Ticker(ticker)
        earnings_history = stock.earnings_history
        
        if earnings_history is None or earnings_history.empty:
            return None
        
        history = []
        for idx, row in earnings_history.iterrows():
            entry = {
                "date": str(idx),
                "eps_estimate": row.get("epsEstimate"),
                "eps_actual": row.get("epsActual"),
                "eps_difference": row.get("epsDifference"),
                "surprise_pct": row.get("surprisePercent")
            }
            history.append(entry)
        
        cache["history"][ticker] = {
            "earnings": history,
            "lastUpdated": datetime.now().isoformat()
        }
        
        return {"ticker": ticker, "history": history}
        
    except Exception as e:
        print(f"  Error fetching earnings history for {ticker}: {e}")
        return None


def detect_revision(ticker: str, cache: dict) -> List[RevisionAlert]:
    """Detect significant estimate revisions by comparing to cached data."""
    alerts = []
    ticker = ticker.upper()
    
    if ticker not in cache["estimates"] or len(cache["estimates"][ticker]) < 2:
        return alerts
    
    snapshots = cache["estimates"][ticker]
    current = snapshots[-1]
    previous = snapshots[-2]
    
    # Check EPS estimate changes
    for period, period_name in [("current_quarter", "Current Q"), ("next_quarter", "Next Q"), 
                                 ("current_year", "Current FY"), ("next_year", "Next FY")]:
        old_eps = previous.get(period, {}).get("eps_estimate")
        new_eps = current.get(period, {}).get("eps_estimate")
        
        if old_eps and new_eps and old_eps != 0:
            change_pct = ((new_eps - old_eps) / abs(old_eps)) * 100
            
            # Significant revision threshold: >2%
            if abs(change_pct) >= 2:
                alert_type = "upgrade" if change_pct > 0 else "downgrade"
                severity = "high" if abs(change_pct) >= 10 else "medium" if abs(change_pct) >= 5 else "low"
                
                alert = RevisionAlert(
                    ticker=ticker,
                    timestamp=datetime.now().isoformat(),
                    alert_type=alert_type,
                    metric="eps",
                    period=period_name,
                    old_estimate=old_eps,
                    new_estimate=new_eps,
                    change_pct=round(change_pct, 2),
                    num_revisions_48h=1,  # Would need tracking for real acceleration
                    severity=severity
                )
                alerts.append(alert)
    
    # Check revenue estimate changes
    for period, period_name in [("current_quarter", "Current Q"), ("next_quarter", "Next Q")]:
        old_rev = previous.get(period, {}).get("revenue_estimate")
        new_rev = current.get(period, {}).get("revenue_estimate")
        
        if old_rev and new_rev and old_rev != 0:
            change_pct = ((new_rev - old_rev) / abs(old_rev)) * 100
            
            if abs(change_pct) >= 2:
                alert_type = "upgrade" if change_pct > 0 else "downgrade"
                severity = "high" if abs(change_pct) >= 10 else "medium" if abs(change_pct) >= 5 else "low"
                
                alert = RevisionAlert(
                    ticker=ticker,
                    timestamp=datetime.now().isoformat(),
                    alert_type=alert_type,
                    metric="revenue",
                    period=period_name,
                    old_estimate=old_rev,
                    new_estimate=new_rev,
                    change_pct=round(change_pct, 2),
                    num_revisions_48h=1,
                    severity=severity
                )
                alerts.append(alert)
    
    return alerts


def calculate_beat_miss_history(ticker: str, cache: dict) -> Dict:
    """Calculate historical beat/miss rate for a ticker."""
    history = cache.get("history", {}).get(ticker, {}).get("earnings", [])
    
    if not history:
        # Try to fetch it
        result = get_earnings_history(ticker, cache)
        if result:
            history = result.get("history", [])
    
    if not history:
        return {"ticker": ticker, "beats": 0, "misses": 0, "meets": 0, "avg_surprise": None}
    
    beats = 0
    misses = 0
    meets = 0
    surprises = []
    
    for entry in history:
        surprise = entry.get("surprise_pct")
        if surprise is not None:
            surprises.append(surprise)
            if surprise > 1:
                beats += 1
            elif surprise < -1:
                misses += 1
            else:
                meets += 1
    
    return {
        "ticker": ticker,
        "quarters_tracked": len(history),
        "beats": beats,
        "misses": misses,
        "meets": meets,
        "beat_rate": round(beats / len(history) * 100, 1) if history else 0,
        "avg_surprise_pct": round(np.mean(surprises), 2) if surprises else None,
        "history": history[-4:]  # Last 4 quarters
    }


def get_revision_momentum(ticker: str, cache: dict, days: int = 30) -> Dict:
    """Calculate estimate revision momentum over time."""
    ticker = ticker.upper()
    
    if ticker not in cache["estimates"] or len(cache["estimates"][ticker]) < 2:
        return {"ticker": ticker, "momentum": "insufficient_data"}
    
    snapshots = cache["estimates"][ticker]
    
    # Need at least 2 snapshots in the time period
    if len(snapshots) < 2:
        return {"ticker": ticker, "momentum": "insufficient_data"}
    
    first = snapshots[0]
    last = snapshots[-1]
    
    # Calculate EPS revision direction
    first_eps = first.get("current_quarter", {}).get("eps_estimate")
    last_eps = last.get("current_quarter", {}).get("eps_estimate")
    
    if first_eps and last_eps and first_eps != 0:
        change = ((last_eps - first_eps) / abs(first_eps)) * 100
        
        if change > 5:
            momentum = "strong_positive"
        elif change > 0:
            momentum = "positive"
        elif change > -5:
            momentum = "negative"
        else:
            momentum = "strong_negative"
    else:
        momentum = "stable"
    
    return {
        "ticker": ticker,
        "momentum": momentum,
        "snapshots_analyzed": len(snapshots),
        "first_eps": first_eps,
        "last_eps": last_eps,
        "change_pct": round(change, 2) if first_eps and last_eps else None
    }


def format_currency(value: float) -> str:
    """Format large numbers as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1e12:
        return f"${value/1e12:.2f}T"
    if abs(value) >= 1e9:
        return f"${value/1e9:.1f}B"
    if abs(value) >= 1e6:
        return f"${value/1e6:.0f}M"
    return f"${value:,.2f}"


def print_estimate_summary(snapshot: EstimateSnapshot):
    """Print formatted estimate summary."""
    print(f"\n{'='*60}")
    print(f"EARNINGS ESTIMATES: {snapshot.ticker}")
    print(f"{'='*60}")
    print(f"Analysts: {snapshot.num_analysts} | Recommendation: {snapshot.recommendation.upper()}")
    print(f"Price Target: ${snapshot.target_price:.2f} (${snapshot.target_low:.2f} - ${snapshot.target_high:.2f})" 
          if snapshot.target_price else "Price Target: N/A")
    print()
    
    print("EPS ESTIMATES:")
    print("-" * 40)
    
    cq = snapshot.current_quarter
    if cq.get("eps_estimate"):
        range_str = f"({cq.get('eps_low', 'N/A')} - {cq.get('eps_high', 'N/A')})" if cq.get('eps_low') else ""
        print(f"  Current Quarter: ${cq['eps_estimate']:.2f} {range_str}")
    
    nq = snapshot.next_quarter
    if nq.get("eps_estimate"):
        range_str = f"({nq.get('eps_low', 'N/A')} - {nq.get('eps_high', 'N/A')})" if nq.get('eps_low') else ""
        print(f"  Next Quarter:    ${nq['eps_estimate']:.2f} {range_str}")
    
    cy = snapshot.current_year
    if cy.get("eps_estimate"):
        print(f"  Current Year:    ${cy['eps_estimate']:.2f}")
    
    ny = snapshot.next_year
    if ny.get("eps_estimate"):
        print(f"  Next Year:       ${ny['eps_estimate']:.2f}")
    
    print()
    print("REVENUE ESTIMATES:")
    print("-" * 40)
    
    if cq.get("revenue_estimate"):
        print(f"  Current Quarter: {format_currency(cq['revenue_estimate'])}")
    if nq.get("revenue_estimate"):
        print(f"  Next Quarter:    {format_currency(nq['revenue_estimate'])}")


def scan_watchlist(cache: dict) -> List[RevisionAlert]:
    """Scan all watchlist tickers for estimate revisions."""
    tickers = load_watchlist()
    if not tickers:
        print("Watchlist is empty. Add tickers with: python cli.py watch add TICKER")
        return []
    
    all_alerts = []
    print(f"Scanning {len(tickers)} watchlist tickers...")
    
    for ticker in tickers:
        snapshot = get_earnings_estimates(ticker, cache)
        if snapshot:
            print(f"  [OK] {ticker}")
            alerts = detect_revision(ticker, cache)
            all_alerts.extend(alerts)
        else:
            print(f"  [--] {ticker}")
    
    save_cache(cache)
    
    # Save any new alerts
    if all_alerts:
        existing = load_alerts()
        existing.extend([asdict(a) for a in all_alerts])
        # Keep last 100 alerts
        if len(existing) > 100:
            existing = existing[-100:]
        save_alerts(existing)
    
    return all_alerts


# Example usage
if __name__ == "__main__":
    cache = load_cache()
    
    # Example: Get estimates for NVDA
    snapshot = get_earnings_estimates("NVDA", cache)
    if snapshot:
        print_estimate_summary(snapshot)
    
    # Get beat/miss history
    history = calculate_beat_miss_history("NVDA", cache)
    print(f"\nBeat/Miss History: {history['beats']} beats, {history['misses']} misses, {history['meets']} meets")
    if history.get("avg_surprise_pct"):
        print(f"Average Surprise: {history['avg_surprise_pct']}%")
    
    save_cache(cache)
