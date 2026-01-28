"""
13F Holdings Change Tracker
Fetches SEC EDGAR 13F filings and tracks position changes for superinvestors
"""

import os
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import urllib.request
import urllib.error

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not installed. Excel output will be limited.")

from config import (
    SUPERINVESTORS, CHANGE_THRESHOLDS, SEC_EDGAR_BASE_URL,
    USER_AGENT, OUTPUT_DIR, CACHE_DIR
)


@dataclass
class Holding:
    """Represents a single 13F holding"""
    cusip: str
    name: str
    value: int  # in thousands
    shares: int
    share_type: str = "SH"
    investment_discretion: str = "SOLE"
    voting_authority_sole: int = 0
    voting_authority_shared: int = 0
    voting_authority_none: int = 0


@dataclass
class Filing:
    """Represents a 13F filing"""
    cik: str
    fund_name: str
    period_of_report: str
    filed_date: str
    accession_number: str
    holdings: List[Holding] = field(default_factory=list)


@dataclass
class PositionChange:
    """Represents a change in position between quarters"""
    cusip: str
    name: str
    fund_name: str
    change_type: str  # NEW, EXIT, INCREASE, DECREASE, UNCHANGED
    prev_shares: int
    curr_shares: int
    prev_value: int
    curr_value: int
    shares_change_pct: float
    value_change_pct: float


