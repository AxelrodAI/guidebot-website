"""Core Market Breadth calculation service"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from cachetools import TTLCache
import yfinance as yf

from config import config
from models import (
    AdvanceDecline, NewHighsLows, DMABreadth, McClellanData,
    BreadthAlert, AlertSeverity, AlertType, MarketBreadthSnapshot,
    BreadthDivergence
)


class BreadthService:
    """Service for calculating market breadth indicators"""
    
    def __init__(self):
        self.cache = TTLCache(maxsize=100, ttl=config.cache_ttl_minutes * 60)
        self._stock_data_cache: Dict[str, pd.DataFrame] = {}
        
    async def get_stock_data(self, symbol: str, period: str = "6mo") -> pd.DataFrame:
        """Fetch stock data with caching"""
        cache_key = f"{symbol}_{period}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            if not df.empty:
                self.cache[cache_key] = df
            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_multiple_stocks(self, symbols: List[str], period: str = "6mo") -> Dict[str, pd.DataFrame]:
        """Fetch multiple stocks concurrently"""
        tasks = [self.get_stock_data(sym, period) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {sym: df for sym, df in zip(symbols, results) if isinstance(df, pd.DataFrame) and not df.empty}
    
    def calculate_advance_decline(self, stock_data: Dict[str, pd.DataFrame]) -> List[AdvanceDecline]:
        """Calculate advance/decline line from stock price changes"""
        # Get aligned dates across all stocks
        all_dates = set()
        for df in stock_data.values():
            all_dates.update(df.index.date)
        dates = sorted(all_dates)[-90:]  # Last 90 days
        
        ad_data = []
        cumulative_ad = 0
        ad_values = []
        
        for date in dates:
            advances = 0
            declines = 0
            unchanged = 0
            
            for symbol, df in stock_data.items():
                df_date = df[df.index.date == date]
                if not df_date.empty:
                    pct_change = df_date['Close'].pct_change().iloc[-1] if len(df_date) > 1 else 0
                    if pct_change > 0.001:
                        advances += 1
                    elif pct_change < -0.001:
                        declines += 1
                    else:
                        unchanged += 1
            
            if advances + declines > 0:
                ad_ratio = advances / (advances + declines)
                net_ad = advances - declines
                cumulative_ad += net_ad
                ad_values.append(cumulative_ad)
                
                # Calculate SMAs
                ad_10sma = np.mean(ad_values[-10:]) if len(ad_values) >= 10 else None
                ad_50sma = np.mean(ad_values[-50:]) if len(ad_values) >= 50 else None
                
                ad_data.append(AdvanceDecline(
                    date=datetime.combine(date, datetime.min.time()),
                    advances=advances,
                    declines=declines,
                    unchanged=unchanged,
                    ad_ratio=ad_ratio,
                    ad_line_value=cumulative_ad,
                    ad_line_10sma=ad_10sma,
                    ad_line_50sma=ad_50sma
                ))
        
        return ad_data
    
    def calculate_new_highs_lows(self, stock_data: Dict[str, pd.DataFrame], lookback: int = 52 * 5) -> List[NewHighsLows]:
        """Calculate new 52-week highs and lows"""
        all_dates = set()
        for df in stock_data.values():
            all_dates.update(df.index.date)
        dates = sorted(all_dates)[-30:]  # Last 30 days
        
        hl_data = []
        
        for date in dates:
            new_highs = 0
            new_lows = 0
            
            for symbol, df in stock_data.items():
                # Get data up to and including this date
                df_to_date = df[df.index.date <= date]
                if len(df_to_date) >= lookback:
                    high_52w = df_to_date['High'].tail(lookback).max()
                    low_52w = df_to_date['Low'].tail(lookback).min()
                    current_close = df_to_date['Close'].iloc[-1]
                    
                    # Check if today's close is a new high or low
                    if current_close >= high_52w * 0.99:  # Within 1% of 52w high
                        new_highs += 1
                    elif current_close <= low_52w * 1.01:  # Within 1% of 52w low
                        new_lows += 1
            
            total = new_highs + new_lows
            hl_data.append(NewHighsLows(
                date=datetime.combine(date, datetime.min.time()),
                new_highs=new_highs,
                new_lows=new_lows,
                net_new_highs=new_highs - new_lows,
                highs_lows_ratio=new_highs / total if total > 0 else 0.5
            ))
        
        return hl_data
    
    def calculate_dma_breadth(self, stock_data: Dict[str, pd.DataFrame]) -> DMABreadth:
        """Calculate % of stocks above 50/200 DMA"""
        above_50 = 0
        above_200 = 0
        total = 0
        
        for symbol, df in stock_data.items():
            if len(df) >= 200:
                current_price = df['Close'].iloc[-1]
                ma_50 = df['Close'].tail(50).mean()
                ma_200 = df['Close'].tail(200).mean()
                
                if current_price > ma_50:
                    above_50 += 1
                if current_price > ma_200:
                    above_200 += 1
                total += 1
        
        return DMABreadth(
            date=datetime.utcnow(),
            above_50dma_count=above_50,
            above_50dma_pct=round(above_50 / total * 100, 2) if total > 0 else 0,
            above_200dma_count=above_200,
            above_200dma_pct=round(above_200 / total * 100, 2) if total > 0 else 0,
            total_stocks=total
        )
    
    def calculate_mcclellan(self, ad_data: List[AdvanceDecline]) -> McClellanData:
        """Calculate McClellan Oscillator and Summation Index"""
        if not ad_data:
            return McClellanData(
                date=datetime.utcnow(),
                oscillator=0,
                summation_index=0,
                oscillator_signal="neutral"
            )
        
        # Extract net advances (advances - declines)
        net_advances = [ad.advances - ad.declines for ad in ad_data]
        
        if len(net_advances) < 39:
            return McClellanData(
                date=datetime.utcnow(),
                oscillator=0,
                summation_index=0,
                oscillator_signal="neutral"
            )
        
        # Calculate EMAs
        df = pd.DataFrame({'net_ad': net_advances})
        ema_19 = df['net_ad'].ewm(span=19, adjust=False).mean().iloc[-1]
        ema_39 = df['net_ad'].ewm(span=39, adjust=False).mean().iloc[-1]
        
        # McClellan Oscillator = 19-day EMA - 39-day EMA
        oscillator = ema_19 - ema_39
        
        # McClellan Summation Index = running total of oscillator values
        oscillator_series = df['net_ad'].ewm(span=19, adjust=False).mean() - df['net_ad'].ewm(span=39, adjust=False).mean()
        summation_index = oscillator_series.sum()
        
        # Calculate 5-day SMA of oscillator
        osc_5sma = oscillator_series.tail(5).mean() if len(oscillator_series) >= 5 else None
        
        # Determine signal
        if oscillator > config.mcclellan_overbought:
            signal = "overbought"
        elif oscillator < config.mcclellan_oversold:
            signal = "oversold"
        elif oscillator > 0:
            signal = "bullish"
        elif oscillator < 0:
            signal = "bearish"
        else:
            signal = "neutral"
        
        return McClellanData(
            date=datetime.utcnow(),
            oscillator=round(oscillator, 2),
            summation_index=round(summation_index, 2),
            oscillator_signal=signal,
            oscillator_5sma=round(osc_5sma, 2) if osc_5sma else None
        )
    
    def detect_divergences(
        self, 
        index_data: pd.DataFrame, 
        ad_data: List[AdvanceDecline],
        lookback_days: int = 20
    ) -> List[BreadthDivergence]:
        """Detect breadth divergences from index"""
        divergences = []
        
        if not ad_data or index_data.empty or len(ad_data) < lookback_days:
            return divergences
        
        # Get index change over lookback period
        index_start = index_data['Close'].iloc[-lookback_days]
        index_end = index_data['Close'].iloc[-1]
        index_change_pct = ((index_end - index_start) / index_start) * 100
        
        # Get A/D line change over same period
        ad_start = ad_data[-lookback_days].ad_line_value
        ad_end = ad_data[-1].ad_line_value
        ad_change = ad_end - ad_start
        
        # Normalize A/D change to percentage scale (rough approximation)
        total_stocks = len(config.sample_stocks)
        ad_change_normalized = (ad_change / total_stocks) * 100 if total_stocks > 0 else 0
        
        # Check for divergence
        if index_change_pct > config.divergence_threshold_pct and ad_change_normalized < -1:
            # Index up, breadth down = bearish divergence
            divergences.append(BreadthDivergence(
                date=datetime.utcnow(),
                divergence_type="bearish",
                index_change_pct=round(index_change_pct, 2),
                breadth_change_pct=round(ad_change_normalized, 2),
                divergence_magnitude=abs(index_change_pct - ad_change_normalized),
                indicator="advance_decline",
                message=f"Bearish divergence: Index up {index_change_pct:.1f}% but A/D line declining. Fewer stocks participating in rally."
            ))
        elif index_change_pct < -config.divergence_threshold_pct and ad_change_normalized > 1:
            # Index down, breadth up = bullish divergence
            divergences.append(BreadthDivergence(
                date=datetime.utcnow(),
                divergence_type="bullish",
                index_change_pct=round(index_change_pct, 2),
                breadth_change_pct=round(ad_change_normalized, 2),
                divergence_magnitude=abs(index_change_pct - ad_change_normalized),
                indicator="advance_decline",
                message=f"Bullish divergence: Index down {abs(index_change_pct):.1f}% but A/D line improving. Breadth strengthening under the surface."
            ))
        
        return divergences
    
    def generate_alerts(
        self,
        mcclellan: McClellanData,
        dma_breadth: DMABreadth,
        new_highs_lows: NewHighsLows,
        divergences: List[BreadthDivergence]
    ) -> List[BreadthAlert]:
        """Generate alerts based on breadth conditions"""
        alerts = []
        
        # McClellan alerts
        if mcclellan.oscillator > config.mcclellan_extreme_overbought:
            alerts.append(BreadthAlert(
                alert_type=AlertType.MCCLELLAN_EXTREME,
                severity=AlertSeverity.HIGH,
                title="McClellan Oscillator Extremely Overbought",
                message=f"McClellan Oscillator at {mcclellan.oscillator:.1f} - extreme overbought territory. Potential for mean reversion.",
                data={"oscillator": mcclellan.oscillator}
            ))
        elif mcclellan.oscillator > config.mcclellan_overbought:
            alerts.append(BreadthAlert(
                alert_type=AlertType.MCCLELLAN_OVERBOUGHT,
                severity=AlertSeverity.MEDIUM,
                title="McClellan Oscillator Overbought",
                message=f"McClellan Oscillator at {mcclellan.oscillator:.1f} - overbought conditions.",
                data={"oscillator": mcclellan.oscillator}
            ))
        elif mcclellan.oscillator < config.mcclellan_extreme_oversold:
            alerts.append(BreadthAlert(
                alert_type=AlertType.MCCLELLAN_EXTREME,
                severity=AlertSeverity.HIGH,
                title="McClellan Oscillator Extremely Oversold",
                message=f"McClellan Oscillator at {mcclellan.oscillator:.1f} - extreme oversold territory. Watch for bounce.",
                data={"oscillator": mcclellan.oscillator}
            ))
        elif mcclellan.oscillator < config.mcclellan_oversold:
            alerts.append(BreadthAlert(
                alert_type=AlertType.MCCLELLAN_OVERSOLD,
                severity=AlertSeverity.MEDIUM,
                title="McClellan Oscillator Oversold",
                message=f"McClellan Oscillator at {mcclellan.oscillator:.1f} - oversold conditions.",
                data={"oscillator": mcclellan.oscillator}
            ))
        
        # DMA breadth alerts
        if dma_breadth.above_50dma_pct > config.dma_bullish_threshold:
            alerts.append(BreadthAlert(
                alert_type=AlertType.DMA_BULLISH,
                severity=AlertSeverity.LOW,
                title="Strong Breadth: High % Above 50 DMA",
                message=f"{dma_breadth.above_50dma_pct:.1f}% of stocks above 50-day moving average - broad participation.",
                data={"above_50dma_pct": dma_breadth.above_50dma_pct}
            ))
        elif dma_breadth.above_50dma_pct < config.dma_bearish_threshold:
            alerts.append(BreadthAlert(
                alert_type=AlertType.DMA_BEARISH,
                severity=AlertSeverity.MEDIUM,
                title="Weak Breadth: Low % Above 50 DMA",
                message=f"Only {dma_breadth.above_50dma_pct:.1f}% of stocks above 50-day moving average - narrow market.",
                data={"above_50dma_pct": dma_breadth.above_50dma_pct}
            ))
        
        # New highs/lows alerts
        if new_highs_lows.net_new_highs > 30:
            alerts.append(BreadthAlert(
                alert_type=AlertType.NEW_HIGHS_SURGE,
                severity=AlertSeverity.LOW,
                title="Surge in New Highs",
                message=f"{new_highs_lows.new_highs} new 52-week highs - strong upside participation.",
                data={"new_highs": new_highs_lows.new_highs, "new_lows": new_highs_lows.new_lows}
            ))
        elif new_highs_lows.net_new_highs < -30:
            alerts.append(BreadthAlert(
                alert_type=AlertType.NEW_LOWS_SURGE,
                severity=AlertSeverity.HIGH,
                title="Surge in New Lows",
                message=f"{new_highs_lows.new_lows} new 52-week lows - broad selling pressure.",
                data={"new_highs": new_highs_lows.new_highs, "new_lows": new_highs_lows.new_lows}
            ))
        
        # Divergence alerts
        for div in divergences:
            severity = AlertSeverity.HIGH if div.divergence_magnitude > 5 else AlertSeverity.MEDIUM
            alerts.append(BreadthAlert(
                alert_type=AlertType.DIVERGENCE_BEARISH if div.divergence_type == "bearish" else AlertType.DIVERGENCE_BULLISH,
                severity=severity,
                title=f"{div.divergence_type.title()} Divergence Detected",
                message=div.message,
                data={
                    "index_change": div.index_change_pct,
                    "breadth_change": div.breadth_change_pct,
                    "magnitude": div.divergence_magnitude
                }
            ))
        
        return alerts
    
    def calculate_health_score(
        self,
        ad_data: AdvanceDecline,
        dma_breadth: DMABreadth,
        mcclellan: McClellanData,
        new_highs_lows: NewHighsLows
    ) -> Tuple[float, str]:
        """Calculate overall market health score (0-100)"""
        score = 50  # Start neutral
        
        # A/D Ratio contribution (0-20 points)
        score += (ad_data.ad_ratio - 0.5) * 40  # +/- 20 points
        
        # DMA breadth contribution (0-30 points)
        score += (dma_breadth.above_50dma_pct - 50) * 0.3
        score += (dma_breadth.above_200dma_pct - 50) * 0.3
        
        # McClellan contribution (0-20 points)
        # Normalize oscillator to -1 to 1 range
        osc_normalized = max(-1, min(1, mcclellan.oscillator / 150))
        score += osc_normalized * 20
        
        # New highs/lows contribution (0-10 points)
        score += (new_highs_lows.highs_lows_ratio - 0.5) * 20
        
        # Clamp to 0-100
        score = max(0, min(100, score))
        
        # Determine trend (would need historical data for real trend)
        if score > 60:
            trend = "bullish"
        elif score < 40:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return round(score, 1), trend
    
    async def get_full_snapshot(self) -> MarketBreadthSnapshot:
        """Get complete market breadth snapshot"""
        # Fetch all stock data
        stock_data = await self.get_multiple_stocks(config.sample_stocks, period="1y")
        index_data = await self.get_stock_data(config.index_symbol, period="3mo")
        
        if not stock_data or index_data.empty:
            raise ValueError("Unable to fetch market data")
        
        # Calculate all indicators
        ad_data = self.calculate_advance_decline(stock_data)
        new_highs_lows_data = self.calculate_new_highs_lows(stock_data)
        dma_breadth = self.calculate_dma_breadth(stock_data)
        mcclellan = self.calculate_mcclellan(ad_data)
        
        # Detect divergences
        divergences = self.detect_divergences(index_data, ad_data)
        
        # Generate alerts
        latest_ad = ad_data[-1] if ad_data else AdvanceDecline(
            date=datetime.utcnow(), advances=0, declines=0, unchanged=0, 
            ad_ratio=0.5, ad_line_value=0
        )
        latest_hl = new_highs_lows_data[-1] if new_highs_lows_data else NewHighsLows(
            date=datetime.utcnow(), new_highs=0, new_lows=0, net_new_highs=0, highs_lows_ratio=0.5
        )
        
        alerts = self.generate_alerts(mcclellan, dma_breadth, latest_hl, divergences)
        
        # Calculate health score
        health_score, health_trend = self.calculate_health_score(
            latest_ad, dma_breadth, mcclellan, latest_hl
        )
        
        # Get index info
        index_price = index_data['Close'].iloc[-1]
        index_prev = index_data['Close'].iloc[-2] if len(index_data) > 1 else index_price
        index_change_pct = ((index_price - index_prev) / index_prev) * 100
        
        return MarketBreadthSnapshot(
            index_symbol=config.index_symbol,
            index_price=round(index_price, 2),
            index_change_pct=round(index_change_pct, 2),
            advance_decline=latest_ad,
            new_highs_lows=latest_hl,
            dma_breadth=dma_breadth,
            mcclellan=mcclellan,
            health_score=health_score,
            health_trend=health_trend,
            alerts=alerts
        )


# Global service instance
breadth_service = BreadthService()
