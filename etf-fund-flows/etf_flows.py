"""
ETF Fund Flows Tracker
Monitor ETF inflows/outflows for sector/thematic trends.
Track large flows, compare to NAV, identify smart money movements.
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random


class ETFCategory(Enum):
    SECTOR = "sector"
    THEMATIC = "thematic"
    BROAD_MARKET = "broad_market"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    LEVERAGED = "leveraged"
    INVERSE = "inverse"


class FlowDirection(Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    NEUTRAL = "neutral"


@dataclass
class ETFInfo:
    """ETF metadata."""
    ticker: str
    name: str
    category: ETFCategory
    sector: Optional[str]  # Tech, Healthcare, Energy, etc.
    theme: Optional[str]  # AI, Clean Energy, Cybersecurity, etc.
    aum: float  # Assets Under Management
    expense_ratio: float
    avg_daily_volume: int
    inception_date: str
    top_holdings: List[str]


@dataclass
class DailyFlow:
    """Daily ETF flow data."""
    ticker: str
    date: str
    flow_amount: float  # Positive = inflow, negative = outflow
    aum: float
    nav: float
    price: float
    nav_premium_discount: float  # (Price - NAV) / NAV
    volume: int
    shares_outstanding: int
    shares_created: int  # New shares issued
    shares_redeemed: int  # Shares redeemed
    
    @property
    def flow_pct(self) -> float:
        """Flow as percentage of AUM."""
        return (self.flow_amount / self.aum * 100) if self.aum > 0 else 0
    
    @property
    def flow_direction(self) -> FlowDirection:
        """Determine flow direction."""
        if self.flow_amount > 1_000_000:  # $1M threshold
            return FlowDirection.INFLOW
        elif self.flow_amount < -1_000_000:
            return FlowDirection.OUTFLOW
        return FlowDirection.NEUTRAL


@dataclass
class FlowAlert:
    """Alert for significant flow activity."""
    ticker: str
    alert_type: str
    description: str
    flow_amount: float
    flow_pct: float
    timestamp: datetime
    significance: float  # 0-1 score


class ETFFundFlowsTracker:
    """
    Track ETF fund flows and identify trends.
    """
    
    # Alert thresholds
    LARGE_FLOW_THRESHOLD = 500_000_000  # $500M
    MEGA_FLOW_THRESHOLD = 1_000_000_000  # $1B
    FLOW_PCT_THRESHOLD = 3  # 3% of AUM
    NAV_PREMIUM_THRESHOLD = 0.5  # 0.5% premium/discount
    STREAK_DAYS_THRESHOLD = 5  # Consecutive days
    
    def __init__(self):
        self.etfs: Dict[str, ETFInfo] = {}
        self.flows: Dict[str, List[DailyFlow]] = {}  # ticker -> list of flows
        self.alerts: List[FlowAlert] = []
        
    def register_etf(self, etf: ETFInfo):
        """Register an ETF for tracking."""
        self.etfs[etf.ticker] = etf
        if etf.ticker not in self.flows:
            self.flows[etf.ticker] = []
    
    def add_flow(self, flow: DailyFlow) -> List[FlowAlert]:
        """Add daily flow data and check for alerts."""
        if flow.ticker not in self.flows:
            self.flows[flow.ticker] = []
        self.flows[flow.ticker].append(flow)
        
        # Sort by date
        self.flows[flow.ticker].sort(key=lambda f: f.date)
        
        return self._check_alerts(flow)
    
    def _check_alerts(self, flow: DailyFlow) -> List[FlowAlert]:
        """Check for alert conditions."""
        alerts = []
        
        # Large flow alert
        if abs(flow.flow_amount) >= self.LARGE_FLOW_THRESHOLD:
            direction = "inflow" if flow.flow_amount > 0 else "outflow"
            alerts.append(FlowAlert(
                ticker=flow.ticker,
                alert_type="LARGE_FLOW",
                description=f"${abs(flow.flow_amount)/1e9:.2f}B {direction}",
                flow_amount=flow.flow_amount,
                flow_pct=flow.flow_pct,
                timestamp=datetime.now(),
                significance=min(abs(flow.flow_amount) / self.MEGA_FLOW_THRESHOLD, 1.0)
            ))
        
        # Mega flow alert
        if abs(flow.flow_amount) >= self.MEGA_FLOW_THRESHOLD:
            direction = "INFLOW" if flow.flow_amount > 0 else "OUTFLOW"
            alerts.append(FlowAlert(
                ticker=flow.ticker,
                alert_type="MEGA_FLOW",
                description=f"🐋 ${abs(flow.flow_amount)/1e9:.2f}B {direction}",
                flow_amount=flow.flow_amount,
                flow_pct=flow.flow_pct,
                timestamp=datetime.now(),
                significance=1.0
            ))
        
        # High percentage flow
        if abs(flow.flow_pct) >= self.FLOW_PCT_THRESHOLD:
            direction = "inflow" if flow.flow_pct > 0 else "outflow"
            alerts.append(FlowAlert(
                ticker=flow.ticker,
                alert_type="HIGH_PCT_FLOW",
                description=f"{abs(flow.flow_pct):.1f}% of AUM {direction}",
                flow_amount=flow.flow_amount,
                flow_pct=flow.flow_pct,
                timestamp=datetime.now(),
                significance=min(abs(flow.flow_pct) / 10, 1.0)
            ))
        
        # NAV premium/discount
        if abs(flow.nav_premium_discount) >= self.NAV_PREMIUM_THRESHOLD:
            pd = "premium" if flow.nav_premium_discount > 0 else "discount"
            alerts.append(FlowAlert(
                ticker=flow.ticker,
                alert_type="NAV_DEVIATION",
                description=f"Trading at {abs(flow.nav_premium_discount):.2f}% {pd} to NAV",
                flow_amount=flow.flow_amount,
                flow_pct=flow.nav_premium_discount,
                timestamp=datetime.now(),
                significance=min(abs(flow.nav_premium_discount) / 2, 1.0)
            ))
        
        # Check for streak
        ticker_flows = self.flows.get(flow.ticker, [])
        if len(ticker_flows) >= self.STREAK_DAYS_THRESHOLD:
            recent = ticker_flows[-self.STREAK_DAYS_THRESHOLD:]
            if all(f.flow_amount > 0 for f in recent):
                total = sum(f.flow_amount for f in recent)
                alerts.append(FlowAlert(
                    ticker=flow.ticker,
                    alert_type="INFLOW_STREAK",
                    description=f"{self.STREAK_DAYS_THRESHOLD}-day inflow streak, ${total/1e6:.0f}M total",
                    flow_amount=total,
                    flow_pct=sum(f.flow_pct for f in recent),
                    timestamp=datetime.now(),
                    significance=0.8
                ))
            elif all(f.flow_amount < 0 for f in recent):
                total = sum(f.flow_amount for f in recent)
                alerts.append(FlowAlert(
                    ticker=flow.ticker,
                    alert_type="OUTFLOW_STREAK",
                    description=f"{self.STREAK_DAYS_THRESHOLD}-day outflow streak, ${abs(total)/1e6:.0f}M total",
                    flow_amount=total,
                    flow_pct=sum(f.flow_pct for f in recent),
                    timestamp=datetime.now(),
                    significance=0.8
                ))
        
        self.alerts.extend(alerts)
        return alerts
    
    def get_top_inflows(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get ETFs with largest inflows over period."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        flow_totals: Dict[str, float] = {}
        for ticker, flows in self.flows.items():
            recent = [f for f in flows if f.date >= cutoff]
            if recent:
                flow_totals[ticker] = sum(f.flow_amount for f in recent)
        
        # Sort by inflows (positive first)
        sorted_flows = sorted(flow_totals.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "ticker": ticker,
                "flow": amount,
                "flow_billions": amount / 1e9,
                "etf_name": self.etfs.get(ticker, ETFInfo(ticker, "", ETFCategory.BROAD_MARKET, None, None, 0, 0, 0, "", [])).name,
                "category": self.etfs.get(ticker, ETFInfo(ticker, "", ETFCategory.BROAD_MARKET, None, None, 0, 0, 0, "", [])).category.value
            }
            for ticker, amount in sorted_flows[:limit]
            if amount > 0
        ]
    
    def get_top_outflows(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get ETFs with largest outflows over period."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        flow_totals: Dict[str, float] = {}
        for ticker, flows in self.flows.items():
            recent = [f for f in flows if f.date >= cutoff]
            if recent:
                flow_totals[ticker] = sum(f.flow_amount for f in recent)
        
        # Sort by outflows (most negative first)
        sorted_flows = sorted(flow_totals.items(), key=lambda x: x[1])
        
        return [
            {
                "ticker": ticker,
                "flow": amount,
                "flow_billions": amount / 1e9,
                "etf_name": self.etfs.get(ticker, ETFInfo(ticker, "", ETFCategory.BROAD_MARKET, None, None, 0, 0, 0, "", [])).name,
                "category": self.etfs.get(ticker, ETFInfo(ticker, "", ETFCategory.BROAD_MARKET, None, None, 0, 0, 0, "", [])).category.value
            }
            for ticker, amount in sorted_flows[:limit]
            if amount < 0
        ]
    
    def get_sector_rotation(self, days: int = 30) -> Dict:
        """Analyze sector rotation based on ETF flows."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        sector_flows: Dict[str, float] = {}
        
        for ticker, flows in self.flows.items():
            etf_info = self.etfs.get(ticker)
            if etf_info and etf_info.sector:
                recent = [f for f in flows if f.date >= cutoff]
                total = sum(f.flow_amount for f in recent)
                sector_flows[etf_info.sector] = sector_flows.get(etf_info.sector, 0) + total
        
        # Sort by flows
        sorted_sectors = sorted(sector_flows.items(), key=lambda x: x[1], reverse=True)
        
        # Identify rotation pattern
        if sorted_sectors:
            top_sector = sorted_sectors[0][0]
            bottom_sector = sorted_sectors[-1][0]
            
            if sorted_sectors[0][1] > 0 and sorted_sectors[-1][1] < 0:
                rotation = f"Rotating from {bottom_sector} to {top_sector}"
            else:
                rotation = "No clear rotation pattern"
        else:
            rotation = "Insufficient data"
        
        return {
            "period_days": days,
            "sector_flows": [
                {"sector": sector, "flow": flow, "flow_billions": flow/1e9}
                for sector, flow in sorted_sectors
            ],
            "rotation_analysis": rotation,
            "top_sector": sorted_sectors[0] if sorted_sectors else None,
            "bottom_sector": sorted_sectors[-1] if sorted_sectors else None
        }
    
    def get_thematic_trends(self, days: int = 30) -> Dict:
        """Analyze thematic ETF flow trends."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        theme_flows: Dict[str, float] = {}
        
        for ticker, flows in self.flows.items():
            etf_info = self.etfs.get(ticker)
            if etf_info and etf_info.theme:
                recent = [f for f in flows if f.date >= cutoff]
                total = sum(f.flow_amount for f in recent)
                theme_flows[etf_info.theme] = theme_flows.get(etf_info.theme, 0) + total
        
        sorted_themes = sorted(theme_flows.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "period_days": days,
            "thematic_flows": [
                {
                    "theme": theme, 
                    "flow": flow, 
                    "flow_billions": flow/1e9,
                    "trend": "🟢 Hot" if flow > 500_000_000 else "🔴 Cold" if flow < -500_000_000 else "⚪ Neutral"
                }
                for theme, flow in sorted_themes
            ]
        }
    
    def get_smart_money_signals(self, days: int = 7) -> List[Dict]:
        """Identify potential smart money movements."""
        signals = []
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        for ticker, flows in self.flows.items():
            recent = [f for f in flows if f.date >= cutoff]
            if len(recent) < 3:
                continue
            
            total_flow = sum(f.flow_amount for f in recent)
            avg_premium = sum(f.nav_premium_discount for f in recent) / len(recent)
            
            etf_info = self.etfs.get(ticker)
            
            # Signal 1: Large persistent inflows with premium
            if total_flow > 500_000_000 and avg_premium > 0.1:
                signals.append({
                    "ticker": ticker,
                    "name": etf_info.name if etf_info else ticker,
                    "signal": "ACCUMULATION",
                    "description": f"Strong inflows (${total_flow/1e9:.1f}B) with NAV premium ({avg_premium:.2f}%)",
                    "total_flow": total_flow,
                    "nav_premium": avg_premium,
                    "confidence": 0.8
                })
            
            # Signal 2: Large outflows with discount
            elif total_flow < -500_000_000 and avg_premium < -0.1:
                signals.append({
                    "ticker": ticker,
                    "name": etf_info.name if etf_info else ticker,
                    "signal": "DISTRIBUTION",
                    "description": f"Heavy outflows (${abs(total_flow)/1e9:.1f}B) with NAV discount ({avg_premium:.2f}%)",
                    "total_flow": total_flow,
                    "nav_premium": avg_premium,
                    "confidence": 0.8
                })
            
            # Signal 3: Divergence - inflows but discount (value buying?)
            elif total_flow > 200_000_000 and avg_premium < -0.2:
                signals.append({
                    "ticker": ticker,
                    "name": etf_info.name if etf_info else ticker,
                    "signal": "CONTRARIAN_BUY",
                    "description": f"Buying into discount: ${total_flow/1e9:.1f}B inflow at {avg_premium:.2f}% discount",
                    "total_flow": total_flow,
                    "nav_premium": avg_premium,
                    "confidence": 0.7
                })
        
        return sorted(signals, key=lambda x: abs(x['total_flow']), reverse=True)
    
    def get_etf_analysis(self, ticker: str, days: int = 30) -> Dict:
        """Get detailed analysis for a specific ETF."""
        flows = self.flows.get(ticker, [])
        etf_info = self.etfs.get(ticker)
        
        if not flows:
            return {"ticker": ticker, "error": "No flow data available"}
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        recent = [f for f in flows if f.date >= cutoff]
        
        if not recent:
            return {"ticker": ticker, "error": "No recent flow data"}
        
        total_flow = sum(f.flow_amount for f in recent)
        avg_daily_flow = total_flow / len(recent)
        
        # Calculate streaks
        current_streak = 0
        streak_type = None
        for f in reversed(recent):
            if streak_type is None:
                streak_type = "inflow" if f.flow_amount > 0 else "outflow"
            if (f.flow_amount > 0 and streak_type == "inflow") or (f.flow_amount < 0 and streak_type == "outflow"):
                current_streak += 1
            else:
                break
        
        # Daily flows
        daily_flows = [
            {
                "date": f.date,
                "flow": f.flow_amount,
                "flow_pct": f.flow_pct,
                "nav_pd": f.nav_premium_discount
            }
            for f in recent[-10:]  # Last 10 days
        ]
        
        return {
            "ticker": ticker,
            "name": etf_info.name if etf_info else "N/A",
            "category": etf_info.category.value if etf_info else "N/A",
            "sector": etf_info.sector if etf_info else None,
            "theme": etf_info.theme if etf_info else None,
            "period_days": days,
            "total_flow": total_flow,
            "total_flow_billions": total_flow / 1e9,
            "avg_daily_flow": avg_daily_flow,
            "current_streak": current_streak,
            "streak_type": streak_type,
            "latest_aum": recent[-1].aum if recent else 0,
            "latest_nav_pd": recent[-1].nav_premium_discount if recent else 0,
            "daily_flows": daily_flows
        }
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get most recent alerts."""
        sorted_alerts = sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
        return [
            {
                "ticker": a.ticker,
                "type": a.alert_type,
                "description": a.description,
                "flow": a.flow_amount,
                "flow_pct": a.flow_pct,
                "significance": a.significance,
                "time": a.timestamp.isoformat()
            }
            for a in sorted_alerts
        ]


