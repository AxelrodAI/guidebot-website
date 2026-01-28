"""
Technical Divergence Alert System
Detect price vs indicator divergences (RSI, MACD, OBV).
Alert on bullish/bearish divergences with historical accuracy tracking.
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random
import math


class DivergenceType(Enum):
    BULLISH = "bullish"      # Price lower low, indicator higher low
    BEARISH = "bearish"      # Price higher high, indicator lower high
    HIDDEN_BULLISH = "hidden_bullish"  # Price higher low, indicator lower low (continuation)
    HIDDEN_BEARISH = "hidden_bearish"  # Price lower high, indicator higher high (continuation)


class IndicatorType(Enum):
    RSI = "RSI"
    MACD = "MACD"
    OBV = "OBV"
    STOCH = "Stochastic"
    MFI = "MFI"
    CCI = "CCI"


class Strength(Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class PriceData:
    """OHLCV price data."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class DivergenceSignal:
    """A detected divergence signal."""
    ticker: str
    divergence_type: DivergenceType
    indicator: IndicatorType
    detected_at: datetime
    price_start: float
    price_end: float
    indicator_start: float
    indicator_end: float
    lookback_bars: int
    strength: Strength
    confidence: float  # 0-1
    timeframe: str  # "1D", "4H", "1H"
    
    @property
    def is_bullish(self) -> bool:
        return self.divergence_type in (DivergenceType.BULLISH, DivergenceType.HIDDEN_BULLISH)
    
    @property
    def price_change_pct(self) -> float:
        return ((self.price_end - self.price_start) / self.price_start) * 100
    
    def summary(self) -> str:
        direction = "📈" if self.is_bullish else "📉"
        return f"{direction} {self.ticker}: {self.divergence_type.value} {self.indicator.value} divergence ({self.strength.value})"


@dataclass
class DivergenceOutcome:
    """Track historical accuracy of divergence signals."""
    signal: DivergenceSignal
    outcome_price: float
    outcome_date: datetime
    return_pct: float
    success: bool  # Did the divergence correctly predict direction?