class SEC13FTracker:
    """Main tracker class for 13F filings"""
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._ensure_dirs()
        
    def _ensure_dirs(self):
        """Create output and cache directories"""
        Path(OUTPUT_DIR).mkdir(exist_ok=True)
        Path(CACHE_DIR).mkdir(exist_ok=True)
        
    def _make_request(self, url: str) -> Optional[bytes]:
        """Make HTTP request with proper headers for SEC EDGAR"""
        import gzip
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, application/xml, text/html"
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                
                # Handle gzip-compressed responses
                if response.headers.get('Content-Encoding') == 'gzip' or data[:2] == b'\x1f\x8b':
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass  # Not actually gzipped
                
                return data
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code}: {url}")
            return None
        except urllib.error.URLError as e:
            print(f"URL Error: {e.reason}")
            return None
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached data if available"""
        if not self.cache_enabled:
            return None
        cache_file = Path(CACHE_DIR) / f"{key}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def _set_cached(self, key: str, data: dict):
        """Cache data to file"""
        if not self.cache_enabled:
            return
        cache_file = Path(CACHE_DIR) / f"{key}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_filings_index(self, cik: str) -> Optional[dict]:
        """Get the filings index for a CIK"""
        # Normalize CIK (remove leading zeros for URL, pad for display)
        cik_num = str(int(cik))
        
        cache_key = f"filings_index_{cik}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = f"{SEC_EDGAR_BASE_URL}/submissions/CIK{cik}.json"
        
        data = self._make_request(url)
        if not data:
            return None
        
        try:
            result = json.loads(data)
            self._set_cached(cache_key, result)
            return result
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for CIK {cik}")
            return None
    
    def find_13f_filings(self, cik: str, limit: int = 4, include_amendments: bool = False) -> List[dict]:
        """Find 13F-HR filings for a CIK
        
        Args:
            cik: SEC CIK number
            limit: Maximum number of filings to return
            include_amendments: If False, prefer original filings over amendments
        """
        index = self.get_filings_index(cik)
        if not index:
            return []
        
        filings = []
        seen_periods = set()  # Track report periods to avoid duplicates
        recent = index.get("filings", {}).get("recent", {})
        
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A"):
                report_date = report_dates[i] if i < len(report_dates) else None
                is_amendment = "/A" in form
                
                # Skip amendments if we already have original for this period
                if not include_amendments and is_amendment and report_date in seen_periods:
                    continue
                
                # Skip if we already have a filing for this period (prefer non-amendments)
                if report_date in seen_periods:
                    continue
                
                if len(filings) < limit:
                    filings.append({
                        "form": form,
                        "accession_number": accessions[i],
                        "filing_date": filing_dates[i],
                        "report_date": report_date,
                        "cik": cik,
                        "is_amendment": is_amendment
                    })
                    if report_date:
                        seen_periods.add(report_date)
        
        return filings
    
    def get_13f_holdings(self, cik: str, accession_number: str) -> List[Holding]:
        """Fetch and parse 13F holdings from XML"""
        import re
        
        # Format accession number for URL (remove dashes)
        acc_formatted = accession_number.replace("-", "")
        cik_num = str(int(cik))
        
        cache_key = f"holdings_{cik}_{acc_formatted}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Holding(**h) for h in cached]
        
        # Use www.sec.gov for filing directory listing
        base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_formatted}"
        
        # Get directory listing HTML
        dir_html = self._make_request(f"{base_url}/")
        
        if not dir_html:
            return []
        
        try:
            html_content = dir_html.decode('utf-8', errors='ignore')
            
            # Find XML files from directory listing
            xml_files = re.findall(r'href="([^"]*\.xml)"', html_content, re.IGNORECASE)
            
            # Find the infotable XML file (usually contains "infotable" or is a numeric name)
            xml_file = None
            for f in xml_files:
                f_lower = f.lower()
                # Get just the filename
                fname = f.split('/')[-1]
                if "infotable" in f_lower:
                    xml_file = fname
                    break
            
            if not xml_file:
                # Try numeric XML files (common pattern for infotables)
                for f in xml_files:
                    fname = f.split('/')[-1]
                    if fname.replace('.xml', '').replace('.XML', '').isdigit():
                        xml_file = fname
                        break
            
            if not xml_file:
                # Try any non-primary XML
                for f in xml_files:
                    fname = f.split('/')[-1]
                    if 'primary' not in fname.lower():
                        xml_file = fname
                        break
            
            if not xml_file:
                print(f"No infotable XML found for {accession_number}")
                return []
            
            # Fetch the XML
            xml_url = f"{base_url}/{xml_file}"
            xml_data = self._make_request(xml_url)
            
            if not xml_data:
                return []
            
            holdings = self._parse_13f_xml(xml_data)
            
            # Cache the results
            self._set_cached(cache_key, [
                {
                    "cusip": h.cusip, "name": h.name, "value": h.value,
                    "shares": h.shares, "share_type": h.share_type,
                    "investment_discretion": h.investment_discretion,
                    "voting_authority_sole": h.voting_authority_sole,
                    "voting_authority_shared": h.voting_authority_shared,
                    "voting_authority_none": h.voting_authority_none
                }
                for h in holdings
            ])
            
            return holdings
            
        except Exception as e:
            print(f"Error fetching holdings: {e}")
            return []
    
    def _parse_13f_xml(self, xml_data: bytes) -> List[Holding]:
        """Parse 13F XML infotable"""
        import re
        holdings = []
        
        try:
            # Handle namespace issues
            xml_str = xml_data.decode('utf-8', errors='ignore')
            
            # Strategy: Remove namespace prefixes from element tags but keep the document valid
            # First, remove xsi:schemaLocation attribute entirely (causes issues)
            xml_str = re.sub(r'\s+xsi:schemaLocation="[^"]*"', '', xml_str)
            
            # Remove xmlns:xsi declaration
            xml_str = re.sub(r'\s+xmlns:xsi="[^"]*"', '', xml_str)
            
            # Remove other xmlns declarations
            xml_str = re.sub(r'\s+xmlns(:\w+)?="[^"]*"', '', xml_str)
            
            # Remove namespace prefixes from element tags (e.g., n1:infoTable -> infoTable)
            xml_str = re.sub(r'<(/?)(\w+):', r'<\1', xml_str)
            
            root = ET.fromstring(xml_str)
            
            # Find all infoTable entries (case-insensitive search)
            for elem in root.iter():
                tag_lower = elem.tag.lower()
                if 'infotable' in tag_lower and 'informationtable' not in tag_lower:
                    holding = self._parse_holding_element(elem)
                    if holding:
                        holdings.append(holding)
            
            # If no holdings found, try alternative structure
            if not holdings:
                for elem in root.iter():
                    if elem.tag.endswith('infoTable') or 'InfoTable' in elem.tag:
                        holding = self._parse_holding_element(elem)
                        if holding:
                            holdings.append(holding)
                            
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        
        return holdings
    
    def _parse_holding_element(self, elem: ET.Element) -> Optional[Holding]:
        """Parse a single holding element from 13F XML"""
        def get_text(parent, tag_patterns):
            for child in parent.iter():
                tag_lower = child.tag.lower()
                for pattern in tag_patterns:
                    if pattern in tag_lower:
                        return child.text or ""
            return ""
        
        def get_int(parent, tag_patterns, default=0):
            text = get_text(parent, tag_patterns)
            try:
                return int(text.replace(",", ""))
            except (ValueError, AttributeError):
                return default
        
        cusip = get_text(elem, ['cusip'])
        name = get_text(elem, ['nameofissuer', 'issuer'])
        value = get_int(elem, ['value'])
        shares = get_int(elem, ['sshprnamt', 'shares'])
        share_type = get_text(elem, ['sshprnamttype', 'type']) or "SH"
        
        if cusip and (value > 0 or shares > 0):
            return Holding(
                cusip=cusip,
                name=name,
                value=value,
                shares=shares,
                share_type=share_type
            )
        return None
    
    def compare_holdings(
        self, 
        prev_holdings: List[Holding], 
        curr_holdings: List[Holding],
        fund_name: str
    ) -> List[PositionChange]:
        """Compare holdings between two quarters and identify changes"""
        changes = []
        
        # Index by CUSIP
        prev_by_cusip = {h.cusip: h for h in prev_holdings}
        curr_by_cusip = {h.cusip: h for h in curr_holdings}
        
        all_cusips = set(prev_by_cusip.keys()) | set(curr_by_cusip.keys())
        
        for cusip in all_cusips:
            prev = prev_by_cusip.get(cusip)
            curr = curr_by_cusip.get(cusip)
            
            if prev and not curr:
                # EXIT - position closed
                changes.append(PositionChange(
                    cusip=cusip,
                    name=prev.name,
                    fund_name=fund_name,
                    change_type="EXIT",
                    prev_shares=prev.shares,
                    curr_shares=0,
                    prev_value=prev.value,
                    curr_value=0,
                    shares_change_pct=-100.0,
                    value_change_pct=-100.0
                ))
            elif curr and not prev:
                # NEW - new position
                changes.append(PositionChange(
                    cusip=cusip,
                    name=curr.name,
                    fund_name=fund_name,
                    change_type="NEW",
                    prev_shares=0,
                    curr_shares=curr.shares,
                    prev_value=0,
                    curr_value=curr.value,
                    shares_change_pct=float('inf'),
                    value_change_pct=float('inf')
                ))
            else:
                # Position exists in both - calculate change
                shares_pct = ((curr.shares - prev.shares) / prev.shares * 100) if prev.shares > 0 else 0
                value_pct = ((curr.value - prev.value) / prev.value * 100) if prev.value > 0 else 0
                
                if shares_pct > 0:
                    change_type = "INCREASE"
                elif shares_pct < 0:
                    change_type = "DECREASE"
                else:
                    change_type = "UNCHANGED"
                
                changes.append(PositionChange(
                    cusip=cusip,
                    name=curr.name,
                    fund_name=fund_name,
                    change_type=change_type,
                    prev_shares=prev.shares,
                    curr_shares=curr.shares,
                    prev_value=prev.value,
                    curr_value=curr.value,
                    shares_change_pct=shares_pct,
                    value_change_pct=value_pct
                ))
        
        return changes
    
    def filter_significant_changes(
        self, 
        changes: List[PositionChange],
        threshold_pct: float = None
    ) -> List[PositionChange]:
        """Filter for significant changes (NEW, EXIT, or >= threshold %)"""
        if threshold_pct is None:
            threshold_pct = CHANGE_THRESHOLDS["significant_change_pct"]
        
        significant = []
        for change in changes:
            if change.change_type in ("NEW", "EXIT"):
                significant.append(change)
            elif abs(change.shares_change_pct) >= threshold_pct:
                significant.append(change)
        
        return significant
    
    def track_fund(self, fund_name: str, cik: str) -> Dict:
        """Track a single fund's 13F changes"""
        print(f"\nTracking {fund_name} (CIK: {cik})...")
        
        filings = self.find_13f_filings(cik, limit=2)
        
        if len(filings) < 2:
            print(f"  Not enough filings found for comparison")
            return {"fund": fund_name, "error": "insufficient_filings", "filings_found": len(filings)}
        
        # Get current and previous quarter holdings
        curr_filing = filings[0]
        prev_filing = filings[1]
        
        print(f"  Current: {curr_filing['report_date']} (filed {curr_filing['filing_date']})")
        print(f"  Previous: {prev_filing['report_date']} (filed {prev_filing['filing_date']})")
        
        # Rate limit
        time.sleep(0.5)
        
        curr_holdings = self.get_13f_holdings(cik, curr_filing['accession_number'])
        time.sleep(0.5)
        prev_holdings = self.get_13f_holdings(cik, prev_filing['accession_number'])
        
        print(f"  Holdings: {len(curr_holdings)} current, {len(prev_holdings)} previous")
        
        if not curr_holdings or not prev_holdings:
            return {
                "fund": fund_name,
                "error": "no_holdings_data",
                "curr_count": len(curr_holdings),
                "prev_count": len(prev_holdings)
            }
        
        # Compare holdings
        changes = self.compare_holdings(prev_holdings, curr_holdings, fund_name)
        significant = self.filter_significant_changes(changes)
        
        # Count by type
        new_positions = [c for c in significant if c.change_type == "NEW"]
        exits = [c for c in significant if c.change_type == "EXIT"]
        increases = [c for c in significant if c.change_type == "INCREASE"]
        decreases = [c for c in significant if c.change_type == "DECREASE"]
        
        print(f"  Changes: {len(new_positions)} NEW, {len(exits)} EXIT, "
              f"{len(increases)} >20% increase, {len(decreases)} >20% decrease")
        
        return {
            "fund": fund_name,
            "cik": cik,
            "current_period": curr_filing['report_date'],
            "previous_period": prev_filing['report_date'],
            "current_filing_date": curr_filing['filing_date'],
            "total_holdings": len(curr_holdings),
            "all_changes": changes,
            "significant_changes": significant,
            "summary": {
                "new_positions": len(new_positions),
                "exits": len(exits),
                "significant_increases": len(increases),
                "significant_decreases": len(decreases)
            }
        }
    
    def track_all_superinvestors(self) -> List[Dict]:
        """Track all configured superinvestors"""
        results = []
        
        for fund_name, cik in SUPERINVESTORS.items():
            try:
                result = self.track_fund(fund_name, cik)
                results.append(result)
                time.sleep(1)  # Rate limiting between funds
            except Exception as e:
                print(f"Error tracking {fund_name}: {e}")
                results.append({"fund": fund_name, "error": str(e)})
        
        return results
    
    def generate_excel_report(self, results: List[Dict], filename: str = None):
        """Generate Excel report of all changes"""
        if not PANDAS_AVAILABLE:
            print("pandas not available - generating CSV instead")
            return self._generate_csv_report(results, filename)
        
        if filename is None:
            filename = f"13f_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        output_path = Path(OUTPUT_DIR) / filename
        
        # Prepare data for DataFrames
        all_significant = []
        summary_data = []
        
        for result in results:
            if "error" in result:
                summary_data.append({
                    "Fund": result.get("fund", "Unknown"),
                    "Status": f"Error: {result.get('error')}",
                    "Period": "",
                    "Holdings": 0,
                    "New": 0,
                    "Exits": 0,
                    "Increases": 0,
                    "Decreases": 0
                })
                continue
            
            summary_data.append({
                "Fund": result["fund"],
                "Status": "OK",
                "Period": result.get("current_period", ""),
                "Holdings": result.get("total_holdings", 0),
                "New": result["summary"]["new_positions"],
                "Exits": result["summary"]["exits"],
                "Increases": result["summary"]["significant_increases"],
                "Decreases": result["summary"]["significant_decreases"]
            })
            
            for change in result.get("significant_changes", []):
                all_significant.append({
                    "Fund": result["fund"],
                    "CUSIP": change.cusip,
                    "Security": change.name,
                    "Change Type": change.change_type,
                    "Prev Shares": change.prev_shares,
                    "Curr Shares": change.curr_shares,
                    "Shares Change %": round(change.shares_change_pct, 2) if change.shares_change_pct != float('inf') else "NEW",
                    "Prev Value ($K)": change.prev_value,
                    "Curr Value ($K)": change.curr_value,
                    "Value Change %": round(change.value_change_pct, 2) if change.value_change_pct != float('inf') else "NEW"
                })
        
        # Create Excel file
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # All significant changes
            if all_significant:
                changes_df = pd.DataFrame(all_significant)
                changes_df.to_excel(writer, sheet_name='Significant Changes', index=False)
                
                # NEW positions sheet
                new_df = changes_df[changes_df['Change Type'] == 'NEW']
                if not new_df.empty:
                    new_df.to_excel(writer, sheet_name='New Positions', index=False)
                
                # EXITS sheet
                exits_df = changes_df[changes_df['Change Type'] == 'EXIT']
                if not exits_df.empty:
                    exits_df.to_excel(writer, sheet_name='Exits', index=False)
        
        print(f"\nExcel report saved: {output_path}")
        return str(output_path)
    
    def _generate_csv_report(self, results: List[Dict], filename: str = None):
        """Fallback CSV report generation without pandas"""
        import csv
        
        if filename is None:
            filename = f"13f_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        output_path = Path(OUTPUT_DIR) / filename
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Fund", "CUSIP", "Security", "Change Type",
                "Prev Shares", "Curr Shares", "Shares Change %",
                "Prev Value ($K)", "Curr Value ($K)", "Value Change %"
            ])
            
            for result in results:
                if "error" in result:
                    continue
                for change in result.get("significant_changes", []):
                    writer.writerow([
                        result["fund"],
                        change.cusip,
                        change.name,
                        change.change_type,
                        change.prev_shares,
                        change.curr_shares,
                        round(change.shares_change_pct, 2) if change.shares_change_pct != float('inf') else "NEW",
                        change.prev_value,
                        change.curr_value,
                        round(change.value_change_pct, 2) if change.value_change_pct != float('inf') else "NEW"
                    ])
        
        print(f"\nCSV report saved: {output_path}")
        return str(output_path)
    
    def generate_alerts(
        self, 
        results: List[Dict], 
        coverage_stocks: List[str] = None,
        use_emoji: bool = True
    ) -> List[str]:
        """Generate alert messages for significant changes"""
        alerts = []
        
        # Use ASCII alternatives if emoji causes issues
        if use_emoji:
            NEW_ICON, EXIT_ICON, UP_ICON, DOWN_ICON = "🆕", "🚪", "📈", "📉"
        else:
            NEW_ICON, EXIT_ICON, UP_ICON, DOWN_ICON = "[NEW]", "[EXIT]", "[UP]", "[DOWN]"
        
        for result in results:
            if "error" in result:
                continue
            
            fund = result["fund"]
            
            for change in result.get("significant_changes", []):
                # Check if in coverage stocks (if specified)
                if coverage_stocks:
                    if change.cusip not in coverage_stocks and change.name not in coverage_stocks:
                        continue
                
                if change.change_type == "NEW":
                    alerts.append(
                        f"{NEW_ICON} {fund} initiated NEW position in {change.name} "
                        f"({change.curr_shares:,} shares, ${change.curr_value:,}K)"
                    )
                elif change.change_type == "EXIT":
                    alerts.append(
                        f"{EXIT_ICON} {fund} EXITED position in {change.name} "
                        f"(was {change.prev_shares:,} shares, ${change.prev_value:,}K)"
                    )
                elif change.change_type == "INCREASE" and change.shares_change_pct >= 50:
                    alerts.append(
                        f"{UP_ICON} {fund} INCREASED {change.name} by {change.shares_change_pct:.1f}% "
                        f"({change.prev_shares:,} -> {change.curr_shares:,} shares)"
                    )
                elif change.change_type == "DECREASE" and change.shares_change_pct <= -50:
                    alerts.append(
                        f"{DOWN_ICON} {fund} DECREASED {change.name} by {abs(change.shares_change_pct):.1f}% "
                        f"({change.prev_shares:,} -> {change.curr_shares:,} shares)"
                    )
        
        return alerts


