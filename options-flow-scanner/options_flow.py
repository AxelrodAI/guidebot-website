"""
Options Flow / Unusual Activity Scanner
Tracks unusual options activity - large block trades, sweeps, and significant OI changes.
Alerts on volume >5x average, large premium trades >$500k, and unusual put/call ratios.
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random


class TradeType(Enum):
    SWEEP = "sweep"  # Aggressive multi-exchange execution
    BLOCK = "block"  # Large single transaction
    SPLIT = "split"  # Split across multiple trades
    NORMAL = "normal"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class Sentiment(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class OptionsFlow:
    """Represents a single options flow transaction."""
    ticker: str
    timestamp: datetime
    expiration: str
    strike: float
    option_type: str  # 'call' or 'put'
    trade_type: TradeType
    order_side: OrderSide
    volume: int
    open_interest: int
    premium: float  # Total premium in dollars
    implied_vol: float
    delta: float
    underlying_price: float
    spot_reference: float  # Underlying price at time of trade
    exchange: str
    
    @property
    def is_unusual(self) -> bool:
        """Determine if this flow is unusual."""
        return (
            self.premium >= 100000 or  # $100k+ premium
            self.volume > self.open_interest * 0.5  # Volume > 50% of OI
        )
    
    @property
    def sentiment(self) -> Sentiment:
        """Infer sentiment from the trade."""
        if self.option_type == 'call':
            if self.order_side == OrderSide.BUY:
                return Sentiment.BULLISH
            elif self.order_side == OrderSide.SELL:
                return Sentiment.BEARISH
        else:  # put
            if self.order_side == OrderSide.BUY:
                return Sentiment.BEARISH
            elif self.order_side == OrderSide.SELL:
                return Sentiment.BULLISH
        return Sentiment.NEUTRAL
    
    def days_to_expiry(self) -> int:
        """Calculate days until expiration."""
        exp_date = datetime.strptime(self.expiration, "%Y-%m-%d")
        return (exp_date - datetime.now()).days
    
    def moneyness(self) -> str:
        """Determine if option is ITM, ATM, or OTM."""
        pct_diff = (self.strike - self.underlying_price) / self.underlying_price
        if self.option_type == 'call':
            if pct_diff < -0.02:
                return "ITM"
            elif pct_diff > 0.02:
                return "OTM"
            return "ATM"
        else:  # put
            if pct_diff > 0.02:
                return "ITM"
            elif pct_diff < -0.02:
                return "OTM"
            return "ATM"


@dataclass
class UnusualActivity:
    """Detected unusual activity pattern."""
    ticker: str
    alert_type: str
    description: str
    flows: List[OptionsFlow]
    total_premium: float
    net_sentiment: Sentiment
    confidence: float  # 0-1 confidence score
    timestamp: datetime


class OptionsFlowScanner:
    """
    Scans for unusual options activity patterns.
    """
    
    # Alert thresholds
    VOLUME_MULTIPLIER_THRESHOLD = 5  # Volume > 5x average
    LARGE_PREMIUM_THRESHOLD = 500000  # $500k premium
    WHALE_PREMIUM_THRESHOLD = 1000000  # $1M whale alert
    OI_CHANGE_THRESHOLD = 0.25  # 25% OI change
    PUT_CALL_SKEW_THRESHOLD = 3  # 3:1 ratio is unusual
    
    def __init__(self):
        self.flows: List[OptionsFlow] = []
        self.historical_volume: Dict[str, Dict[str, float]] = {}  # ticker -> date -> avg volume
        self.alerts: List[UnusualActivity] = []
        self.watchlist: List[str] = []
        
    def add_flow(self, flow: OptionsFlow) -> List[UnusualActivity]:
        """Add a flow and check for unusual activity."""
        self.flows.append(flow)
        return self._check_for_alerts(flow)
    
    def _check_for_alerts(self, flow: OptionsFlow) -> List[UnusualActivity]:
        """Check if the new flow triggers any alerts."""
        alerts = []
        
        # Large premium alert
        if flow.premium >= self.LARGE_PREMIUM_THRESHOLD:
            alert = UnusualActivity(
                ticker=flow.ticker,
                alert_type="LARGE_PREMIUM",
                description=f"${flow.premium:,.0f} premium on {flow.option_type} {flow.strike} exp {flow.expiration}",
                flows=[flow],
                total_premium=flow.premium,
                net_sentiment=flow.sentiment,
                confidence=min(flow.premium / self.WHALE_PREMIUM_THRESHOLD, 1.0),
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Whale alert
        if flow.premium >= self.WHALE_PREMIUM_THRESHOLD:
            alert = UnusualActivity(
                ticker=flow.ticker,
                alert_type="WHALE_ALERT",
                description=f"🐋 WHALE: ${flow.premium:,.0f} {flow.trade_type.value} on {flow.ticker}",
                flows=[flow],
                total_premium=flow.premium,
                net_sentiment=flow.sentiment,
                confidence=0.95,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Sweep alert (aggressive execution)
        if flow.trade_type == TradeType.SWEEP and flow.premium >= 100000:
            alert = UnusualActivity(
                ticker=flow.ticker,
                alert_type="SWEEP",
                description=f"Aggressive sweep: {flow.volume} contracts across exchanges",
                flows=[flow],
                total_premium=flow.premium,
                net_sentiment=flow.sentiment,
                confidence=0.8,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Volume vs OI alert
        if flow.open_interest > 0 and flow.volume > flow.open_interest:
            alert = UnusualActivity(
                ticker=flow.ticker,
                alert_type="VOLUME_OI_ANOMALY",
                description=f"Volume ({flow.volume}) exceeds OI ({flow.open_interest})",
                flows=[flow],
                total_premium=flow.premium,
                net_sentiment=flow.sentiment,
                confidence=0.85,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        self.alerts.extend(alerts)
        return alerts
    
    def scan_ticker(self, ticker: str, lookback_hours: int = 24) -> Dict:
        """Scan a specific ticker for unusual activity."""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        ticker_flows = [f for f in self.flows if f.ticker == ticker and f.timestamp >= cutoff]
        
        if not ticker_flows:
            return {"ticker": ticker, "flows": [], "summary": "No recent activity"}
        
        # Aggregate stats
        total_call_volume = sum(f.volume for f in ticker_flows if f.option_type == 'call')
        total_put_volume = sum(f.volume for f in ticker_flows if f.option_type == 'put')
        total_call_premium = sum(f.premium for f in ticker_flows if f.option_type == 'call')
        total_put_premium = sum(f.premium for f in ticker_flows if f.option_type == 'put')
        
        # Put/Call ratio
        pc_volume_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else float('inf')
        pc_premium_ratio = total_put_premium / total_call_premium if total_call_premium > 0 else float('inf')
        
        # Net sentiment
        bullish_premium = sum(f.premium for f in ticker_flows if f.sentiment == Sentiment.BULLISH)
        bearish_premium = sum(f.premium for f in ticker_flows if f.sentiment == Sentiment.BEARISH)
        
        if bullish_premium > bearish_premium * 1.5:
            net_sentiment = "BULLISH"
        elif bearish_premium > bullish_premium * 1.5:
            net_sentiment = "BEARISH"
        else:
            net_sentiment = "NEUTRAL"
        
        # Identify largest flows
        largest_flows = sorted(ticker_flows, key=lambda f: f.premium, reverse=True)[:5]
        
        return {
            "ticker": ticker,
            "period_hours": lookback_hours,
            "total_flows": len(ticker_flows),
            "call_volume": total_call_volume,
            "put_volume": total_put_volume,
            "call_premium": total_call_premium,
            "put_premium": total_put_premium,
            "put_call_volume_ratio": round(pc_volume_ratio, 2),
            "put_call_premium_ratio": round(pc_premium_ratio, 2),
            "net_sentiment": net_sentiment,
            "bullish_premium": bullish_premium,
            "bearish_premium": bearish_premium,
            "largest_flows": [
                {
                    "type": f.option_type,
                    "strike": f.strike,
                    "expiration": f.expiration,
                    "premium": f.premium,
                    "volume": f.volume,
                    "sentiment": f.sentiment.value
                }
                for f in largest_flows
            ]
        }
    
    def get_market_overview(self, lookback_hours: int = 4) -> Dict:
        """Get market-wide options flow overview."""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        recent_flows = [f for f in self.flows if f.timestamp >= cutoff]
        
        if not recent_flows:
            return {"message": "No recent flow data"}
        
        # Aggregate by ticker
        ticker_data: Dict[str, Dict] = {}
        for flow in recent_flows:
            if flow.ticker not in ticker_data:
                ticker_data[flow.ticker] = {
                    "total_premium": 0,
                    "call_premium": 0,
                    "put_premium": 0,
                    "flow_count": 0,
                    "bullish_premium": 0,
                    "bearish_premium": 0
                }
            ticker_data[flow.ticker]["total_premium"] += flow.premium
            ticker_data[flow.ticker]["flow_count"] += 1
            if flow.option_type == 'call':
                ticker_data[flow.ticker]["call_premium"] += flow.premium
            else:
                ticker_data[flow.ticker]["put_premium"] += flow.premium
            if flow.sentiment == Sentiment.BULLISH:
                ticker_data[flow.ticker]["bullish_premium"] += flow.premium
            else:
                ticker_data[flow.ticker]["bearish_premium"] += flow.premium
        
        # Sort by total premium
        top_tickers = sorted(
            ticker_data.items(),
            key=lambda x: x[1]["total_premium"],
            reverse=True
        )[:20]
        
        # Calculate overall market sentiment
        total_bullish = sum(d["bullish_premium"] for _, d in top_tickers)
        total_bearish = sum(d["bearish_premium"] for _, d in top_tickers)
        
        return {
            "period_hours": lookback_hours,
            "total_flows": len(recent_flows),
            "total_premium": sum(f.premium for f in recent_flows),
            "market_sentiment": "BULLISH" if total_bullish > total_bearish * 1.2 else 
                               "BEARISH" if total_bearish > total_bullish * 1.2 else "NEUTRAL",
            "top_tickers": [
                {
                    "ticker": ticker,
                    "total_premium": data["total_premium"],
                    "call_premium": data["call_premium"],
                    "put_premium": data["put_premium"],
                    "flow_count": data["flow_count"],
                    "sentiment": "BULLISH" if data["bullish_premium"] > data["bearish_premium"] * 1.3 else
                                "BEARISH" if data["bearish_premium"] > data["bullish_premium"] * 1.3 else "NEUTRAL"
                }
                for ticker, data in top_tickers
            ]
        }
    
    def detect_unusual_volume(self, avg_volume: Dict[str, float]) -> List[UnusualActivity]:
        """Detect when volume exceeds 5x historical average."""
        alerts = []
        
        # Group today's flows by ticker
        today = datetime.now().date()
        today_flows = [f for f in self.flows if f.timestamp.date() == today]
        
        ticker_volumes: Dict[str, int] = {}
        for flow in today_flows:
            ticker_volumes[flow.ticker] = ticker_volumes.get(flow.ticker, 0) + flow.volume
        
        for ticker, volume in ticker_volumes.items():
            if ticker in avg_volume:
                if volume > avg_volume[ticker] * self.VOLUME_MULTIPLIER_THRESHOLD:
                    alert = UnusualActivity(
                        ticker=ticker,
                        alert_type="UNUSUAL_VOLUME",
                        description=f"Volume {volume:,} is {volume/avg_volume[ticker]:.1f}x average",
                        flows=[f for f in today_flows if f.ticker == ticker],
                        total_premium=sum(f.premium for f in today_flows if f.ticker == ticker),
                        net_sentiment=Sentiment.NEUTRAL,
                        confidence=min((volume / avg_volume[ticker]) / 10, 1.0),
                        timestamp=datetime.now()
                    )
                    alerts.append(alert)
        
        return alerts
    
    def detect_put_call_skew(self, lookback_hours: int = 24) -> List[Dict]:
        """Detect unusual put/call ratios."""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        recent_flows = [f for f in self.flows if f.timestamp >= cutoff]
        
        # Group by ticker
        ticker_ratios: Dict[str, Dict] = {}
        for flow in recent_flows:
            if flow.ticker not in ticker_ratios:
                ticker_ratios[flow.ticker] = {"calls": 0, "puts": 0}
            if flow.option_type == 'call':
                ticker_ratios[flow.ticker]["calls"] += flow.premium
            else:
                ticker_ratios[flow.ticker]["puts"] += flow.premium
        
        # Find unusual ratios
        skewed = []
        for ticker, data in ticker_ratios.items():
            if data["calls"] == 0 and data["puts"] > 0:
                ratio = float('inf')
            elif data["puts"] == 0 and data["calls"] > 0:
                ratio = 0
            else:
                ratio = data["puts"] / data["calls"] if data["calls"] > 0 else 0
            
            if ratio >= self.PUT_CALL_SKEW_THRESHOLD or (ratio > 0 and ratio <= 1/self.PUT_CALL_SKEW_THRESHOLD):
                skewed.append({
                    "ticker": ticker,
                    "put_call_ratio": ratio,
                    "call_premium": data["calls"],
                    "put_premium": data["puts"],
                    "bias": "BEARISH" if ratio >= self.PUT_CALL_SKEW_THRESHOLD else "BULLISH"
                })
        
        return sorted(skewed, key=lambda x: abs(x["put_call_ratio"] - 1), reverse=True)
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get most recent alerts."""
        sorted_alerts = sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
        return [
            {
                "ticker": a.ticker,
                "type": a.alert_type,
                "description": a.description,
                "premium": a.total_premium,
                "sentiment": a.net_sentiment.value,
                "confidence": a.confidence,
                "time": a.timestamp.isoformat()
            }
            for a in sorted_alerts
        ]