class TechnicalIndicators:
    """Calculate technical indicators from price data."""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calculate RSI from closing prices."""
        if len(prices) < period + 1:
            return []
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        
        rsi_values = []
        
        for i in range(period, len(deltas) + 1):
            avg_gain = sum(gains[i-period:i]) / period
            avg_loss = sum(losses[i-period:i]) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float]]:
        """Calculate MACD line and histogram."""
        if len(prices) < slow + signal:
            return [], []
        
        def ema(data, period):
            ema_values = []
            multiplier = 2 / (period + 1)
            ema_values.append(sum(data[:period]) / period)
            for i in range(period, len(data)):
                ema_values.append((data[i] * multiplier) + (ema_values[-1] * (1 - multiplier)))
            return ema_values
        
        ema_fast = ema(prices, fast)
        ema_slow = ema(prices, slow)
        
        # Align EMAs
        offset = slow - fast
        macd_line = [ema_fast[i + offset] - ema_slow[i] for i in range(len(ema_slow))]
        
        signal_line = ema(macd_line, signal) if len(macd_line) >= signal else []
        
        histogram = []
        offset = len(macd_line) - len(signal_line)
        for i in range(len(signal_line)):
            histogram.append(macd_line[i + offset] - signal_line[i])
        
        return macd_line, histogram
    
    @staticmethod
    def calculate_obv(prices: List[float], volumes: List[int]) -> List[float]:
        """Calculate On-Balance Volume."""
        if len(prices) != len(volumes) or len(prices) < 2:
            return []
        
        obv = [0]
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif prices[i] < prices[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        
        return obv


class DivergenceDetector:
    """Detect divergences between price and indicators."""
    
    def __init__(self, lookback_min: int = 5, lookback_max: int = 25):
        self.lookback_min = lookback_min
        self.lookback_max = lookback_max
        self.indicators = TechnicalIndicators()
    
    def find_local_extrema(self, values: List[float], window: int = 3) -> Tuple[List[int], List[int]]:
        """Find local highs and lows indices."""
        highs = []
        lows = []
        
        for i in range(window, len(values) - window):
            is_high = all(values[i] > values[i-j] and values[i] > values[i+j] 
                         for j in range(1, window + 1))
            is_low = all(values[i] < values[i-j] and values[i] < values[i+j] 
                        for j in range(1, window + 1))
            
            if is_high:
                highs.append(i)
            if is_low:
                lows.append(i)
        
        return highs, lows
    
    def detect_divergence(
        self,
        prices: List[float],
        indicator_values: List[float],
        indicator_type: IndicatorType
    ) -> Optional[DivergenceSignal]:
        """Detect divergence between price and indicator."""
        if len(prices) != len(indicator_values) or len(prices) < self.lookback_max:
            return None
        
        price_highs, price_lows = self.find_local_extrema(prices)
        ind_highs, ind_lows = self.find_local_extrema(indicator_values)
        
        # Check for bearish divergence (price higher high, indicator lower high)
        if len(price_highs) >= 2 and len(ind_highs) >= 2:
            p1_idx, p2_idx = price_highs[-2], price_highs[-1]
            i1_idx, i2_idx = ind_highs[-2], ind_highs[-1]
            
            # Ensure indices are in reasonable range
            if abs(p2_idx - i2_idx) <= 3 and abs(p1_idx - i1_idx) <= 3:
                if prices[p2_idx] > prices[p1_idx] and indicator_values[i2_idx] < indicator_values[i1_idx]:
                    strength = self._calculate_strength(
                        prices[p2_idx] - prices[p1_idx],
                        indicator_values[i1_idx] - indicator_values[i2_idx],
                        indicator_type
                    )
                    return DivergenceSignal(
                        ticker="",  # Set by caller
                        divergence_type=DivergenceType.BEARISH,
                        indicator=indicator_type,
                        detected_at=datetime.now(),
                        price_start=prices[p1_idx],
                        price_end=prices[p2_idx],
                        indicator_start=indicator_values[i1_idx],
                        indicator_end=indicator_values[i2_idx],
                        lookback_bars=p2_idx - p1_idx,
                        strength=strength,
                        confidence=self._calculate_confidence(strength, indicator_type),
                        timeframe="1D"
                    )
        
        # Check for bullish divergence (price lower low, indicator higher low)
        if len(price_lows) >= 2 and len(ind_lows) >= 2:
            p1_idx, p2_idx = price_lows[-2], price_lows[-1]
            i1_idx, i2_idx = ind_lows[-2], ind_lows[-1]
            
            if abs(p2_idx - i2_idx) <= 3 and abs(p1_idx - i1_idx) <= 3:
                if prices[p2_idx] < prices[p1_idx] and indicator_values[i2_idx] > indicator_values[i1_idx]:
                    strength = self._calculate_strength(
                        prices[p1_idx] - prices[p2_idx],
                        indicator_values[i2_idx] - indicator_values[i1_idx],
                        indicator_type
                    )
                    return DivergenceSignal(
                        ticker="",
                        divergence_type=DivergenceType.BULLISH,
                        indicator=indicator_type,
                        detected_at=datetime.now(),
                        price_start=prices[p1_idx],
                        price_end=prices[p2_idx],
                        indicator_start=indicator_values[i1_idx],
                        indicator_end=indicator_values[i2_idx],
                        lookback_bars=p2_idx - p1_idx,
                        strength=strength,
                        confidence=self._calculate_confidence(strength, indicator_type),
                        timeframe="1D"
                    )
        
        return None
    
    def _calculate_strength(self, price_diff: float, ind_diff: float, indicator: IndicatorType) -> Strength:
        """Calculate divergence strength based on magnitude."""
        # Normalize by indicator type
        if indicator == IndicatorType.RSI:
            if abs(ind_diff) > 15:
                return Strength.STRONG
            elif abs(ind_diff) > 8:
                return Strength.MODERATE
            return Strength.WEAK
        elif indicator == IndicatorType.MACD:
            # MACD varies by stock price, use relative
            if abs(ind_diff / (abs(ind_diff) + 0.01)) > 0.5:
                return Strength.STRONG
            return Strength.MODERATE
        return Strength.MODERATE
    
    def _calculate_confidence(self, strength: Strength, indicator: IndicatorType) -> float:
        """Calculate confidence score."""
        base = 0.5
        if strength == Strength.STRONG:
            base = 0.8
        elif strength == Strength.MODERATE:
            base = 0.65
        
        # RSI divergences historically more reliable
        if indicator == IndicatorType.RSI:
            base += 0.1
        
        return min(base, 0.95)


class DivergenceScanner:
    """
    Scan watchlist for divergences with accuracy tracking.
    """
    
    def __init__(self):
        self.detector = DivergenceDetector()
        self.signals: List[DivergenceSignal] = []
        self.outcomes: List[DivergenceOutcome] = []
        self.watchlist: List[str] = []
        self.price_data: Dict[str, List[PriceData]] = {}
    
    def add_to_watchlist(self, ticker: str):
        """Add ticker to watchlist."""
        if ticker not in self.watchlist:
            self.watchlist.append(ticker)
    
    def remove_from_watchlist(self, ticker: str):
        """Remove ticker from watchlist."""
        if ticker in self.watchlist:
            self.watchlist.remove(ticker)
    
    def scan_ticker(self, ticker: str, prices: List[PriceData]) -> List[DivergenceSignal]:
        """Scan a single ticker for divergences."""
        signals = []
        
        closes = [p.close for p in prices]
        volumes = [p.volume for p in prices]
        
        # Check RSI divergence
        rsi = self.detector.indicators.calculate_rsi(closes)
        if len(rsi) > 0:
            # Align RSI with prices
            offset = len(closes) - len(rsi)
            aligned_prices = closes[offset:]
            
            signal = self.detector.detect_divergence(aligned_prices, rsi, IndicatorType.RSI)
            if signal:
                signal.ticker = ticker
                signals.append(signal)
        
        # Check MACD divergence
        macd_line, histogram = self.detector.indicators.calculate_macd(closes)
        if len(histogram) > 0:
            offset = len(closes) - len(histogram)
            aligned_prices = closes[offset:]
            
            signal = self.detector.detect_divergence(aligned_prices, histogram, IndicatorType.MACD)
            if signal:
                signal.ticker = ticker
                signals.append(signal)
        
        # Check OBV divergence
        obv = self.detector.indicators.calculate_obv(closes, volumes)
        if len(obv) == len(closes):
            signal = self.detector.detect_divergence(closes, obv, IndicatorType.OBV)
            if signal:
                signal.ticker = ticker
                signals.append(signal)
        
        self.signals.extend(signals)
        return signals
    
    def scan_watchlist(self) -> Dict[str, List[DivergenceSignal]]:
        """Scan all watchlist tickers for divergences."""
        results = {}
        for ticker in self.watchlist:
            if ticker in self.price_data:
                signals = self.scan_ticker(ticker, self.price_data[ticker])
                if signals:
                    results[ticker] = signals
        return results
    
    def get_recent_signals(self, hours: int = 24, divergence_type: Optional[DivergenceType] = None) -> List[DivergenceSignal]:
        """Get signals from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        signals = [s for s in self.signals if s.detected_at >= cutoff]
        
        if divergence_type:
            signals = [s for s in signals if s.divergence_type == divergence_type]
        
        return sorted(signals, key=lambda s: s.detected_at, reverse=True)
    
    def get_accuracy_stats(self, indicator: Optional[IndicatorType] = None) -> Dict:
        """Calculate historical accuracy statistics."""
        outcomes = self.outcomes
        if indicator:
            outcomes = [o for o in outcomes if o.signal.indicator == indicator]
        
        if not outcomes:
            return {"message": "No tracked outcomes yet"}
        
        total = len(outcomes)
        successful = sum(1 for o in outcomes if o.success)
        
        bullish = [o for o in outcomes if o.signal.is_bullish]
        bearish = [o for o in outcomes if not o.signal.is_bullish]
        
        return {
            "total_signals": total,
            "successful": successful,
            "accuracy": successful / total * 100,
            "bullish_accuracy": sum(1 for o in bullish if o.success) / len(bullish) * 100 if bullish else 0,
            "bearish_accuracy": sum(1 for o in bearish if o.success) / len(bearish) * 100 if bearish else 0,
            "avg_return": sum(o.return_pct for o in outcomes) / total,
            "avg_winning_return": sum(o.return_pct for o in outcomes if o.success) / successful if successful else 0,
            "by_indicator": self._accuracy_by_indicator(outcomes)
        }
    
    def _accuracy_by_indicator(self, outcomes: List[DivergenceOutcome]) -> Dict:
        """Break down accuracy by indicator."""
        by_ind = {}
        for indicator in IndicatorType:
            ind_outcomes = [o for o in outcomes if o.signal.indicator == indicator]
            if ind_outcomes:
                successful = sum(1 for o in ind_outcomes if o.success)
                by_ind[indicator.value] = {
                    "count": len(ind_outcomes),
                    "accuracy": successful / len(ind_outcomes) * 100
                }
        return by_ind
    
    def get_signal_summary(self) -> Dict:
        """Get summary of current signals."""
        recent = self.get_recent_signals(hours=48)
        
        bullish = [s for s in recent if s.is_bullish]
        bearish = [s for s in recent if not s.is_bullish]
        
        by_indicator = {}
        for ind in IndicatorType:
            count = len([s for s in recent if s.indicator == ind])
            if count > 0:
                by_indicator[ind.value] = count
        
        return {
            "total_signals": len(recent),
            "bullish": len(bullish),
            "bearish": len(bearish),
            "by_indicator": by_indicator,
            "strong_signals": len([s for s in recent if s.strength == Strength.STRONG]),
            "high_confidence": len([s for s in recent if s.confidence >= 0.75]),
            "tickers_with_signals": list(set(s.ticker for s in recent))
        }


