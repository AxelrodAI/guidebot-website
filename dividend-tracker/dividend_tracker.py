#!/usr/bin/env python3
"""
Dividend Calendar + Yield Monitor
Track ex-dates, dividend changes, payout ratio warnings.

Features:
- Upcoming ex-date calendar
- Dividend change detection (cuts/increases)
- Yield anomaly alerts
- Payout ratio warnings
- Historical dividend analysis
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
class DividendInfo:
    """Dividend information for a stock"""
    ticker: str
    name: str
    current_price: float
    annual_dividend: float
    dividend_yield: float
    ex_date: Optional[str]
    payment_date: Optional[str]
    payout_ratio: float
    dividend_growth_5y: float
    consecutive_years: int  # Years of consecutive dividend growth
    last_change_pct: float  # Last dividend change percentage
    last_change_type: str  # "increase", "decrease", "unchanged", "initiated"
    frequency: str  # "quarterly", "monthly", "annual", "irregular"
    timestamp: str

@dataclass
class DividendAlert:
    """Alert for dividend-related events"""
    ticker: str
    alert_type: str  # EX_DATE_UPCOMING, DIVIDEND_CUT, DIVIDEND_INCREASE, HIGH_YIELD, LOW_PAYOUT, HIGH_PAYOUT
    severity: str  # "info", "warning", "critical"
    message: str
    details: Dict
    timestamp: str

class DividendTracker:
    """Main tracker for dividend monitoring"""
    
    # Alert thresholds
    HIGH_YIELD_THRESHOLD = 0.06  # 6% yield - potentially unsustainable
    VERY_HIGH_YIELD_THRESHOLD = 0.10  # 10% yield - red flag
    HIGH_PAYOUT_THRESHOLD = 0.80  # 80% payout ratio - stress warning
    LOW_PAYOUT_THRESHOLD = 0.30  # 30% payout - room to grow
    DIVIDEND_CUT_THRESHOLD = -0.05  # 5% cut triggers alert
    DIVIDEND_INCREASE_THRESHOLD = 0.05  # 5% increase is notable
    EX_DATE_LOOKAHEAD_DAYS = 14  # Alert 2 weeks before ex-date
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(self.cache_dir, "dividend_cache.json")
        self.alerts_file = os.path.join(self.cache_dir, "dividend_alerts.json")
        self._load_cache()
    
    def _load_cache(self):
        """Load cached historical dividend data"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {"last_updated": None, "dividend_history": {}}
        except:
            self.cache = {"last_updated": None, "dividend_history": {}}
    
    def _save_cache(self):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2, default=str)
    
    def _save_alerts(self, alerts: List[DividendAlert]):
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
                "severity": alert.severity,
                "message": alert.message,
                "details": alert.details,
                "timestamp": alert.timestamp
            })
        
        # Keep only last 200 alerts
        existing = existing[-200:]
        
        with open(self.alerts_file, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def get_dividend_info(self, ticker: str) -> Optional[DividendInfo]:
        """Get comprehensive dividend information for a ticker"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Basic info
            name = info.get('shortName', info.get('longName', ticker))
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            
            # Dividend data
            annual_dividend = info.get('dividendRate', 0) or 0
            # Calculate yield ourselves (yfinance dividendYield is inconsistent)
            dividend_yield = annual_dividend / current_price if current_price > 0 else 0
            payout_ratio = info.get('payoutRatio', 0) or 0
            
            # Ex-date and payment date
            ex_date = None
            if 'exDividendDate' in info and info['exDividendDate']:
                try:
                    ex_date = datetime.fromtimestamp(info['exDividendDate']).strftime('%Y-%m-%d')
                except:
                    pass
            
            # Get dividend history for analysis
            try:
                dividends = stock.dividends
                if len(dividends) > 0:
                    dividend_history = dividends.tail(20).tolist()  # Last 20 dividends
                else:
                    dividend_history = []
            except:
                dividend_history = []
            
            # Calculate dividend change
            last_change_pct = 0.0
            last_change_type = "unchanged"
            if len(dividend_history) >= 2:
                prev = dividend_history[-2]
                curr = dividend_history[-1]
                if prev > 0:
                    last_change_pct = (curr - prev) / prev
                    if last_change_pct > 0.01:
                        last_change_type = "increase"
                    elif last_change_pct < -0.01:
                        last_change_type = "decrease"
            elif len(dividend_history) == 1:
                last_change_type = "initiated"
            
            # Estimate frequency
            frequency = "quarterly"
            if len(dividend_history) >= 4:
                # Rough estimate based on count per year
                try:
                    years_span = (dividends.index[-1] - dividends.index[0]).days / 365
                    if years_span > 0:
                        freq_estimate = len(dividends) / years_span
                        if freq_estimate >= 10:
                            frequency = "monthly"
                        elif freq_estimate >= 3:
                            frequency = "quarterly"
                        elif freq_estimate >= 1.5:
                            frequency = "semi-annual"
                        else:
                            frequency = "annual"
                except:
                    pass
            
            # Calculate 5-year dividend growth (simplified)
            dividend_growth_5y = 0.0
            if len(dividend_history) >= 8:
                old_avg = sum(dividend_history[:4]) / 4
                new_avg = sum(dividend_history[-4:]) / 4
                if old_avg > 0:
                    total_growth = (new_avg - old_avg) / old_avg
                    # Annualize roughly
                    dividend_growth_5y = total_growth / 3  # ~3 years between samples
            
            # Update cache with current dividend
            if ticker not in self.cache["dividend_history"]:
                self.cache["dividend_history"][ticker] = []
            if dividend_history:
                self.cache["dividend_history"][ticker] = dividend_history[-5:]
            
            return DividendInfo(
                ticker=ticker,
                name=name,
                current_price=current_price,
                annual_dividend=annual_dividend,
                dividend_yield=dividend_yield,
                ex_date=ex_date,
                payment_date=None,  # Not always available
                payout_ratio=payout_ratio,
                dividend_growth_5y=dividend_growth_5y,
                consecutive_years=0,  # Would need more data
                last_change_pct=last_change_pct,
                last_change_type=last_change_type,
                frequency=frequency,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"  ⚠️ Error fetching {ticker}: {e}")
            return None
    
    def analyze_ticker(self, ticker: str, verbose: bool = False) -> Tuple[Optional[DividendInfo], List[DividendAlert]]:
        """Analyze a ticker for dividend info and generate alerts"""
        alerts = []
        
        div_info = self.get_dividend_info(ticker)
        if div_info is None:
            return None, alerts
        
        # Check for no dividend
        if div_info.annual_dividend == 0:
            if verbose:
                print(f"  ℹ️ {ticker} does not pay a dividend")
            return div_info, alerts
        
        now = datetime.now()
        
        # Alert: Ex-date upcoming
        if div_info.ex_date:
            try:
                ex_dt = datetime.strptime(div_info.ex_date, '%Y-%m-%d')
                days_until = (ex_dt - now).days
                
                if 0 < days_until <= self.EX_DATE_LOOKAHEAD_DAYS:
                    alerts.append(DividendAlert(
                        ticker=ticker,
                        alert_type="EX_DATE_UPCOMING",
                        severity="info",
                        message=f"Ex-dividend date in {days_until} days ({div_info.ex_date})",
                        details={
                            "ex_date": div_info.ex_date,
                            "days_until": days_until,
                            "dividend_amount": div_info.annual_dividend / 4 if div_info.frequency == "quarterly" else div_info.annual_dividend,
                            "yield": div_info.dividend_yield
                        },
                        timestamp=now.isoformat()
                    ))
            except:
                pass
        
        # Alert: Dividend cut
        if div_info.last_change_type == "decrease" and div_info.last_change_pct <= self.DIVIDEND_CUT_THRESHOLD:
            alerts.append(DividendAlert(
                ticker=ticker,
                alert_type="DIVIDEND_CUT",
                severity="critical",
                message=f"Dividend cut of {abs(div_info.last_change_pct)*100:.1f}%",
                details={
                    "change_pct": div_info.last_change_pct,
                    "current_dividend": div_info.annual_dividend,
                    "yield": div_info.dividend_yield
                },
                timestamp=now.isoformat()
            ))
        
        # Alert: Dividend increase
        if div_info.last_change_type == "increase" and div_info.last_change_pct >= self.DIVIDEND_INCREASE_THRESHOLD:
            alerts.append(DividendAlert(
                ticker=ticker,
                alert_type="DIVIDEND_INCREASE",
                severity="info",
                message=f"Dividend increase of {div_info.last_change_pct*100:.1f}%",
                details={
                    "change_pct": div_info.last_change_pct,
                    "current_dividend": div_info.annual_dividend,
                    "yield": div_info.dividend_yield
                },
                timestamp=now.isoformat()
            ))
        
        # Alert: Very high yield (potential value trap)
        if div_info.dividend_yield >= self.VERY_HIGH_YIELD_THRESHOLD:
            alerts.append(DividendAlert(
                ticker=ticker,
                alert_type="HIGH_YIELD",
                severity="critical",
                message=f"Unusually high yield of {div_info.dividend_yield*100:.1f}% - potential value trap",
                details={
                    "yield": div_info.dividend_yield,
                    "payout_ratio": div_info.payout_ratio,
                    "price": div_info.current_price
                },
                timestamp=now.isoformat()
            ))
        elif div_info.dividend_yield >= self.HIGH_YIELD_THRESHOLD:
            alerts.append(DividendAlert(
                ticker=ticker,
                alert_type="HIGH_YIELD",
                severity="warning",
                message=f"High yield of {div_info.dividend_yield*100:.1f}% - verify sustainability",
                details={
                    "yield": div_info.dividend_yield,
                    "payout_ratio": div_info.payout_ratio,
                    "price": div_info.current_price
                },
                timestamp=now.isoformat()
            ))
        
        # Alert: High payout ratio
        if div_info.payout_ratio >= self.HIGH_PAYOUT_THRESHOLD:
            alerts.append(DividendAlert(
                ticker=ticker,
                alert_type="HIGH_PAYOUT",
                severity="warning",
                message=f"High payout ratio of {div_info.payout_ratio*100:.1f}% - limited safety margin",
                details={
                    "payout_ratio": div_info.payout_ratio,
                    "dividend": div_info.annual_dividend,
                    "yield": div_info.dividend_yield
                },
                timestamp=now.isoformat()
            ))
        
        # Alert: Very low payout (room to grow or not committed)
        if 0 < div_info.payout_ratio <= self.LOW_PAYOUT_THRESHOLD:
            alerts.append(DividendAlert(
                ticker=ticker,
                alert_type="LOW_PAYOUT",
                severity="info",
                message=f"Low payout ratio of {div_info.payout_ratio*100:.1f}% - room for dividend growth",
                details={
                    "payout_ratio": div_info.payout_ratio,
                    "dividend": div_info.annual_dividend,
                    "yield": div_info.dividend_yield
                },
                timestamp=now.isoformat()
            ))
        
        return div_info, alerts
    
    def scan_watchlist(self, tickers: List[str], verbose: bool = True) -> Tuple[List[DividendInfo], List[DividendAlert]]:
        """Scan multiple tickers for dividend information"""
        all_info = []
        all_alerts = []
        
        for i, ticker in enumerate(tickers, 1):
            if verbose:
                print(f"💰 Scanning {ticker} ({i}/{len(tickers)})...")
            
            try:
                div_info, alerts = self.analyze_ticker(ticker, verbose=verbose)
                
                if div_info:
                    all_info.append(div_info)
                    all_alerts.extend(alerts)
                    
                    if verbose and alerts:
                        print(f"  ⚠️ {len(alerts)} alert(s) generated")
                        
            except Exception as e:
                if verbose:
                    print(f"  ❌ Error scanning {ticker}: {e}")
        
        # Sort alerts by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        all_alerts.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        # Save cache and alerts
        self._save_cache()
        self._save_alerts(all_alerts)
        
        return all_info, all_alerts
    
    def get_upcoming_exdates(self, tickers: List[str], days_ahead: int = 30) -> List[Dict]:
        """Get calendar of upcoming ex-dividend dates"""
        calendar = []
        now = datetime.now()
        cutoff = now + timedelta(days=days_ahead)
        
        for ticker in tickers:
            div_info = self.get_dividend_info(ticker)
            if div_info and div_info.ex_date:
                try:
                    ex_dt = datetime.strptime(div_info.ex_date, '%Y-%m-%d')
                    if now <= ex_dt <= cutoff:
                        calendar.append({
                            "ticker": ticker,
                            "name": div_info.name,
                            "ex_date": div_info.ex_date,
                            "days_until": (ex_dt - now).days,
                            "yield": div_info.dividend_yield,
                            "amount_est": div_info.annual_dividend / 4 if div_info.frequency == "quarterly" else div_info.annual_dividend
                        })
                except:
                    pass
        
        # Sort by date
        calendar.sort(key=lambda x: x["ex_date"])
        return calendar
    
    def get_yield_rankings(self, tickers: List[str]) -> List[Dict]:
        """Rank tickers by dividend yield"""
        rankings = []
        
        for ticker in tickers:
            div_info = self.get_dividend_info(ticker)
            if div_info and div_info.dividend_yield > 0:
                rankings.append({
                    "ticker": ticker,
                    "name": div_info.name,
                    "yield": div_info.dividend_yield,
                    "payout_ratio": div_info.payout_ratio,
                    "annual_dividend": div_info.annual_dividend,
                    "last_change": div_info.last_change_type
                })
        
        # Sort by yield descending
        rankings.sort(key=lambda x: x["yield"], reverse=True)
        return rankings
    
    def format_dividend_info(self, div_info: DividendInfo) -> str:
        """Format dividend info for display"""
        if div_info.annual_dividend == 0:
            return f"💰 {div_info.ticker} ({div_info.name}): No dividend"
        
        yield_warning = "⚠️" if div_info.dividend_yield >= self.HIGH_YIELD_THRESHOLD else ""
        payout_warning = "⚠️" if div_info.payout_ratio >= self.HIGH_PAYOUT_THRESHOLD else ""
        
        change_emoji = {
            "increase": "📈",
            "decrease": "📉",
            "unchanged": "➡️",
            "initiated": "🆕"
        }.get(div_info.last_change_type, "")
        
        lines = [
            f"💰 {div_info.ticker} ({div_info.name})",
            f"   💵 Annual Div: ${div_info.annual_dividend:.2f} | Yield: {div_info.dividend_yield*100:.2f}% {yield_warning}",
            f"   📊 Payout Ratio: {div_info.payout_ratio*100:.1f}% {payout_warning} | Frequency: {div_info.frequency}",
            f"   {change_emoji} Last Change: {div_info.last_change_type} ({div_info.last_change_pct*100:+.1f}%)"
        ]
        
        if div_info.ex_date:
            lines.append(f"   📅 Next Ex-Date: {div_info.ex_date}")
        
        return "\n".join(lines)
    
    def format_alert(self, alert: DividendAlert) -> str:
        """Format alert for display"""
        emoji = {
            "EX_DATE_UPCOMING": "📅",
            "DIVIDEND_CUT": "🔻",
            "DIVIDEND_INCREASE": "📈",
            "HIGH_YIELD": "⚠️",
            "HIGH_PAYOUT": "⚠️",
            "LOW_PAYOUT": "💡"
        }.get(alert.alert_type, "🔔")
        
        severity_color = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🟢"
        }.get(alert.severity, "⚪")
        
        return f"{emoji} {severity_color} [{alert.ticker}] {alert.message}"


# Default dividend-focused watchlist
DEFAULT_DIVIDEND_WATCHLIST = [
    # Dividend Aristocrats / High Quality
    "JNJ", "PG", "KO", "PEP", "MMM", "ABT", "MCD", "WMT",
    # REITs
    "O", "VNQ", "SPG", "VICI",
    # Utilities
    "NEE", "DUK", "SO", "D",
    # High Yield
    "T", "VZ", "MO", "PM",
    # Dividend ETFs
    "VYM", "SCHD", "DVY", "SDY"
]


if __name__ == "__main__":
    tracker = DividendTracker()
    
    print("=" * 60)
    print("💰 DIVIDEND CALENDAR + YIELD MONITOR")
    print("=" * 60)
    
    # Scan a few tickers
    test_tickers = ["JNJ", "KO", "O", "T", "SCHD"]
    
    div_infos, alerts = tracker.scan_watchlist(test_tickers)
    
    print("\n" + "=" * 60)
    print("📊 DIVIDEND SUMMARY")
    print("=" * 60)
    
    for div_info in div_infos:
        print()
        print(tracker.format_dividend_info(div_info))
    
    if alerts:
        print("\n" + "=" * 60)
        print("⚠️ ALERTS")
        print("=" * 60)
        
        for alert in alerts:
            print(tracker.format_alert(alert))
    
    # Show upcoming calendar
    print("\n" + "=" * 60)
    print("📅 UPCOMING EX-DATES (30 days)")
    print("=" * 60)
    
    calendar = tracker.get_upcoming_exdates(test_tickers)
    for event in calendar:
        print(f"  {event['ex_date']} - {event['ticker']}: ${event['amount_est']:.2f} (Yield: {event['yield']*100:.2f}%)")
