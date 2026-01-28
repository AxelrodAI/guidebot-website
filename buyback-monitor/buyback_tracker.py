#!/usr/bin/env python3
"""
Buyback & Share Count Monitor

Track corporate share repurchase programs, dilution, and execution rates.
"""

import sys
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List
import random

# Windows Unicode fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class BuybackProgram:
    """A share repurchase program"""
    ticker: str
    announcement_date: str
    authorized_amount: float  # $ authorized
    remaining_amount: float  # $ remaining
    shares_authorized: Optional[int]  # shares if specified
    expiration_date: Optional[str]
    program_type: str  # "10b-18", "ASR", "open_market"
    status: str  # "active", "completed", "expired"


@dataclass
class ShareCountChange:
    """Quarter-over-quarter share count change"""
    ticker: str
    quarter: str
    basic_shares: int
    diluted_shares: int
    prev_basic: int
    prev_diluted: int
    change_basic: int
    change_diluted: int
    change_pct: float
    source: str  # "buyback", "dilution", "issuance"


@dataclass
class BuybackExecution:
    """Execution of a buyback program"""
    ticker: str
    period: str
    shares_repurchased: int
    amount_spent: float
    avg_price: float
    program_utilization: float  # % of authorized used


@dataclass
class InsiderActivity:
    """Insider selling during buyback window"""
    ticker: str
    insider_name: str
    insider_role: str
    transaction_date: str
    transaction_type: str  # "sell", "buy"
    shares: int
    price: float
    during_buyback: bool


@dataclass
class BuybackAlert:
    """Alert for buyback activity"""
    ticker: str
    alert_type: str
    severity: str  # "high", "medium", "low"
    message: str
    timestamp: str
    data: dict


@dataclass
class CompanyBuybackProfile:
    """Full buyback profile for a company"""
    ticker: str
    company_name: str
    current_price: float
    market_cap: float
    shares_outstanding: int
    
    # Buyback programs
    active_programs: List[BuybackProgram]
    historical_programs: List[BuybackProgram]
    
    # Execution metrics
    total_authorized: float
    total_executed: float
    execution_rate: float  # % executed of authorized
    
    # Share count trends
    share_changes: List[ShareCountChange]
    net_share_change_1y: float  # % change in shares over 1 year
    
    # Yield metrics
    buyback_yield: float  # Annual buyback $ / market cap
    total_yield: float  # Dividend + buyback yield
    
    # Execution history
    executions: List[BuybackExecution]
    avg_execution_price: float
    current_price_vs_avg: float  # % difference
    
    # Insider activity
    insider_activity: List[InsiderActivity]
    insider_selling_during_buyback: bool
    
    # Alerts
    alerts: List[BuybackAlert]
    
    # Scores
    execution_score: float  # 0-100, how well they execute
    timing_score: float  # 0-100, do they buy low?
    credibility_score: float  # 0-100, overall track record


