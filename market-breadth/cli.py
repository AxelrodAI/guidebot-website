"""CLI for Market Breadth Dashboard"""
import asyncio
import argparse
import json
import sys
import io
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from breadth_service import breadth_service
from config import config


async def show_snapshot():
    """Display full market breadth snapshot"""
    print("\n[MARKET BREADTH SNAPSHOT]")
    print("=" * 60)
    
    try:
        snapshot = await breadth_service.get_full_snapshot()
        
        print(f"\n>> {snapshot.index_symbol}: ${snapshot.index_price:.2f} ({snapshot.index_change_pct:+.2f}%)")
        print(f">> Health Score: {snapshot.health_score:.0f}/100 ({snapshot.health_trend})")
        
        print(f"\n[Advance/Decline]")
        ad = snapshot.advance_decline
        print(f"   Advancing: {ad.advances} | Declining: {ad.declines} | Unchanged: {ad.unchanged}")
        print(f"   A/D Ratio: {ad.ad_ratio:.2f}")
        print(f"   A/D Line: {ad.ad_line_value:.0f}")
        
        print(f"\n[New Highs/Lows]")
        hl = snapshot.new_highs_lows
        print(f"   New Highs: {hl.new_highs} | New Lows: {hl.new_lows}")
        print(f"   Net: {hl.net_new_highs:+d}")
        
        print(f"\n[DMA Breadth]")
        dma = snapshot.dma_breadth
        print(f"   Above 50 DMA: {dma.above_50dma_pct:.1f}% ({dma.above_50dma_count}/{dma.total_stocks})")
        print(f"   Above 200 DMA: {dma.above_200dma_pct:.1f}% ({dma.above_200dma_count}/{dma.total_stocks})")
        
        print(f"\n[McClellan Oscillator]")
        mc = snapshot.mcclellan
        print(f"   Oscillator: {mc.oscillator:.1f} ({mc.oscillator_signal})")
        print(f"   Summation Index: {mc.summation_index:.1f}")
        
        if snapshot.alerts:
            print(f"\n[!] Active Alerts ({len(snapshot.alerts)}):")
            for alert in snapshot.alerts:
                severity = "!!!" if alert.severity.value in ["high", "critical"] else "!"
                print(f"   [{severity}] {alert.title}")
                print(f"       {alert.message}")
        else:
            print(f"\n[OK] No active alerts")
        
        print(f"\nTimestamp: {snapshot.timestamp.isoformat()}")
        
    except Exception as e:
        print(f"[ERROR] {e}")


async def show_mcclellan():
    """Display McClellan Oscillator details"""
    print("\n[McCLELLAN OSCILLATOR ANALYSIS]")
    print("=" * 60)
    
    try:
        stock_data = await breadth_service.get_multiple_stocks(config.sample_stocks, period="6mo")
        ad_data = breadth_service.calculate_advance_decline(stock_data)
        mcclellan = breadth_service.calculate_mcclellan(ad_data)
        
        print(f"\n   Oscillator Value: {mcclellan.oscillator:.2f}")
        print(f"   Summation Index: {mcclellan.summation_index:.2f}")
        print(f"   Signal: {mcclellan.oscillator_signal}")
        if mcclellan.oscillator_5sma:
            print(f"   5-day SMA: {mcclellan.oscillator_5sma:.2f}")
        
        # Interpretation
        print(f"\n[Interpretation]")
        if mcclellan.oscillator > 150:
            print("   Extremely overbought - potential for pullback")
        elif mcclellan.oscillator > 100:
            print("   Overbought - market breadth strong but extended")
        elif mcclellan.oscillator > 0:
            print("   Bullish - positive breadth momentum")
        elif mcclellan.oscillator > -100:
            print("   Bearish - negative breadth momentum")
        elif mcclellan.oscillator > -150:
            print("   Oversold - market breadth weak but may bounce")
        else:
            print("   Extremely oversold - potential for mean reversion")
            
    except Exception as e:
        print(f"[ERROR] {e}")


