#!/usr/bin/env python3
"""
Macro Economic Calendar + Event Risk Tracker
Track Fed meetings, CPI/PPI, jobs reports, GDP, retail sales, PMI.
Show estimates vs actual, historical market reactions, countdown timers.

Author: PM3
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import pandas as pd
import numpy as np

# Configuration
DATA_DIR = Path(__file__).parent
EVENTS_CACHE = DATA_DIR / "events_data.json"
HISTORY_FILE = DATA_DIR / "historical_reactions.json"

# Major Economic Events
ECONOMIC_EVENTS = {
    "fed_meeting": {
        "name": "FOMC Meeting / Fed Decision",
        "impact": "HIGH",
        "typical_reaction": "High volatility in equities, bonds, USD",
        "frequency": "8x per year"
    },
    "cpi": {
        "name": "Consumer Price Index (CPI)",
        "impact": "HIGH",
        "typical_reaction": "Bonds and growth stocks sensitive",
        "frequency": "Monthly"
    },
    "ppi": {
        "name": "Producer Price Index (PPI)",
        "impact": "MEDIUM",
        "typical_reaction": "Leading indicator for CPI",
        "frequency": "Monthly"
    },
    "nfp": {
        "name": "Non-Farm Payrolls (Jobs Report)",
        "impact": "HIGH",
        "typical_reaction": "Major market mover, first Friday monthly",
        "frequency": "Monthly"
    },
    "gdp": {
        "name": "GDP Growth",
        "impact": "HIGH",
        "typical_reaction": "Quarterly economic health check",
        "frequency": "Quarterly"
    },
    "retail_sales": {
        "name": "Retail Sales",
        "impact": "MEDIUM",
        "typical_reaction": "Consumer spending indicator",
        "frequency": "Monthly"
    },
    "pmi_manufacturing": {
        "name": "ISM Manufacturing PMI",
        "impact": "MEDIUM",
        "typical_reaction": ">50 expansion, <50 contraction",
        "frequency": "Monthly"
    },
    "pmi_services": {
        "name": "ISM Services PMI",
        "impact": "MEDIUM",
        "typical_reaction": ">50 expansion, <50 contraction",
        "frequency": "Monthly"
    },
    "unemployment_claims": {
        "name": "Initial Jobless Claims",
        "impact": "LOW",
        "typical_reaction": "Weekly labor market pulse",
        "frequency": "Weekly"
    },
    "consumer_confidence": {
        "name": "Consumer Confidence",
        "impact": "MEDIUM",
        "typical_reaction": "Forward-looking consumer sentiment",
        "frequency": "Monthly"
    },
    "housing_starts": {
        "name": "Housing Starts",
        "impact": "LOW",
        "typical_reaction": "Housing market health",
        "frequency": "Monthly"
    },
    "pce": {
        "name": "PCE Price Index (Fed's preferred inflation)",
        "impact": "HIGH",
        "typical_reaction": "Fed's key inflation metric",
        "frequency": "Monthly"
    }
}


def load_cache():
    """Load cached events data."""
    if EVENTS_CACHE.exists():
        with open(EVENTS_CACHE) as f:
            return json.load(f)
    return {"events": [], "last_updated": None}


def save_cache(data):
    """Save events data to cache."""
    data["last_updated"] = datetime.now().isoformat()
    with open(EVENTS_CACHE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_historical():
    """Load historical reactions data."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {"reactions": []}