def generate_sample_data() -> OptionsFlowScanner:
    """Generate sample options flow data for demonstration."""
    scanner = OptionsFlowScanner()
    
    tickers = ['AAPL', 'TSLA', 'NVDA', 'SPY', 'QQQ', 'AMD', 'META', 'AMZN', 'MSFT', 'GOOGL']
    exchanges = ['CBOE', 'ISE', 'PHLX', 'BOX', 'MIAX', 'NASDAQ']
    
    # Generate flows for the past 24 hours
    for _ in range(100):
        ticker = random.choice(tickers)
        base_price = {
            'AAPL': 178, 'TSLA': 245, 'NVDA': 485, 'SPY': 475, 'QQQ': 405,
            'AMD': 125, 'META': 385, 'AMZN': 175, 'MSFT': 395, 'GOOGL': 145
        }[ticker]
        
        # Random time in past 24 hours
        hours_ago = random.uniform(0, 24)
        timestamp = datetime.now() - timedelta(hours=hours_ago)
        
        # Generate strike near the money
        option_type = random.choice(['call', 'put'])
        strike_offset = random.uniform(-0.05, 0.05) * base_price
        strike = round((base_price + strike_offset) / 5) * 5  # Round to $5
        
        # Expiration 1-60 days out
        days_to_exp = random.choice([7, 14, 21, 30, 45, 60])
        exp_date = datetime.now() + timedelta(days=days_to_exp)
        expiration = exp_date.strftime("%Y-%m-%d")
        
        # Volume and OI
        volume = random.randint(50, 5000)
        open_interest = random.randint(100, 50000)
        
        # Premium (volume * price per contract * 100 shares)
        option_price = random.uniform(0.5, 15)
        premium = volume * option_price * 100
        
        # Add some whale trades
        if random.random() < 0.05:
            volume = random.randint(5000, 20000)
            premium = volume * random.uniform(5, 20) * 100
        
        trade_type = random.choices(
            [TradeType.SWEEP, TradeType.BLOCK, TradeType.SPLIT, TradeType.NORMAL],
            weights=[0.15, 0.1, 0.1, 0.65]
        )[0]
        
        order_side = random.choice([OrderSide.BUY, OrderSide.SELL])
        
        flow = OptionsFlow(
            ticker=ticker,
            timestamp=timestamp,
            expiration=expiration,
            strike=strike,
            option_type=option_type,
            trade_type=trade_type,
            order_side=order_side,
            volume=volume,
            open_interest=open_interest,
            premium=premium,
            implied_vol=random.uniform(0.2, 0.8),
            delta=random.uniform(-0.9, 0.9),
            underlying_price=base_price,
            spot_reference=base_price * (1 + random.uniform(-0.01, 0.01)),
            exchange=random.choice(exchanges)
        )
        
        scanner.add_flow(flow)
    
    return scanner


