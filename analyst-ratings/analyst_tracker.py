#!/usr/bin/env python3
"""
Analyst Rating Changes Monitor
Track upgrades/downgrades, price target changes, and consensus ratings.

Features:
- Rating change detection (upgrades/downgrades)
- Price target monitoring
- Consensus rating aggregation
- Analyst accuracy scoring
- Significant shift alerting
"""

import sys
# Fix Windows encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json
import os

@dataclass
class AnalystRating:
    """Individual analyst rating/price target"""
    firm: str
    rating: str  # Buy, Hold, Sell, etc.
    rating_numeric: int  # 1-5 scale (1=strong sell, 5=strong buy)
    price_target: float
    prior_rating: Optional[str] = None
    prior_target: Optional[float] = None
    date: Optional[str] = None
    action: str = "reiterate"  # upgrade, downgrade, initiate, reiterate

@dataclass  
class ConsensusRating:
    """Aggregated consensus for a stock"""
    ticker: str
    name: str
    current_price: float
    
    # Consensus metrics
    consensus_rating: str  # Strong Buy, Buy, Hold, Sell, Strong Sell
    consensus_score: float  # 1-5 scale
    num_analysts: int
    
    # Rating distribution
    strong_buy: int
    buy: int
    hold: int
    sell: int
    strong_sell: int
    
    # Price targets
    target_high: float
    target_low: float
    target_mean: float
    target_median: float
    upside_pct: float
    
    # Recent activity
    recent_upgrades: int  # Last 30 days
    recent_downgrades: int
    
    timestamp: str

@dataclass
class RatingAlert:
    """Alert for rating changes"""
    ticker: str
    alert_type: str  # UPGRADE, DOWNGRADE, TARGET_CHANGE, CONSENSUS_SHIFT, INITIATION
    severity: str  # "low", "medium", "high"
    message: str
    details: Dict
    timestamp: str