def main():
    """Main entry point"""
    print("=" * 60)
    print("13F Holdings Change Tracker")
    print("=" * 60)
    
    tracker = SEC13FTracker(cache_enabled=True)
    
    # Track all superinvestors
    results = tracker.track_all_superinvestors()
    
    # Generate Excel report
    report_path = tracker.generate_excel_report(results)
    
    # Generate alerts
    print("\n" + "=" * 60)
    print("ALERTS")
    print("=" * 60)
    
    # Detect Windows console for emoji support
    import sys
    use_emoji = sys.platform != 'win32' or 'UTF-8' in str(sys.stdout.encoding).upper()
    
    alerts = tracker.generate_alerts(results, use_emoji=use_emoji)
    
    if alerts:
        for alert in alerts[:20]:  # Limit to first 20 alerts
            try:
                print(alert)
            except UnicodeEncodeError:
                print(alert.encode('ascii', 'replace').decode('ascii'))
        if len(alerts) > 20:
            print(f"... and {len(alerts) - 20} more alerts")
    else:
        print("No significant alerts generated.")
    
    # Summary stats
    total_new = sum(r.get("summary", {}).get("new_positions", 0) for r in results if "summary" in r)
    total_exits = sum(r.get("summary", {}).get("exits", 0) for r in results if "summary" in r)
    total_increases = sum(r.get("summary", {}).get("significant_increases", 0) for r in results if "summary" in r)
    total_decreases = sum(r.get("summary", {}).get("significant_decreases", 0) for r in results if "summary" in r)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Funds tracked: {len(results)}")
    print(f"Total NEW positions: {total_new}")
    print(f"Total EXITS: {total_exits}")
    print(f"Total >20% INCREASES: {total_increases}")
    print(f"Total >20% DECREASES: {total_decreases}")
    print(f"\nReport saved: {report_path}")
    
    return results


if __name__ == "__main__":
    main()