if __name__ == "__main__":
    # Demo
    scanner = generate_sample_data()
    
    print("=== OPTIONS FLOW SCANNER ===\n")
    
    # Market overview
    overview = scanner.get_market_overview(lookback_hours=24)
    print(f"Market Overview (24h):")
    print(f"  Total Flows: {overview['total_flows']}")
    print(f"  Total Premium: ${overview['total_premium']:,.0f}")
    print(f"  Market Sentiment: {overview['market_sentiment']}")
    print(f"\nTop Active Tickers:")
    for t in overview['top_tickers'][:5]:
        print(f"  {t['ticker']}: ${t['total_premium']:,.0f} ({t['sentiment']})")
    
    # Recent alerts
    print(f"\n=== RECENT ALERTS ===")
    for alert in scanner.get_recent_alerts(10):
        print(f"  [{alert['type']}] {alert['ticker']}: {alert['description']}")
    
    # Scan specific ticker
    print(f"\n=== NVDA FLOW ANALYSIS ===")
    nvda = scanner.scan_ticker('NVDA')
    print(f"  Net Sentiment: {nvda['net_sentiment']}")
    print(f"  P/C Volume Ratio: {nvda['put_call_volume_ratio']}")
    print(f"  Call Premium: ${nvda['call_premium']:,.0f}")
    print(f"  Put Premium: ${nvda['put_premium']:,.0f}")