# Sample data generators
def generate_sample_profile(ticker: str) -> CompanyBuybackProfile:
    """Generate sample buyback profile for testing"""
    
    # Random company characteristics
    price = random.uniform(50, 500)
    shares = random.randint(100_000_000, 2_000_000_000)
    market_cap = price * shares
    
    # Generate buyback programs
    active_programs = []
    if random.random() > 0.3:
        authorized = random.uniform(1e9, 20e9)
        remaining = authorized * random.uniform(0.2, 0.8)
        active_programs.append(BuybackProgram(
            ticker=ticker,
            announcement_date=(datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
            authorized_amount=authorized,
            remaining_amount=remaining,
            shares_authorized=int(authorized / price),
            expiration_date=(datetime.now() + timedelta(days=random.randint(180, 730))).strftime('%Y-%m-%d'),
            program_type=random.choice(["10b-18", "ASR", "open_market"]),
            status="active"
        ))
    
    # Historical programs
    historical_programs = []
    for i in range(random.randint(0, 3)):
        auth = random.uniform(500e6, 10e9)
        historical_programs.append(BuybackProgram(
            ticker=ticker,
            announcement_date=(datetime.now() - timedelta(days=random.randint(400, 1500))).strftime('%Y-%m-%d'),
            authorized_amount=auth,
            remaining_amount=0,
            shares_authorized=int(auth / (price * random.uniform(0.6, 1.4))),
            expiration_date=(datetime.now() - timedelta(days=random.randint(30, 300))).strftime('%Y-%m-%d'),
            program_type=random.choice(["10b-18", "ASR", "open_market"]),
            status=random.choice(["completed", "expired"])
        ))
    
    # Execution metrics
    total_auth = sum(p.authorized_amount for p in active_programs + historical_programs)
    execution_rate = random.uniform(0.3, 0.95)
    total_executed = total_auth * execution_rate
    
    # Share count changes
    share_changes = []
    current_shares = shares
    for i in range(4):  # Last 4 quarters
        quarter = f"Q{4-i} {2025 if i < 2 else 2024}"
        change_pct = random.uniform(-0.03, 0.02)  # -3% to +2%
        prev_shares = int(current_shares / (1 + change_pct))
        change = current_shares - prev_shares
        
        share_changes.append(ShareCountChange(
            ticker=ticker,
            quarter=quarter,
            basic_shares=current_shares,
            diluted_shares=int(current_shares * 1.02),
            prev_basic=prev_shares,
            prev_diluted=int(prev_shares * 1.02),
            change_basic=change,
            change_diluted=int(change * 1.02),
            change_pct=change_pct * 100,
            source="buyback" if change < 0 else random.choice(["dilution", "issuance"])
        ))
        current_shares = prev_shares
    
    # Calculate net change
    net_change_1y = (shares - share_changes[-1].prev_basic) / share_changes[-1].prev_basic * 100
    
    # Executions
    executions = []
    for i in range(random.randint(2, 6)):
        quarter = f"Q{random.randint(1, 4)} {random.choice([2024, 2025])}"
        amount = random.uniform(100e6, 2e9)
        exec_price = price * random.uniform(0.8, 1.2)
        executions.append(BuybackExecution(
            ticker=ticker,
            period=quarter,
            shares_repurchased=int(amount / exec_price),
            amount_spent=amount,
            avg_price=exec_price,
            program_utilization=random.uniform(0.1, 0.4)
        ))
    
    avg_exec_price = sum(e.avg_price * e.amount_spent for e in executions) / max(1, sum(e.amount_spent for e in executions))
    
    # Buyback yield
    annual_buyback = sum(e.amount_spent for e in executions if '2025' in e.period)
    buyback_yield = (annual_buyback / market_cap) * 100 if market_cap > 0 else 0
    dividend_yield = random.uniform(0, 3)
    
    # Insider activity
    insider_activity = []
    insider_selling = False
    if random.random() > 0.6:
        for _ in range(random.randint(1, 3)):
            is_sell = random.random() > 0.3
            during_buyback = active_programs and random.random() > 0.5
            if is_sell and during_buyback:
                insider_selling = True
            
            insider_activity.append(InsiderActivity(
                ticker=ticker,
                insider_name=random.choice(["John Smith", "Jane Doe", "Bob Johnson", "Mary Williams"]),
                insider_role=random.choice(["CEO", "CFO", "Director", "VP"]),
                transaction_date=(datetime.now() - timedelta(days=random.randint(1, 90))).strftime('%Y-%m-%d'),
                transaction_type="sell" if is_sell else "buy",
                shares=random.randint(1000, 100000),
                price=price * random.uniform(0.95, 1.05),
                during_buyback=during_buyback
            ))
    
    # Scores
    execution_score = min(100, execution_rate * 100 + random.uniform(-10, 10))
    timing_score = 100 - abs(price - avg_exec_price) / price * 100 + random.uniform(-10, 10)
    timing_score = max(0, min(100, timing_score))
    credibility_score = (execution_score + timing_score) / 2
    
    # Generate alerts
    alerts = []
    
    # New authorization alert
    if active_programs:
        for prog in active_programs:
            days_since = (datetime.now() - datetime.strptime(prog.announcement_date, '%Y-%m-%d')).days
            if days_since < 30:
                alerts.append(BuybackAlert(
                    ticker=ticker,
                    alert_type="NEW_AUTHORIZATION",
                    severity="medium",
                    message=f"New ${prog.authorized_amount/1e9:.1f}B buyback program announced",
                    timestamp=prog.announcement_date,
                    data={"amount": prog.authorized_amount, "type": prog.program_type}
                ))
    
    # Low execution rate
    if execution_rate < 0.5:
        alerts.append(BuybackAlert(
            ticker=ticker,
            alert_type="LOW_EXECUTION",
            severity="medium",
            message=f"Buyback execution rate only {execution_rate:.0%} of authorized",
            timestamp=datetime.now().strftime('%Y-%m-%d'),
            data={"execution_rate": execution_rate}
        ))
    
    # Insider selling during buyback
    if insider_selling:
        alerts.append(BuybackAlert(
            ticker=ticker,
            alert_type="INSIDER_SELLING_DURING_BUYBACK",
            severity="high",
            message="Insiders selling while company buys back shares",
            timestamp=datetime.now().strftime('%Y-%m-%d'),
            data={"insider_activity": len([i for i in insider_activity if i.during_buyback and i.transaction_type == 'sell'])}
        ))
    
    # High buyback yield
    if buyback_yield > 5:
        alerts.append(BuybackAlert(
            ticker=ticker,
            alert_type="HIGH_BUYBACK_YIELD",
            severity="low",
            message=f"Attractive buyback yield of {buyback_yield:.1f}%",
            timestamp=datetime.now().strftime('%Y-%m-%d'),
            data={"buyback_yield": buyback_yield}
        ))
    
    # Share count increase (dilution)
    if net_change_1y > 2:
        alerts.append(BuybackAlert(
            ticker=ticker,
            alert_type="NET_DILUTION",
            severity="high",
            message=f"Net share count increased {net_change_1y:.1f}% despite buybacks",
            timestamp=datetime.now().strftime('%Y-%m-%d'),
            data={"net_change": net_change_1y}
        ))
    
    # Poor timing
    if timing_score < 40:
        alerts.append(BuybackAlert(
            ticker=ticker,
            alert_type="POOR_TIMING",
            severity="medium",
            message=f"Company consistently buys back shares at elevated prices",
            timestamp=datetime.now().strftime('%Y-%m-%d'),
            data={"timing_score": timing_score, "current_vs_avg": (price - avg_exec_price) / avg_exec_price * 100}
        ))
    
    return CompanyBuybackProfile(
        ticker=ticker.upper(),
        company_name=f"{ticker.upper()} Corp",
        current_price=round(price, 2),
        market_cap=round(market_cap, 0),
        shares_outstanding=shares,
        active_programs=active_programs,
        historical_programs=historical_programs,
        total_authorized=total_auth,
        total_executed=total_executed,
        execution_rate=round(execution_rate, 3),
        share_changes=share_changes,
        net_share_change_1y=round(net_change_1y, 2),
        buyback_yield=round(buyback_yield, 2),
        total_yield=round(buyback_yield + dividend_yield, 2),
        executions=executions,
        avg_execution_price=round(avg_exec_price, 2),
        current_price_vs_avg=round((price - avg_exec_price) / avg_exec_price * 100, 2),
        insider_activity=insider_activity,
        insider_selling_during_buyback=insider_selling,
        alerts=alerts,
        execution_score=round(execution_score, 1),
        timing_score=round(timing_score, 1),
        credibility_score=round(credibility_score, 1)
    )


class BuybackMonitor:
    """Monitor for buyback activity"""
    
    def __init__(self):
        self.profiles = {}  # ticker -> profile
        self.watchlist = set()
    
    def analyze(self, ticker: str) -> CompanyBuybackProfile:
        """Analyze buyback activity for a ticker"""
        profile = generate_sample_profile(ticker)
        self.profiles[ticker.upper()] = profile
        return profile
    
    def add_to_watchlist(self, ticker: str):
        """Add ticker to watchlist"""
        self.watchlist.add(ticker.upper())
        if ticker.upper() not in self.profiles:
            self.analyze(ticker)
    
    def remove_from_watchlist(self, ticker: str):
        """Remove ticker from watchlist"""
        self.watchlist.discard(ticker.upper())
    
    def get_watchlist_alerts(self) -> List[BuybackAlert]:
        """Get all alerts for watchlist"""
        alerts = []
        for ticker in self.watchlist:
            if ticker in self.profiles:
                alerts.extend(self.profiles[ticker].alerts)
        return sorted(alerts, key=lambda a: a.severity == 'high', reverse=True)
    
    def scan_for_opportunities(self, min_yield: float = 3.0) -> List[dict]:
        """Scan for high buyback yield opportunities"""
        opportunities = []
        
        # Analyze a set of sample tickers
        sample_tickers = ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'JPM', 'BAC', 'WFC', 
                         'XOM', 'CVX', 'HD', 'LOW', 'TGT', 'WMT', 'COST']
        
        for ticker in sample_tickers:
            if ticker not in self.profiles:
                self.analyze(ticker)
            
            profile = self.profiles[ticker]
            
            if profile.buyback_yield >= min_yield and profile.execution_score >= 60:
                opportunities.append({
                    'ticker': ticker,
                    'buyback_yield': profile.buyback_yield,
                    'total_yield': profile.total_yield,
                    'execution_score': profile.execution_score,
                    'net_share_change': profile.net_share_change_1y,
                    'active_program': len(profile.active_programs) > 0
                })
        
        return sorted(opportunities, key=lambda x: x['buyback_yield'], reverse=True)
    
    def get_worst_executors(self) -> List[dict]:
        """Find companies with poor buyback execution"""
        poor_executors = []
        
        for ticker, profile in self.profiles.items():
            if profile.execution_rate < 0.5 or profile.net_share_change_1y > 2:
                poor_executors.append({
                    'ticker': ticker,
                    'execution_rate': profile.execution_rate,
                    'net_share_change': profile.net_share_change_1y,
                    'credibility_score': profile.credibility_score,
                    'insider_selling': profile.insider_selling_during_buyback
                })
        
        return sorted(poor_executors, key=lambda x: x['execution_rate'])
    
    def compare_yields(self) -> List[dict]:
        """Compare buyback yields across tracked companies"""
        yields = []
        
        for ticker, profile in self.profiles.items():
            yields.append({
                'ticker': ticker,
                'buyback_yield': profile.buyback_yield,
                'total_yield': profile.total_yield,
                'execution_score': profile.execution_score,
                'market_cap_b': profile.market_cap / 1e9
            })
        
        return sorted(yields, key=lambda x: x['buyback_yield'], reverse=True)


# Singleton
_monitor = None

def get_monitor() -> BuybackMonitor:
    """Get or create monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = BuybackMonitor()
    return _monitor