def save_historical(history):
    """Save historical reactions."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)


def get_spy_reaction(date, event_type):
    """
    Get SPY price reaction on event day.
    Returns % change from previous close to event day close.
    """
    try:
        spy = yf.Ticker("SPY")
        
        # Get data around the date
        start = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d")
        end = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")
        
        hist = spy.history(start=start, end=end)
        
        if hist.empty:
            return None
        
        # Find the event date and previous trading day
        event_idx = hist.index.get_indexer([pd.Timestamp(date)], method='nearest')[0]
        
        if event_idx > 0:
            prev_close = hist.iloc[event_idx - 1]['Close']
            event_close = hist.iloc[event_idx]['Close']
            
            pct_change = ((event_close - prev_close) / prev_close) * 100
            
            return {
                "date": date,
                "prev_close": round(prev_close, 2),
                "event_close": round(event_close, 2),
                "change_pct": round(pct_change, 2),
                "direction": "up" if pct_change > 0 else "down" if pct_change < 0 else "flat"
            }
    except Exception as e:
        return {"error": str(e)}
    
    return None


def calculate_countdown(event_date):
    """Calculate time until event."""
    now = datetime.now()
    
    if isinstance(event_date, str):
        event_dt = datetime.strptime(event_date, "%Y-%m-%d")
    else:
        event_dt = event_date
    
    # Set event time to 8:30 AM ET (typical release time)
    event_dt = event_dt.replace(hour=8, minute=30)
    
    delta = event_dt - now
    
    if delta.total_seconds() < 0:
        return {"status": "PASSED", "days": 0, "hours": 0, "minutes": 0}
    
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    if days == 0 and hours < 12:
        urgency = "IMMINENT"
    elif days == 0:
        urgency = "TODAY"
    elif days <= 2:
        urgency = "SOON"
    else:
        urgency = "UPCOMING"
    
    return {
        "status": urgency,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "countdown_str": f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
    }


def generate_sample_calendar():
    """
    Generate sample economic calendar data.
    In production, this would pull from economic calendar APIs.
    """
    today = datetime.now()
    
    # Sample upcoming events (would be pulled from real API)
    events = [
        {
            "id": "fomc-2026-01",
            "type": "fed_meeting",
            "name": "FOMC Rate Decision",
            "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "time": "14:00 ET",
            "estimate": "Hold at 4.25-4.50%",
            "prior": "4.25-4.50%",
            "impact": "HIGH",
            "notes": "January meeting - no major changes expected"
        },
        {
            "id": "cpi-2026-01",
            "type": "cpi",
            "name": "CPI (Jan)",
            "date": (today + timedelta(days=12)).strftime("%Y-%m-%d"),
            "time": "08:30 ET",
            "estimate": "2.9% YoY",
            "prior": "2.9% YoY",
            "impact": "HIGH",
            "notes": "Core CPI expected at 3.2%"
        },
        {
            "id": "nfp-2026-02",
            "type": "nfp",
            "name": "Non-Farm Payrolls (Jan)",
            "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "time": "08:30 ET",
            "estimate": "+180K",
            "prior": "+216K",
            "impact": "HIGH",
            "notes": "Unemployment rate expected at 4.1%"
        },
        {
            "id": "retail-2026-01",
            "type": "retail_sales",
            "name": "Retail Sales (Dec)",
            "date": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
            "time": "08:30 ET",
            "estimate": "+0.4%",
            "prior": "+0.7%",
            "impact": "MEDIUM",
            "notes": "Holiday spending impact"
        },
        {
            "id": "ppi-2026-01",
            "type": "ppi",
            "name": "PPI (Jan)",
            "date": (today + timedelta(days=14)).strftime("%Y-%m-%d"),
            "time": "08:30 ET",
            "estimate": "1.3% YoY",
            "prior": "1.0% YoY",
            "impact": "MEDIUM",
            "notes": "Producer inflation gauge"
        },
        {
            "id": "pmi-mfg-2026-02",
            "type": "pmi_manufacturing",
            "name": "ISM Manufacturing PMI (Jan)",
            "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "time": "10:00 ET",
            "estimate": "49.2",
            "prior": "49.3",
            "impact": "MEDIUM",
            "notes": "Manufacturing remains in contraction"
        },
        {
            "id": "pce-2026-01",
            "type": "pce",
            "name": "PCE Price Index (Dec)",
            "date": (today + timedelta(days=20)).strftime("%Y-%m-%d"),
            "time": "08:30 ET",
            "estimate": "2.6% YoY",
            "prior": "2.4% YoY",
            "impact": "HIGH",
            "notes": "Fed's preferred inflation measure"
        },
        {
            "id": "gdp-2025-q4",
            "type": "gdp",
            "name": "GDP Q4 2025 (Advance)",
            "date": (today + timedelta(days=25)).strftime("%Y-%m-%d"),
            "time": "08:30 ET",
            "estimate": "2.3%",
            "prior": "3.1%",
            "impact": "HIGH",
            "notes": "Q4 economic growth"
        }
    ]
    
    return events


def analyze_calendar():
    """Analyze upcoming events and calculate risk metrics."""
    events = generate_sample_calendar()
    
    analyzed = []
    high_risk_count = 0
    
    for event in events:
        countdown = calculate_countdown(event["date"])
        
        event_info = ECONOMIC_EVENTS.get(event["type"], {})
        
        analyzed_event = {
            **event,
            "countdown": countdown,
            "event_info": event_info,
            "typical_reaction": event_info.get("typical_reaction", "")
        }
        
        if event["impact"] == "HIGH" and countdown["status"] in ["IMMINENT", "TODAY", "SOON"]:
            high_risk_count += 1
            analyzed_event["alert"] = f"HIGH IMPACT event in {countdown['countdown_str']}"
        
        analyzed.append(analyzed_event)
    
    # Sort by date
    analyzed.sort(key=lambda x: x["date"])
    
    return {
        "events": analyzed,
        "total_events": len(analyzed),
        "high_impact_soon": high_risk_count,
        "risk_level": "HIGH" if high_risk_count >= 2 else "MEDIUM" if high_risk_count == 1 else "LOW",
        "generated_at": datetime.now().isoformat()
    }


def get_historical_reactions(event_type, num_events=10):
    """
    Get historical market reactions to event type.
    In production, would use real historical data.
    """
    # Sample historical data (would be real in production)
    sample_reactions = {
        "cpi": [
            {"date": "2024-12-11", "actual": "2.7%", "estimate": "2.7%", "spy_change": "+0.82%", "beat": "meet"},
            {"date": "2024-11-13", "actual": "2.6%", "estimate": "2.6%", "spy_change": "-0.29%", "beat": "meet"},
            {"date": "2024-10-10", "actual": "2.4%", "estimate": "2.3%", "spy_change": "-0.21%", "beat": "miss"},
            {"date": "2024-09-11", "actual": "2.5%", "estimate": "2.6%", "spy_change": "+1.07%", "beat": "beat"},
        ],
        "nfp": [
            {"date": "2025-01-10", "actual": "+216K", "estimate": "+160K", "spy_change": "-1.54%", "beat": "beat"},
            {"date": "2024-12-06", "actual": "+227K", "estimate": "+200K", "spy_change": "+0.25%", "beat": "beat"},
            {"date": "2024-11-01", "actual": "+12K", "estimate": "+100K", "spy_change": "+0.41%", "beat": "miss"},
        ],
        "fed_meeting": [
            {"date": "2024-12-18", "actual": "Cut 25bps", "estimate": "Cut 25bps", "spy_change": "-2.95%", "beat": "hawkish"},
            {"date": "2024-11-07", "actual": "Cut 25bps", "estimate": "Cut 25bps", "spy_change": "+0.74%", "beat": "meet"},
            {"date": "2024-09-18", "actual": "Cut 50bps", "estimate": "Cut 50bps", "spy_change": "+0.03%", "beat": "meet"},
        ]
    }
    
    reactions = sample_reactions.get(event_type, [])
    
    # Calculate stats
    if reactions:
        changes = [float(r["spy_change"].replace("%", "").replace("+", "")) for r in reactions]
        avg_move = np.mean(np.abs(changes))
        avg_direction = np.mean(changes)
        
        return {
            "event_type": event_type,
            "reactions": reactions[:num_events],
            "stats": {
                "avg_absolute_move": round(avg_move, 2),
                "avg_direction": round(avg_direction, 2),
                "tends_positive": avg_direction > 0.1,
                "tends_negative": avg_direction < -0.1,
                "high_volatility": avg_move > 1.0
            }
        }
    
    return {"event_type": event_type, "reactions": [], "stats": {}}


def generate_event_report():
    """Generate comprehensive event risk report."""
    calendar = analyze_calendar()
    
    report_lines = [
        "=" * 70,
        "MACRO ECONOMIC CALENDAR + EVENT RISK REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"RISK LEVEL: {calendar['risk_level']}",
        f"High-Impact Events Soon: {calendar['high_impact_soon']}",
        f"Total Upcoming Events: {calendar['total_events']}",
        "",
        "-" * 70,
        "UPCOMING EVENTS",
        "-" * 70,
    ]
    
    for event in calendar["events"]:
        countdown = event["countdown"]
        impact_emoji = {"HIGH": "[!!!]", "MEDIUM": "[!!]", "LOW": "[!]"}.get(event["impact"], "")
        
        report_lines.extend([
            "",
            f"{impact_emoji} {event['name']}",
            f"   Date: {event['date']} at {event['time']}",
            f"   Countdown: {countdown['countdown_str']} ({countdown['status']})",
            f"   Estimate: {event['estimate']} | Prior: {event['prior']}",
            f"   Notes: {event.get('notes', 'N/A')}",
        ])
        
        if event.get("alert"):
            report_lines.append(f"   >>> ALERT: {event['alert']}")
    
    # Add historical context for high-impact events
    report_lines.extend([
        "",
        "-" * 70,
        "HISTORICAL REACTIONS (SPY)",
        "-" * 70,
    ])
    
    for event_type in ["cpi", "nfp", "fed_meeting"]:
        hist = get_historical_reactions(event_type, 3)
        if hist.get("reactions"):
            event_name = ECONOMIC_EVENTS.get(event_type, {}).get("name", event_type)
            report_lines.extend([
                "",
                f"{event_name}:",
                f"   Avg Move: {hist['stats']['avg_absolute_move']}% | Direction Bias: {hist['stats']['avg_direction']:+.2f}%",
            ])
            for r in hist["reactions"][:3]:
                report_lines.append(f"   - {r['date']}: {r['actual']} vs {r['estimate']} -> SPY {r['spy_change']}")
    
    report_lines.extend(["", "=" * 70])
    
    return "\n".join(report_lines)


def export_to_json(output_file=None):
    """Export calendar to JSON."""
    output_file = output_file or (DATA_DIR / "macro_calendar.json")
    
    calendar = analyze_calendar()
    
    # Add historical reactions
    for event in calendar["events"]:
        hist = get_historical_reactions(event["type"], 5)
        event["historical"] = hist
    
    with open(output_file, "w") as f:
        json.dump(calendar, f, indent=2, default=str)
    
    return str(output_file)


if __name__ == "__main__":
    print(generate_event_report())
    
    json_file = export_to_json()
    print(f"\nExported to: {json_file}")
