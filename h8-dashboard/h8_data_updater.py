#!/usr/bin/env python3
"""
H.8 Data Updater - Fetches Fed H.8 data and outputs JSON for the dashboard.

Run daily or every Friday after 4:15 PM ET when new data is released.

Usage:
    python h8_data_updater.py
    
The script outputs h8_data.json which the dashboard reads.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import warnings

warnings.filterwarnings('ignore')

try:
    import pandas as pd
    from fredapi import Fred
except ImportError as e:
    print(f"Missing package: {e.name}")
    print("Install with: pip install fredapi pandas")
    sys.exit(1)


# =============================================================================
# H.8 SERIES CONFIGURATION
# =============================================================================

H8_SERIES = {
    # Loans
    "TOTLL": {"name": "Total Loans & Leases", "category": "loans"},
    "TOTCI": {"name": "C&I Loans", "category": "loans"},
    "RELACBW027SBOG": {"name": "Real Estate Loans", "category": "loans"},
    "CLSACBW027SBOG": {"name": "Consumer Loans", "category": "loans"},
    
    # Deposits
    "DPSACBW027SBOG": {"name": "Total Deposits", "category": "deposits"},
    "LTDACBW027SBOG": {"name": "Large Time Deposits", "category": "deposits"},
    
    # Other
    "TOTBKCR": {"name": "Total Bank Credit", "category": "other"},
    "SBCACBW027SBOG": {"name": "Securities", "category": "other"},
    "CASACBW027SBOG": {"name": "Cash Assets", "category": "other"},
}


def get_fred_api_key() -> Optional[str]:
    """Get FRED API key from environment or .env file."""
    api_key = os.environ.get("FRED_API_KEY")
    if api_key:
        return api_key
    
    # Check .env files
    for env_path in [Path(__file__).parent / ".env", Path.home() / ".env"]:
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("FRED_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    
    # Check parent directories
    parent_env = Path(__file__).parent.parent / "long-short-bot" / ".env"
    if parent_env.exists():
        with open(parent_env, "r") as f:
            for line in f:
                if line.strip().startswith("FRED_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    
    return None


def get_quarter_start(date: datetime) -> datetime:
    """Get the first day of the quarter for a given date."""
    quarter = (date.month - 1) // 3
    return datetime(date.year, quarter * 3 + 1, 1)


def get_quarter_label(date: datetime) -> str:
    """Get quarter label like 'Q1 2025'."""
    quarter = (date.month - 1) // 3 + 1
    return f"Q{quarter} {date.year}"


def fetch_series_data(fred: Fred, series_id: str, years: int = 6) -> Optional[pd.Series]:
    """Fetch a single series from FRED."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        data = fred.get_series(
            series_id,
            observation_start=start_date,
            observation_end=end_date
        )
        return data
    except Exception as e:
        print(f"  Warning: Could not fetch {series_id}: {e}")
        return None


def calculate_qtd_growth(data: pd.Series, as_of_date: datetime) -> Dict:
    """
    Calculate quarter-to-date growth for current and past 5 years.
    Returns weekly data points within the quarter.
    """
    results = {}
    current_year = as_of_date.year
    
    for year_offset in range(6):  # Current year + 5 historical years
        target_year = current_year - year_offset
        target_quarter = (as_of_date.month - 1) // 3 + 1
        
        # Get quarter start for this year
        quarter_start = datetime(target_year, (target_quarter - 1) * 3 + 1, 1)
        quarter_end = datetime(target_year, (target_quarter - 1) * 3 + 1, 1) + timedelta(days=92)
        
        # Filter data to this quarter
        mask = (data.index >= pd.Timestamp(quarter_start)) & (data.index < pd.Timestamp(quarter_end))
        quarter_data = data[mask]
        
        if len(quarter_data) < 2:
            continue
        
        # Calculate cumulative growth from quarter start
        base_value = quarter_data.iloc[0]
        growth_points = []
        
        for i, (date, value) in enumerate(quarter_data.items()):
            pct_change = ((value - base_value) / base_value) * 100
            week_num = i + 1
            growth_points.append({
                "week": week_num,
                "date": date.strftime("%Y-%m-%d"),
                "value": round(float(value), 2),
                "qtd_growth_pct": round(pct_change, 3)
            })
        
        year_label = f"{target_year}" if year_offset == 0 else f"{target_year}"
        results[year_label] = {
            "quarter": f"Q{target_quarter}",
            "data": growth_points
        }
    
    return results


def calculate_yoy_trends(data: pd.Series, weeks: int = 104) -> list:
    """Calculate year-over-year percentage changes."""
    if len(data) < 53:
        return []
    
    # Get last N weeks
    recent = data.iloc[-weeks:] if len(data) >= weeks else data
    
    results = []
    for date, value in recent.items():
        # Find value from 52 weeks ago
        target_date = date - timedelta(weeks=52)
        
        # Find closest date in data
        past_data = data[data.index <= target_date]
        if len(past_data) == 0:
            continue
        
        past_value = past_data.iloc[-1]
        yoy_pct = ((value - past_value) / past_value) * 100
        
        results.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(float(value), 2),
            "yoy_pct": round(yoy_pct, 2)
        })
    
    return results