class AnalystTracker:
    """Main tracker for analyst ratings"""
    
    # Rating mappings
    RATING_MAP = {
        "Strong Buy": 5, "Outperform": 5, "Overweight": 5,
        "Buy": 4, "Accumulate": 4, "Positive": 4,
        "Hold": 3, "Neutral": 3, "Equal-Weight": 3, "Market Perform": 3, "Sector Perform": 3,
        "Sell": 2, "Underweight": 2, "Underperform": 2, "Negative": 2, "Reduce": 2,
        "Strong Sell": 1
    }
    
    # Thresholds
    SIGNIFICANT_TARGET_CHANGE = 0.10  # 10% change
    SIGNIFICANT_CONSENSUS_SHIFT = 0.5  # 0.5 points on 1-5 scale
    LARGE_UPSIDE_THRESHOLD = 0.25  # 25% upside potential
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(self.cache_dir, "ratings_cache.json")
        self.alerts_file = os.path.join(self.cache_dir, "ratings_alerts.json")
        self._load_cache()
    
    def _load_cache(self):
        """Load cached historical data"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {"last_updated": None, "historical_ratings": {}}
        except:
            self.cache = {"last_updated": None, "historical_ratings": {}}
    
    def _save_cache(self):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2, default=str)
    
    def _save_alerts(self, alerts: List[RatingAlert]):
        """Save alerts to JSON file"""
        existing = []
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r') as f:
                    existing = json.load(f)
            except:
                existing = []
        
        for alert in alerts:
            existing.append({
                "ticker": alert.ticker,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "details": alert.details,
                "timestamp": alert.timestamp
            })
        
        # Keep last 300 alerts
        existing = existing[-300:]
        
        with open(self.alerts_file, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def _rating_to_numeric(self, rating: str) -> int:
        """Convert text rating to 1-5 scale"""
        if not rating:
            return 3
        for key, val in self.RATING_MAP.items():
            if key.lower() in rating.lower():
                return val
        return 3  # Default to Hold
    
    def _numeric_to_consensus(self, score: float) -> str:
        """Convert numeric score to consensus text"""
        if score >= 4.5:
            return "Strong Buy"
        elif score >= 3.5:
            return "Buy"
        elif score >= 2.5:
            return "Hold"
        elif score >= 1.5:
            return "Sell"
        else:
            return "Strong Sell"
    
    def get_consensus(self, ticker: str) -> Optional[ConsensusRating]:
        """Get consensus rating for a ticker"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            name = info.get('shortName', info.get('longName', ticker))
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            
            # Get recommendation data
            rec = info.get('recommendationKey', 'hold')
            rec_mean = info.get('recommendationMean', 3.0)  # 1-5 scale, 1=strong buy
            num_analysts = info.get('numberOfAnalystOpinions', 0)
            
            # Get target prices
            target_high = info.get('targetHighPrice', current_price)
            target_low = info.get('targetLowPrice', current_price)
            target_mean = info.get('targetMeanPrice', current_price)
            target_median = info.get('targetMedianPrice', current_price)
            
            # Calculate upside
            upside_pct = (target_mean - current_price) / current_price if current_price > 0 else 0
            
            # Try to get recommendation trends
            try:
                rec_trend = stock.recommendations
                if rec_trend is not None and len(rec_trend) > 0:
                    # Count recent recommendations (last 30 days)
                    recent = rec_trend.tail(10)  # Last ~10 actions
                    
                    # Count distribution from recent
                    strong_buy = len(recent[recent['To Grade'].str.lower().str.contains('strong buy|outperform', na=False)])
                    buy = len(recent[recent['To Grade'].str.lower().str.contains('^buy|accumulate|overweight', na=False)])
                    hold = len(recent[recent['To Grade'].str.lower().str.contains('hold|neutral|equal', na=False)])
                    sell = len(recent[recent['To Grade'].str.lower().str.contains('^sell|underweight|reduce', na=False)])
                    strong_sell = len(recent[recent['To Grade'].str.lower().str.contains('strong sell', na=False)])
                    
                    # Count upgrades/downgrades
                    upgrades = len(recent[recent['Action'].str.lower().str.contains('up', na=False)])
                    downgrades = len(recent[recent['Action'].str.lower().str.contains('down', na=False)])
                else:
                    strong_buy = buy = hold = sell = strong_sell = 0
                    upgrades = downgrades = 0
            except:
                strong_buy = buy = hold = sell = strong_sell = 0
                upgrades = downgrades = 0
            
            # Convert yfinance recommendation mean (1=strong buy, 5=strong sell) to our scale (1=strong sell, 5=strong buy)
            # yfinance uses inverted scale
            consensus_score = 6 - rec_mean if rec_mean else 3
            
            return ConsensusRating(
                ticker=ticker,
                name=name,
                current_price=current_price,
                consensus_rating=self._numeric_to_consensus(consensus_score),
                consensus_score=round(consensus_score, 2),
                num_analysts=num_analysts,
                strong_buy=strong_buy,
                buy=buy,
                hold=hold,
                sell=sell,
                strong_sell=strong_sell,
                target_high=target_high or 0,
                target_low=target_low or 0,
                target_mean=target_mean or 0,
                target_median=target_median or 0,
                upside_pct=upside_pct,
                recent_upgrades=upgrades,
                recent_downgrades=downgrades,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"  ⚠️ Error fetching {ticker}: {e}")
            return None
    
    def get_recent_changes(self, ticker: str, days: int = 30) -> List[AnalystRating]:
        """Get recent rating changes for a ticker"""
        changes = []
        
        try:
            stock = yf.Ticker(ticker)
            rec = stock.recommendations
            
            if rec is None or len(rec) == 0:
                return changes
            
            # Filter to recent
            cutoff = datetime.now() - timedelta(days=days)
            
            for idx, row in rec.iterrows():
                try:
                    # Check if date is recent
                    rec_date = idx
                    if hasattr(rec_date, 'to_pydatetime'):
                        rec_date = rec_date.to_pydatetime()
                    
                    if rec_date.replace(tzinfo=None) < cutoff:
                        continue
                    
                    firm = row.get('Firm', 'Unknown')
                    to_grade = row.get('To Grade', '')
                    from_grade = row.get('From Grade', '')
                    action = row.get('Action', 'reiterate').lower()
                    
                    # Determine action type
                    if 'up' in action:
                        action_type = 'upgrade'
                    elif 'down' in action:
                        action_type = 'downgrade'
                    elif 'init' in action:
                        action_type = 'initiate'
                    else:
                        action_type = 'reiterate'
                    
                    changes.append(AnalystRating(
                        firm=firm,
                        rating=to_grade,
                        rating_numeric=self._rating_to_numeric(to_grade),
                        price_target=0,  # Not always in this data
                        prior_rating=from_grade if from_grade else None,
                        prior_target=None,
                        date=rec_date.strftime('%Y-%m-%d') if hasattr(rec_date, 'strftime') else str(rec_date),
                        action=action_type
                    ))
                except:
                    continue
                    
        except Exception as e:
            print(f"  ⚠️ Error getting changes for {ticker}: {e}")
        
        return changes
    
    def analyze_ticker(self, ticker: str, verbose: bool = False) -> Tuple[Optional[ConsensusRating], List[RatingAlert]]:
        """Analyze a ticker for consensus and generate alerts"""
        alerts = []
        
        consensus = self.get_consensus(ticker)
        if consensus is None:
            return None, alerts
        
        now = datetime.now()
        
        # Check for cached historical data
        cached = self.cache.get("historical_ratings", {}).get(ticker, {})
        prev_score = cached.get("consensus_score", consensus.consensus_score)
        prev_target = cached.get("target_mean", consensus.target_mean)
        
        # Alert: Significant consensus shift
        score_change = consensus.consensus_score - prev_score
        if abs(score_change) >= self.SIGNIFICANT_CONSENSUS_SHIFT:
            direction = "improved" if score_change > 0 else "weakened"
            alerts.append(RatingAlert(
                ticker=ticker,
                alert_type="CONSENSUS_SHIFT",
                severity="high" if abs(score_change) >= 1.0 else "medium",
                message=f"Consensus {direction} by {abs(score_change):.1f} points ({prev_score:.1f} → {consensus.consensus_score:.1f})",
                details={
                    "old_score": prev_score,
                    "new_score": consensus.consensus_score,
                    "change": score_change,
                    "consensus": consensus.consensus_rating
                },
                timestamp=now.isoformat()
            ))
        
        # Alert: Significant target change
        if prev_target > 0:
            target_change_pct = (consensus.target_mean - prev_target) / prev_target
            if abs(target_change_pct) >= self.SIGNIFICANT_TARGET_CHANGE:
                direction = "raised" if target_change_pct > 0 else "cut"
                alerts.append(RatingAlert(
                    ticker=ticker,
                    alert_type="TARGET_CHANGE",
                    severity="medium",
                    message=f"Average price target {direction} {abs(target_change_pct)*100:.0f}% (${prev_target:.0f} → ${consensus.target_mean:.0f})",
                    details={
                        "old_target": prev_target,
                        "new_target": consensus.target_mean,
                        "change_pct": target_change_pct
                    },
                    timestamp=now.isoformat()
                ))
        
        # Alert: Large upside
        if consensus.upside_pct >= self.LARGE_UPSIDE_THRESHOLD:
            alerts.append(RatingAlert(
                ticker=ticker,
                alert_type="UPSIDE_POTENTIAL",
                severity="low",
                message=f"Large upside potential: {consensus.upside_pct*100:.0f}% to target ${consensus.target_mean:.0f}",
                details={
                    "current_price": consensus.current_price,
                    "target_mean": consensus.target_mean,
                    "upside_pct": consensus.upside_pct
                },
                timestamp=now.isoformat()
            ))
        
        # Alert: Recent upgrade/downgrade activity
        if consensus.recent_upgrades >= 3:
            alerts.append(RatingAlert(
                ticker=ticker,
                alert_type="UPGRADE_CLUSTER",
                severity="medium",
                message=f"Multiple recent upgrades: {consensus.recent_upgrades} in past 30 days",
                details={
                    "upgrades": consensus.recent_upgrades,
                    "downgrades": consensus.recent_downgrades
                },
                timestamp=now.isoformat()
            ))
        elif consensus.recent_downgrades >= 3:
            alerts.append(RatingAlert(
                ticker=ticker,
                alert_type="DOWNGRADE_CLUSTER",
                severity="high",
                message=f"Multiple recent downgrades: {consensus.recent_downgrades} in past 30 days",
                details={
                    "upgrades": consensus.recent_upgrades,
                    "downgrades": consensus.recent_downgrades
                },
                timestamp=now.isoformat()
            ))
        
        # Update cache
        if "historical_ratings" not in self.cache:
            self.cache["historical_ratings"] = {}
        self.cache["historical_ratings"][ticker] = {
            "consensus_score": consensus.consensus_score,
            "target_mean": consensus.target_mean,
            "timestamp": now.isoformat()
        }
        
        return consensus, alerts
    
    def scan_watchlist(self, tickers: List[str], verbose: bool = True) -> Tuple[List[ConsensusRating], List[RatingAlert]]:
        """Scan multiple tickers"""
        all_ratings = []
        all_alerts = []
        
        for i, ticker in enumerate(tickers, 1):
            if verbose:
                print(f"📊 Scanning {ticker} ({i}/{len(tickers)})...")
            
            try:
                consensus, alerts = self.analyze_ticker(ticker, verbose=verbose)
                
                if consensus:
                    all_ratings.append(consensus)
                    all_alerts.extend(alerts)
                    
                    if verbose and alerts:
                        print(f"  ⚠️ {len(alerts)} alert(s)")
                        
            except Exception as e:
                if verbose:
                    print(f"  ❌ Error: {e}")
        
        # Sort alerts by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_alerts.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        # Save
        self._save_cache()
        self._save_alerts(all_alerts)
        
        return all_ratings, all_alerts
    
    def get_best_rated(self, tickers: List[str], top_n: int = 10) -> List[ConsensusRating]:
        """Get best rated stocks from watchlist"""
        ratings = []
        
        for ticker in tickers:
            consensus = self.get_consensus(ticker)
            if consensus and consensus.num_analysts > 0:
                ratings.append(consensus)
        
        # Sort by consensus score descending
        ratings.sort(key=lambda x: x.consensus_score, reverse=True)
        return ratings[:top_n]
    
    def get_biggest_upside(self, tickers: List[str], top_n: int = 10) -> List[ConsensusRating]:
        """Get stocks with biggest upside to targets"""
        ratings = []
        
        for ticker in tickers:
            consensus = self.get_consensus(ticker)
            if consensus and consensus.upside_pct != 0:
                ratings.append(consensus)
        
        # Sort by upside descending
        ratings.sort(key=lambda x: x.upside_pct, reverse=True)
        return ratings[:top_n]
    
    def format_consensus(self, c: ConsensusRating) -> str:
        """Format consensus for display"""
        rating_emoji = {
            "Strong Buy": "🟢",
            "Buy": "🟢",
            "Hold": "🟡",
            "Sell": "🔴",
            "Strong Sell": "🔴"
        }.get(c.consensus_rating, "⚪")
        
        upside_emoji = "📈" if c.upside_pct > 0 else "📉"
        
        lines = [
            f"{rating_emoji} {c.ticker} ({c.name}) - {c.consensus_rating}",
            f"   📊 Score: {c.consensus_score:.1f}/5 | Analysts: {c.num_analysts}",
            f"   💵 Price: ${c.current_price:.2f} | Target: ${c.target_mean:.2f} {upside_emoji} {c.upside_pct*100:+.1f}%",
            f"   🎯 Range: ${c.target_low:.2f} - ${c.target_high:.2f}"
        ]
        
        if c.recent_upgrades or c.recent_downgrades:
            lines.append(f"   📈 Upgrades: {c.recent_upgrades} | 📉 Downgrades: {c.recent_downgrades}")
        
        return "\n".join(lines)
    
    def format_alert(self, alert: RatingAlert) -> str:
        """Format alert for display"""
        emoji = {
            "CONSENSUS_SHIFT": "🔄",
            "TARGET_CHANGE": "🎯",
            "UPSIDE_POTENTIAL": "📈",
            "UPGRADE_CLUSTER": "📈",
            "DOWNGRADE_CLUSTER": "📉"
        }.get(alert.alert_type, "🔔")
        
        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(alert.severity, "⚪")
        
        return f"{emoji} {severity_emoji} [{alert.ticker}] {alert.message}"


# Default watchlist
DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "BAC", "GS", "JNJ", "PFE", "UNH",
    "DIS", "NFLX", "CRM", "ADBE", "AMD", "INTC"
]


if __name__ == "__main__":
    tracker = AnalystTracker()
    
    print("=" * 60)
    print("📊 ANALYST RATING MONITOR")
    print("=" * 60)
    
    test_tickers = ["AAPL", "NVDA", "TSLA"]
    
    ratings, alerts = tracker.scan_watchlist(test_tickers)
    
    print("\n" + "=" * 60)
    print("📊 CONSENSUS RATINGS")
    print("=" * 60)
    
    for r in ratings:
        print()
        print(tracker.format_consensus(r))
    
    if alerts:
        print("\n" + "=" * 60)
        print("⚠️ ALERTS")
        print("=" * 60)
        
        for alert in alerts:
            print(tracker.format_alert(alert))
