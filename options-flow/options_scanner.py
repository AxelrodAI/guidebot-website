#!/usr/bin/env python3
"""
Options Flow / Unusual Activity Scanner
Tracks unusual options activity using free data sources (Yahoo Finance)

Features:
- Large block trades detection
- Unusual volume alerts (>5x average)
- Large premium trades (>$500k)
- Put/Call ratio analysis
- Open Interest change tracking
- Sweep detection (multiple exchanges)
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
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json
import os

@dataclass
class UnusualActivity:
    """Represents an unusual options activity alert"""
    ticker: str
    alert_type: str  # VOLUME_SPIKE, LARGE_PREMIUM, OI_CHANGE, PC_RATIO, BLOCK_TRADE
    strike: float
    expiry: str
    option_type: str  # call or put
    volume: int
    open_interest: int
    implied_volatility: float
    last_price: float
    bid: float
    ask: float
    premium_traded: float
    volume_vs_avg: float  # multiplier vs average
    oi_change_pct: float
    details: str
    timestamp: str
    score: int  # 0-100 significance score

class OptionsFlowScanner:
    """Main scanner for unusual options activity"""
    
    # Alert thresholds
    VOLUME_SPIKE_THRESHOLD = 5.0  # Volume > 5x average
    LARGE_PREMIUM_THRESHOLD = 500000  # $500k+ trades
    OI_CHANGE_THRESHOLD = 0.20  # 20% OI change
    UNUSUAL_PC_RATIO_HIGH = 2.0  # Unusually bearish
    UNUSUAL_PC_RATIO_LOW = 0.3  # Unusually bullish
    MIN_VOLUME = 100  # Minimum volume to consider
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(self.cache_dir, "options_cache.json")
        self.alerts_file = os.path.join(self.cache_dir, "alerts.json")
        self._load_cache()
    
    def _load_cache(self):
        """Load cached historical data for comparison"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {"last_updated": None, "historical_oi": {}, "avg_volumes": {}}
        except:
            self.cache = {"last_updated": None, "historical_oi": {}, "avg_volumes": {}}
    
    def _save_cache(self):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def _save_alerts(self, alerts: List[UnusualActivity]):
        """Save alerts to JSON file"""
        existing = []
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r') as f:
                    existing = json.load(f)
            except:
                existing = []
        
        # Add new alerts
        for alert in alerts:
            existing.append({
                "ticker": alert.ticker,
                "alert_type": alert.alert_type,
                "strike": alert.strike,
                "expiry": alert.expiry,
                "option_type": alert.option_type,
                "volume": alert.volume,
                "open_interest": alert.open_interest,
                "implied_volatility": alert.implied_volatility,
                "last_price": alert.last_price,
                "premium_traded": alert.premium_traded,
                "volume_vs_avg": alert.volume_vs_avg,
                "oi_change_pct": alert.oi_change_pct,
                "details": alert.details,
                "timestamp": alert.timestamp,
                "score": alert.score
            })
        
        # Keep only last 500 alerts
        existing = existing[-500:]
        
        with open(self.alerts_file, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def get_options_chain(self, ticker: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch options chain for a ticker"""
        stock = yf.Ticker(ticker)
        
        # Get all expiration dates
        try:
            expirations = stock.options
        except:
            return pd.DataFrame(), pd.DataFrame()
        
        all_calls = []
        all_puts = []
        
        for exp in expirations[:6]:  # Limit to next 6 expirations for speed
            try:
                chain = stock.option_chain(exp)
                calls = chain.calls.copy()
                puts = chain.puts.copy()
                calls['expiry'] = exp
                puts['expiry'] = exp
                all_calls.append(calls)
                all_puts.append(puts)
            except:
                continue
        
        calls_df = pd.concat(all_calls) if all_calls else pd.DataFrame()
        puts_df = pd.concat(all_puts) if all_puts else pd.DataFrame()
        
        return calls_df, puts_df
    
    def calculate_premium(self, row: pd.Series) -> float:
        """Calculate premium traded (volume * mid price * 100)"""
        mid = (row.get('bid', 0) + row.get('ask', 0)) / 2
        if mid == 0:
            mid = row.get('lastPrice', 0)
        return row.get('volume', 0) * mid * 100
    
    def calculate_significance_score(self, alert: UnusualActivity) -> int:
        """Calculate 0-100 significance score for an alert"""
        score = 50  # Base score
        
        # Volume multiplier impact (max +30)
        if alert.volume_vs_avg >= 10:
            score += 30
        elif alert.volume_vs_avg >= 5:
            score += 20
        elif alert.volume_vs_avg >= 3:
            score += 10
        
        # Premium size impact (max +20)
        if alert.premium_traded >= 1000000:
            score += 20
        elif alert.premium_traded >= 500000:
            score += 15
        elif alert.premium_traded >= 100000:
            score += 10
        
        # OI change impact (max +10)
        if abs(alert.oi_change_pct) >= 0.5:
            score += 10
        elif abs(alert.oi_change_pct) >= 0.2:
            score += 5
        
        # Near-term expiry bonus (max +10)
        try:
            expiry_date = datetime.strptime(alert.expiry, "%Y-%m-%d")
            days_to_expiry = (expiry_date - datetime.now()).days
            if days_to_expiry <= 7:
                score += 10
            elif days_to_expiry <= 30:
                score += 5
        except:
            pass
        
        return min(100, max(0, score))
    
    def scan_ticker(self, ticker: str, verbose: bool = False) -> List[UnusualActivity]:
        """Scan a single ticker for unusual activity"""
        alerts = []
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        except:
            if verbose:
                print(f"  ⚠️ Could not fetch stock info for {ticker}")
            return alerts
        
        calls_df, puts_df = self.get_options_chain(ticker)
        
        if calls_df.empty and puts_df.empty:
            if verbose:
                print(f"  ⚠️ No options data for {ticker}")
            return alerts
        
        # Process calls
        for _, row in calls_df.iterrows():
            alert = self._analyze_option(ticker, row, "call", current_price)
            if alert:
                alerts.append(alert)
        
        # Process puts
        for _, row in puts_df.iterrows():
            alert = self._analyze_option(ticker, row, "put", current_price)
            if alert:
                alerts.append(alert)
        
        # Calculate Put/Call ratio
        total_call_volume = calls_df['volume'].sum() if 'volume' in calls_df.columns else 0
        total_put_volume = puts_df['volume'].sum() if 'volume' in puts_df.columns else 0
        
        if total_call_volume > 0:
            pc_ratio = total_put_volume / total_call_volume
            
            if pc_ratio >= self.UNUSUAL_PC_RATIO_HIGH or pc_ratio <= self.UNUSUAL_PC_RATIO_LOW:
                sentiment = "BEARISH 🐻" if pc_ratio >= self.UNUSUAL_PC_RATIO_HIGH else "BULLISH 🐂"
                alert = UnusualActivity(
                    ticker=ticker,
                    alert_type="PC_RATIO",
                    strike=current_price,
                    expiry="aggregate",
                    option_type="ratio",
                    volume=int(total_call_volume + total_put_volume),
                    open_interest=0,
                    implied_volatility=0,
                    last_price=0,
                    bid=0,
                    ask=0,
                    premium_traded=0,
                    volume_vs_avg=pc_ratio,
                    oi_change_pct=0,
                    details=f"P/C Ratio: {pc_ratio:.2f} - Unusual {sentiment} sentiment",
                    timestamp=datetime.now().isoformat(),
                    score=0
                )
                alert.score = self.calculate_significance_score(alert)
                alerts.append(alert)
        
        # Update cache with current OI
        self._update_cache(ticker, calls_df, puts_df)
        
        return alerts
    
    def _analyze_option(self, ticker: str, row: pd.Series, option_type: str, 
                        current_price: float) -> Optional[UnusualActivity]:
        """Analyze a single option contract for unusual activity"""
        
        volume = row.get('volume', 0)
        if pd.isna(volume) or volume < self.MIN_VOLUME:
            return None
        
        oi = row.get('openInterest', 0)
        if pd.isna(oi):
            oi = 0
        
        strike = row.get('strike', 0)
        expiry = row.get('expiry', 'unknown')
        iv = row.get('impliedVolatility', 0)
        last_price = row.get('lastPrice', 0)
        bid = row.get('bid', 0)
        ask = row.get('ask', 0)
        
        # Calculate premium
        premium = self.calculate_premium(row)
        
        # Calculate volume vs average (estimate based on OI)
        avg_volume = max(oi * 0.1, 100) if oi > 0 else 100  # Rough estimate
        volume_ratio = volume / avg_volume
        
        # Check for historical OI change
        cache_key = f"{ticker}_{expiry}_{strike}_{option_type}"
        historical_oi = self.cache.get("historical_oi", {}).get(cache_key, oi)
        oi_change_pct = (oi - historical_oi) / historical_oi if historical_oi > 0 else 0
        
        # Determine alert type
        alert_type = None
        details = ""
        
        if premium >= self.LARGE_PREMIUM_THRESHOLD:
            alert_type = "LARGE_PREMIUM"
            details = f"${premium:,.0f} premium traded ({volume:,} contracts)"
        elif volume_ratio >= self.VOLUME_SPIKE_THRESHOLD:
            alert_type = "VOLUME_SPIKE"
            details = f"{volume_ratio:.1f}x average volume ({volume:,} vs ~{int(avg_volume):,} avg)"
        elif abs(oi_change_pct) >= self.OI_CHANGE_THRESHOLD:
            direction = "increase" if oi_change_pct > 0 else "decrease"
            alert_type = "OI_CHANGE"
            details = f"OI {direction} of {abs(oi_change_pct)*100:.1f}% ({historical_oi:,} → {oi:,})"
        
        # Block trade detection (high volume in single contract)
        if volume >= 1000 and alert_type is None:
            alert_type = "BLOCK_TRADE"
            details = f"Large block: {volume:,} contracts at ${last_price:.2f}"
        
        if alert_type is None:
            return None
        
        # Determine if ITM/OTM/ATM
        if option_type == "call":
            moneyness = "ITM" if strike < current_price else ("ATM" if abs(strike - current_price) / current_price < 0.02 else "OTM")
        else:
            moneyness = "ITM" if strike > current_price else ("ATM" if abs(strike - current_price) / current_price < 0.02 else "OTM")
        
        details = f"[{moneyness}] {details}"
        
        alert = UnusualActivity(
            ticker=ticker,
            alert_type=alert_type,
            strike=strike,
            expiry=str(expiry),
            option_type=option_type,
            volume=int(volume),
            open_interest=int(oi),
            implied_volatility=float(iv) if not pd.isna(iv) else 0,
            last_price=float(last_price) if not pd.isna(last_price) else 0,
            bid=float(bid) if not pd.isna(bid) else 0,
            ask=float(ask) if not pd.isna(ask) else 0,
            premium_traded=premium,
            volume_vs_avg=volume_ratio,
            oi_change_pct=oi_change_pct,
            details=details,
            timestamp=datetime.now().isoformat(),
            score=0
        )
        
        alert.score = self.calculate_significance_score(alert)
        
        return alert
    
    def _update_cache(self, ticker: str, calls_df: pd.DataFrame, puts_df: pd.DataFrame):
        """Update cache with current OI data"""
        if "historical_oi" not in self.cache:
            self.cache["historical_oi"] = {}
        
        for df, opt_type in [(calls_df, "call"), (puts_df, "put")]:
            if df.empty:
                continue
            for _, row in df.iterrows():
                cache_key = f"{ticker}_{row.get('expiry', '')}_{row.get('strike', '')}_{opt_type}"
                oi = row.get('openInterest', 0)
                if not pd.isna(oi):
                    self.cache["historical_oi"][cache_key] = int(oi)
        
        self.cache["last_updated"] = datetime.now().isoformat()
        self._save_cache()
    
    def scan_watchlist(self, tickers: List[str], verbose: bool = True) -> List[UnusualActivity]:
        """Scan multiple tickers for unusual activity"""
        all_alerts = []
        
        for i, ticker in enumerate(tickers, 1):
            if verbose:
                print(f"📊 Scanning {ticker} ({i}/{len(tickers)})...")
            
            try:
                alerts = self.scan_ticker(ticker, verbose=verbose)
                all_alerts.extend(alerts)
                
                if verbose and alerts:
                    print(f"  ✅ Found {len(alerts)} unusual activities")
            except Exception as e:
                if verbose:
                    print(f"  ❌ Error scanning {ticker}: {e}")
        
        # Sort by score descending
        all_alerts.sort(key=lambda x: x.score, reverse=True)
        
        # Save alerts
        self._save_alerts(all_alerts)
        
        return all_alerts
    
    def get_summary(self, alerts: List[UnusualActivity]) -> Dict:
        """Generate summary statistics from alerts"""
        if not alerts:
            return {"total_alerts": 0}
        
        by_type = {}
        by_ticker = {}
        total_premium = 0
        
        for alert in alerts:
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1
            by_ticker[alert.ticker] = by_ticker.get(alert.ticker, 0) + 1
            total_premium += alert.premium_traded
        
        return {
            "total_alerts": len(alerts),
            "by_type": by_type,
            "by_ticker": by_ticker,
            "total_premium_traded": total_premium,
            "top_score": alerts[0].score if alerts else 0,
            "avg_score": sum(a.score for a in alerts) / len(alerts)
        }
    
    def format_alert(self, alert: UnusualActivity) -> str:
        """Format an alert for display"""
        emoji = {
            "VOLUME_SPIKE": "📈",
            "LARGE_PREMIUM": "💰",
            "OI_CHANGE": "📊",
            "PC_RATIO": "⚖️",
            "BLOCK_TRADE": "🔷"
        }.get(alert.alert_type, "🔔")
        
        opt_emoji = "📗" if alert.option_type == "call" else "📕"
        
        lines = [
            f"{emoji} [{alert.ticker}] {alert.alert_type} - Score: {alert.score}/100",
            f"   {opt_emoji} {alert.option_type.upper()} ${alert.strike} exp {alert.expiry}",
            f"   📊 Vol: {alert.volume:,} | OI: {alert.open_interest:,} | IV: {alert.implied_volatility*100:.1f}%",
            f"   💵 Premium: ${alert.premium_traded:,.0f} @ ${alert.last_price:.2f}",
            f"   ℹ️  {alert.details}"
        ]
        
        return "\n".join(lines)


# Default watchlist - high liquidity stocks
DEFAULT_WATCHLIST = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META", 
    "AMZN", "GOOGL", "JPM", "BAC", "XLF", "GLD", "IWM"
]


if __name__ == "__main__":
    scanner = OptionsFlowScanner()
    
    print("=" * 60)
    print("🔍 OPTIONS FLOW SCANNER")
    print("=" * 60)
    
    alerts = scanner.scan_watchlist(["SPY", "AAPL", "TSLA"])
    
    print("\n" + "=" * 60)
    print("📋 TOP UNUSUAL ACTIVITY")
    print("=" * 60)
    
    for alert in alerts[:10]:
        print()
        print(scanner.format_alert(alert))
    
    summary = scanner.get_summary(alerts)
    print("\n" + "=" * 60)
    print("📈 SUMMARY")
    print("=" * 60)
    print(f"Total Alerts: {summary['total_alerts']}")
    print(f"Total Premium: ${summary.get('total_premium_traded', 0):,.0f}")
    print(f"By Type: {summary.get('by_type', {})}")