def calculate_summary_stats(data: pd.Series) -> Dict:
    """Calculate summary statistics for a series."""
    if len(data) < 2:
        return {}
    
    latest = data.iloc[-1]
    latest_date = data.index[-1]
    
    # Week-over-week
    prev_week = data.iloc[-2] if len(data) >= 2 else None
    wow_chg = float(latest - prev_week) if prev_week is not None else None
    wow_pct = (wow_chg / prev_week * 100) if prev_week and prev_week != 0 else None
    
    # Year-over-year (52 weeks)
    prev_year = data.iloc[-53] if len(data) >= 53 else None
    yoy_chg = float(latest - prev_year) if prev_year is not None else None
    yoy_pct = (yoy_chg / prev_year * 100) if prev_year and prev_year != 0 else None
    
    # Quarter-to-date
    quarter_start = get_quarter_start(latest_date.to_pydatetime())
    quarter_data = data[data.index >= pd.Timestamp(quarter_start)]
    qtd_base = quarter_data.iloc[0] if len(quarter_data) > 0 else None
    qtd_chg = float(latest - qtd_base) if qtd_base is not None else None
    qtd_pct = (qtd_chg / qtd_base * 100) if qtd_base and qtd_base != 0 else None
    
    # 52-week sparkline (sampled to ~26 points)
    sparkline_data = data.iloc[-52::2] if len(data) >= 52 else data
    sparkline = [round(float(v), 1) for v in sparkline_data.values]
    
    return {
        "latest_value": round(float(latest), 2),
        "latest_date": latest_date.strftime("%Y-%m-%d"),
        "wow_chg": round(wow_chg, 2) if wow_chg is not None else None,
        "wow_pct": round(wow_pct, 3) if wow_pct is not None else None,
        "yoy_chg": round(yoy_chg, 2) if yoy_chg is not None else None,
        "yoy_pct": round(yoy_pct, 2) if yoy_pct is not None else None,
        "qtd_chg": round(qtd_chg, 2) if qtd_chg is not None else None,
        "qtd_pct": round(qtd_pct, 3) if qtd_pct is not None else None,
        "sparkline": sparkline
    }


def get_release_info() -> Dict:
    """
    Get H.8 release date info.
    H.8 is released every Friday at 4:15 PM ET.
    Data is as-of the prior Wednesday.
    """
    now = datetime.now()
    
    # Find the most recent Friday (release date)
    days_since_friday = (now.weekday() - 4) % 7
    last_friday = now - timedelta(days=days_since_friday)
    
    # Data as-of date is Wednesday before that Friday (2 days before)
    data_as_of = last_friday - timedelta(days=2)
    
    return {
        "release_date": last_friday.strftime("%Y-%m-%d"),
        "data_as_of": data_as_of.strftime("%Y-%m-%d"),
        "release_day": "Friday",
        "release_time": "4:15 PM ET",
        "next_release": (last_friday + timedelta(days=7)).strftime("%Y-%m-%d")
    }


def main():
    print("=" * 60)
    print("H.8 DATA UPDATER")
    print("=" * 60)
    
    api_key = get_fred_api_key()
    if not api_key:
        print("\n[ERROR] FRED API key not found!")
        print("Set FRED_API_KEY environment variable or add to .env file")
        sys.exit(1)
    
    try:
        fred = Fred(api_key=api_key)
        fred.get_series_info('TOTBKCR')
        print("[OK] Connected to FRED API")
    except Exception as e:
        print(f"[ERROR] Failed to connect to FRED: {e}")
        sys.exit(1)
    
    # Build output data structure
    output = {
        "meta": {
            "updated_at": datetime.now().isoformat(),
            "source": "Federal Reserve H.8 Release via FRED",
            **get_release_info()
        },
        "series": {},
        "qtd_comparison": {
            "loans": {},
            "deposits": {}
        },
        "yoy_trends": {}
    }
    
    # Fetch all series
    print("\nFetching H.8 data...")
    all_data = {}
    
    for series_id, info in H8_SERIES.items():
        print(f"  {info['name']} ({series_id})...")
        data = fetch_series_data(fred, series_id)
        
        if data is not None and len(data) > 0:
            all_data[series_id] = data
            
            # Calculate summary stats
            stats = calculate_summary_stats(data)
            output["series"][series_id] = {
                "name": info["name"],
                "category": info["category"],
                **stats
            }
            
            # Calculate YoY trends (for loans and deposits)
            if info["category"] in ["loans", "deposits"]:
                output["yoy_trends"][series_id] = {
                    "name": info["name"],
                    "category": info["category"],
                    "data": calculate_yoy_trends(data, 104)
                }
            
            # Calculate QTD comparison for key series
            if series_id in ["TOTLL", "TOTCI", "RELACBW027SBOG", "CLSACBW027SBOG"]:
                latest_date = data.index[-1].to_pydatetime()
                output["qtd_comparison"]["loans"][series_id] = {
                    "name": info["name"],
                    "quarters": calculate_qtd_growth(data, latest_date)
                }
            elif series_id in ["DPSACBW027SBOG", "LTDACBW027SBOG"]:
                latest_date = data.index[-1].to_pydatetime()
                output["qtd_comparison"]["deposits"][series_id] = {
                    "name": info["name"],
                    "quarters": calculate_qtd_growth(data, latest_date)
                }
    
    # Write JSON output
    output_path = Path(__file__).parent / "h8_data.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Data saved to: {output_path}")
    print(f"  Release date: {output['meta']['release_date']}")
    print(f"  Data as-of: {output['meta']['data_as_of']}")
    print(f"  Series count: {len(output['series'])}")
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