def generate_sample_data() -> DivergenceScanner:
    """Generate sample divergence data for demonstration."""
    scanner = DivergenceScanner()
    
    tickers = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'GOOGL', 'MSFT', 'AMZN', 'SPY', 'QQQ']
    
    for ticker in tickers:
        scanner.add_to_watchlist(ticker)
        
        # Generate price data
        prices = []
        base_price = random.uniform(100, 500)
        for i in range(60):
            date = (datetime.now() - timedelta(days=60-i)).strftime("%Y-%m-%d")
            change = random.gauss(0, 0.02)
            base_price *= (1 + change)
            
            prices.append(PriceData(
                date=date,
                open=base_price * (1 + random.gauss(0, 0.005)),
                high=base_price * (1 + abs(random.gauss(0, 0.01))),
                low=base_price * (1 - abs(random.gauss(0, 0.01))),
                close=base_price,
                volume=random.randint(1_000_000, 50_000_000)
            ))
        
        scanner.price_data[ticker] = prices
    
    # Scan for divergences
    scanner.scan_watchlist()
    
    # Generate some sample signals manually for demo
    sample_signals = [
        DivergenceSignal(
            ticker="NVDA",
            divergence_type=DivergenceType.BULLISH,
            indicator=IndicatorType.RSI,
            detected_at=datetime.now() - timedelta(hours=2),
            price_start=485.50,
            price_end=478.20,
            indicator_start=28.5,
            indicator_end=35.2,
            lookback_bars=8,
            strength=Strength.STRONG,
            confidence=0.85,
            timeframe="1D"
        ),
        DivergenceSignal(
            ticker="TSLA",
            divergence_type=DivergenceType.BEARISH,
            indicator=IndicatorType.MACD,
            detected_at=datetime.now() - timedelta(hours=5),
            price_start=242.10,
            price_end=248.90,
            indicator_start=2.45,
            indicator_end=1.85,
            lookback_bars=12,
            strength=Strength.MODERATE,
            confidence=0.72,
            timeframe="1D"
        ),
        DivergenceSignal(
            ticker="AMD",
            divergence_type=DivergenceType.BULLISH,
            indicator=IndicatorType.OBV,
            detected_at=datetime.now() - timedelta(hours=8),
            price_start=125.80,
            price_end=122.40,
            indicator_start=15_000_000,
            indicator_end=18_500_000,
            lookback_bars=6,
            strength=Strength.STRONG,
            confidence=0.78,
            timeframe="1D"
        ),
        DivergenceSignal(
            ticker="META",
            divergence_type=DivergenceType.HIDDEN_BEARISH,
            indicator=IndicatorType.RSI,
            detected_at=datetime.now() - timedelta(hours=12),
            price_start=392.50,
            price_end=385.20,
            indicator_start=58.2,
            indicator_end=65.8,
            lookback_bars=10,
            strength=Strength.WEAK,
            confidence=0.58,
            timeframe="1D"
        ),
    ]
    
    scanner.signals.extend(sample_signals)
    
    # Add some historical outcomes
    for signal in sample_signals[:2]:
        outcome = DivergenceOutcome(
            signal=signal,
            outcome_price=signal.price_end * (1.05 if signal.is_bullish else 0.95),
            outcome_date=datetime.now(),
            return_pct=5.0 if signal.is_bullish else -5.0,
            success=True
        )
        scanner.outcomes.append(outcome)
    
    return scanner


if __name__ == "__main__":
    # Demo
    scanner = generate_sample_data()
    
    print("=== TECHNICAL DIVERGENCE SCANNER ===\n")
    
    # Summary
    summary = scanner.get_signal_summary()
    print(f"Signal Summary (48h):")
    print(f"  Total: {summary['total_signals']}")
    print(f"  Bullish: {summary['bullish']} | Bearish: {summary['bearish']}")
    print(f"  Strong: {summary['strong_signals']} | High Confidence: {summary['high_confidence']}")
    
    # Recent signals
    print(f"\n=== RECENT SIGNALS ===")
    for signal in scanner.get_recent_signals(hours=24):
        print(f"  {signal.summary()}")
        print(f"    Confidence: {signal.confidence:.0%} | Timeframe: {signal.timeframe}")
    
    # Accuracy
    print(f"\n=== ACCURACY STATS ===")
    stats = scanner.get_accuracy_stats()
    if 'accuracy' in stats:
        print(f"  Overall: {stats['accuracy']:.1f}%")
        print(f"  Bullish: {stats['bullish_accuracy']:.1f}%")
        print(f"  Bearish: {stats['bearish_accuracy']:.1f}%")