def generate_sample_data() -> ETFFundFlowsTracker:
    """Generate sample ETF flow data for demonstration."""
    tracker = ETFFundFlowsTracker()
    
    # Register ETFs
    etf_data = [
        ("SPY", "SPDR S&P 500 ETF", ETFCategory.BROAD_MARKET, None, None, 450e9),
        ("QQQ", "Invesco QQQ Trust", ETFCategory.BROAD_MARKET, "Technology", None, 200e9),
        ("IWM", "iShares Russell 2000 ETF", ETFCategory.BROAD_MARKET, None, None, 60e9),
        ("XLK", "Technology Select Sector SPDR", ETFCategory.SECTOR, "Technology", None, 55e9),
        ("XLF", "Financial Select Sector SPDR", ETFCategory.SECTOR, "Financials", None, 35e9),
        ("XLE", "Energy Select Sector SPDR", ETFCategory.SECTOR, "Energy", None, 30e9),
        ("XLV", "Health Care Select Sector SPDR", ETFCategory.SECTOR, "Healthcare", None, 35e9),
        ("XLI", "Industrial Select Sector SPDR", ETFCategory.SECTOR, "Industrials", None, 18e9),
        ("XLY", "Consumer Discretionary Select SPDR", ETFCategory.SECTOR, "Consumer Discretionary", None, 18e9),
        ("XLP", "Consumer Staples Select SPDR", ETFCategory.SECTOR, "Consumer Staples", None, 16e9),
        ("ARKK", "ARK Innovation ETF", ETFCategory.THEMATIC, None, "Disruptive Innovation", 8e9),
        ("ARKG", "ARK Genomic Revolution ETF", ETFCategory.THEMATIC, "Healthcare", "Genomics", 3e9),
        ("ICLN", "iShares Global Clean Energy ETF", ETFCategory.THEMATIC, "Energy", "Clean Energy", 4e9),
        ("TAN", "Invesco Solar ETF", ETFCategory.THEMATIC, "Energy", "Solar", 2e9),
        ("SMH", "VanEck Semiconductor ETF", ETFCategory.THEMATIC, "Technology", "Semiconductors", 12e9),
        ("BOTZ", "Global X Robotics & AI ETF", ETFCategory.THEMATIC, "Technology", "AI & Robotics", 2e9),
        ("HACK", "ETFMG Prime Cyber Security ETF", ETFCategory.THEMATIC, "Technology", "Cybersecurity", 2e9),
        ("TLT", "iShares 20+ Year Treasury Bond ETF", ETFCategory.FIXED_INCOME, "Bonds", None, 40e9),
        ("LQD", "iShares iBoxx $ Investment Grade ETF", ETFCategory.FIXED_INCOME, "Bonds", None, 35e9),
        ("HYG", "iShares iBoxx $ High Yield ETF", ETFCategory.FIXED_INCOME, "Bonds", None, 15e9),
        ("GLD", "SPDR Gold Shares", ETFCategory.COMMODITY, "Commodities", "Gold", 55e9),
        ("SLV", "iShares Silver Trust", ETFCategory.COMMODITY, "Commodities", "Silver", 10e9),
        ("USO", "United States Oil Fund", ETFCategory.COMMODITY, "Commodities", "Oil", 2e9),
        ("TQQQ", "ProShares UltraPro QQQ", ETFCategory.LEVERAGED, "Technology", None, 20e9),
        ("SQQQ", "ProShares UltraPro Short QQQ", ETFCategory.INVERSE, "Technology", None, 3e9),
    ]
    
    for ticker, name, category, sector, theme, aum in etf_data:
        etf = ETFInfo(
            ticker=ticker,
            name=name,
            category=category,
            sector=sector,
            theme=theme,
            aum=aum,
            expense_ratio=random.uniform(0.03, 0.75),
            avg_daily_volume=random.randint(1_000_000, 50_000_000),
            inception_date="2010-01-01",
            top_holdings=[]
        )
        tracker.register_etf(etf)
    
    # Generate 30 days of flow data
    for days_ago in range(30, -1, -1):
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        for ticker, name, category, sector, theme, base_aum in etf_data:
            # Random flow with some patterns
            flow_multiplier = 1.0
            
            # Tech seeing inflows recently
            if sector == "Technology" or theme in ("Semiconductors", "AI & Robotics"):
                flow_multiplier = 1.5
            # Energy seeing outflows
            elif sector == "Energy":
                flow_multiplier = -0.5
            
            base_flow = base_aum * 0.002  # 0.2% of AUM typical daily flow
            flow = random.gauss(0, base_flow) * flow_multiplier
            
            # Add some large flow days
            if random.random() < 0.05:
                flow *= random.uniform(3, 10)
            
            nav = 100 + random.gauss(0, 2)
            price = nav * (1 + random.gauss(0, 0.003))
            
            daily_flow = DailyFlow(
                ticker=ticker,
                date=date,
                flow_amount=flow,
                aum=base_aum + random.gauss(0, base_aum * 0.02),
                nav=nav,
                price=price,
                nav_premium_discount=(price - nav) / nav * 100,
                volume=random.randint(1_000_000, 50_000_000),
                shares_outstanding=int(base_aum / nav / 100),
                shares_created=max(0, int(flow / nav / 100)) if flow > 0 else 0,
                shares_redeemed=max(0, int(abs(flow) / nav / 100)) if flow < 0 else 0
            )
            
            tracker.add_flow(daily_flow)
    
    return tracker


if __name__ == "__main__":
    # Demo
    tracker = generate_sample_data()
    
    print("=== ETF FUND FLOWS TRACKER ===\n")
    
    # Top inflows
    print("TOP INFLOWS (7 days):")
    for etf in tracker.get_top_inflows(days=7, limit=5):
        print(f"  {etf['ticker']}: ${etf['flow_billions']:.2f}B - {etf['etf_name']}")
    
    # Top outflows
    print("\nTOP OUTFLOWS (7 days):")
    for etf in tracker.get_top_outflows(days=7, limit=5):
        print(f"  {etf['ticker']}: ${etf['flow_billions']:.2f}B - {etf['etf_name']}")
    
    # Sector rotation
    print("\nSECTOR ROTATION (30 days):")
    rotation = tracker.get_sector_rotation(days=30)
    print(f"  {rotation['rotation_analysis']}")
    for s in rotation['sector_flows'][:5]:
        print(f"    {s['sector']}: ${s['flow_billions']:.2f}B")
    
    # Smart money signals
    print("\nSMART MONEY SIGNALS:")
    for signal in tracker.get_smart_money_signals()[:3]:
        print(f"  {signal['signal']}: {signal['ticker']} - {signal['description']}")