async def show_dma_breadth():
    """Display DMA breadth analysis"""
    print("\n[DMA BREADTH ANALYSIS]")
    print("=" * 60)
    
    try:
        stock_data = await breadth_service.get_multiple_stocks(config.sample_stocks, period="1y")
        dma = breadth_service.calculate_dma_breadth(stock_data)
        
        print(f"\n   Stocks Analyzed: {dma.total_stocks}")
        print(f"\n   Above 50-day MA: {dma.above_50dma_count} ({dma.above_50dma_pct:.1f}%)")
        print(f"   Above 200-day MA: {dma.above_200dma_count} ({dma.above_200dma_pct:.1f}%)")
        
        # Visual bar (ASCII safe)
        pct_50 = int(dma.above_50dma_pct / 5)
        pct_200 = int(dma.above_200dma_pct / 5)
        print(f"\n   50 DMA:  [{'#' * pct_50}{'-' * (20 - pct_50)}] {dma.above_50dma_pct:.0f}%")
        print(f"   200 DMA: [{'#' * pct_200}{'-' * (20 - pct_200)}] {dma.above_200dma_pct:.0f}%")
        
        # Interpretation
        print(f"\n[Interpretation]")
        if dma.above_50dma_pct > 70:
            print("   [+] Strong participation - most stocks in uptrends")
        elif dma.above_50dma_pct > 50:
            print("   [~] Moderate participation - mixed market")
        else:
            print("   [-] Weak participation - few stocks leading")
            
    except Exception as e:
        print(f"[ERROR] {e}")


async def show_alerts():
    """Display current alerts"""
    print("\n[MARKET BREADTH ALERTS]")
    print("=" * 60)
    
    try:
        snapshot = await breadth_service.get_full_snapshot()
        
        if not snapshot.alerts:
            print("\n   [OK] No active alerts - market breadth is within normal ranges")
        else:
            for alert in snapshot.alerts:
                severity_markers = {
                    "low": "[LOW]",
                    "medium": "[MED]",
                    "high": "[HIGH]",
                    "critical": "[CRIT]"
                }
                marker = severity_markers.get(alert.severity.value, "[?]")
                
                print(f"\n{marker} {alert.title}")
                print(f"   Type: {alert.alert_type.value}")
                print(f"   {alert.message}")
                if alert.data:
                    print(f"   Data: {json.dumps(alert.data)}")
                    
    except Exception as e:
        print(f"[ERROR] {e}")


async def show_summary():
    """Display voice-friendly summary"""
    print("\n[MARKET BREADTH SUMMARY]")
    print("=" * 60)
    
    try:
        snapshot = await breadth_service.get_full_snapshot()
        
        # Build summary
        direction = "up" if snapshot.index_change_pct > 0 else "down"
        
        print(f"""
{snapshot.index_symbol} is {direction} {abs(snapshot.index_change_pct):.1f}% at ${snapshot.index_price:.2f}.

Market health score is {snapshot.health_score:.0f} out of 100, rated as {snapshot.health_trend}.

{snapshot.dma_breadth.above_50dma_pct:.0f}% of stocks are above their 50-day moving average.
{snapshot.dma_breadth.above_200dma_pct:.0f}% are above their 200-day.

Today shows {snapshot.advance_decline.advances} advancing stocks versus {snapshot.advance_decline.declines} declining.

The McClellan Oscillator is at {snapshot.mcclellan.oscillator:.1f}, which is {snapshot.mcclellan.oscillator_signal}.
""")
        
        if snapshot.alerts:
            high_alerts = [a for a in snapshot.alerts if a.severity.value in ["high", "critical"]]
            if high_alerts:
                print(f"[!] Important: {len(high_alerts)} high-priority alert(s):")
                for a in high_alerts[:3]:
                    print(f"   * {a.title}")
                    
    except Exception as e:
        print(f"[ERROR] {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Market Breadth Dashboard CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py snapshot    - Full market breadth snapshot
  python cli.py mcclellan   - McClellan Oscillator details
  python cli.py dma         - DMA breadth analysis
  python cli.py alerts      - Current alerts
  python cli.py summary     - Voice-friendly summary
        """
    )
    
    parser.add_argument(
        "command",
        choices=["snapshot", "mcclellan", "dma", "alerts", "summary"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    commands = {
        "snapshot": show_snapshot,
        "mcclellan": show_mcclellan,
        "dma": show_dma_breadth,
        "alerts": show_alerts,
        "summary": show_summary
    }
    
    asyncio.run(commands[args.command]())


if __name__ == "__main__":
    main()
