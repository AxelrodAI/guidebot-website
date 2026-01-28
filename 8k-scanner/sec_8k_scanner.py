"""
SEC 8-K Filing Scanner
Real-time 8-K filing monitor for material events
"""
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Optional
from pathlib import Path
import hashlib

# 8-K Item Types and their descriptions
ITEM_TYPES = {
    "1.01": {"name": "Entry into Material Agreement", "impact": "HIGH", "category": "business"},
    "1.02": {"name": "Termination of Material Agreement", "impact": "HIGH", "category": "business"},
    "1.03": {"name": "Bankruptcy or Receivership", "impact": "CRITICAL", "category": "financial"},
    "1.04": {"name": "Mine Safety Reporting", "impact": "LOW", "category": "regulatory"},
    "2.01": {"name": "Acquisition/Disposition of Assets", "impact": "HIGH", "category": "business"},
    "2.02": {"name": "Results of Operations (Non-Reliance)", "impact": "HIGH", "category": "financial"},
    "2.03": {"name": "Creation of Direct Financial Obligation", "impact": "MEDIUM", "category": "financial"},
    "2.04": {"name": "Triggering Events (Acceleration)", "impact": "HIGH", "category": "financial"},
    "2.05": {"name": "Costs for Exit/Disposal Activities", "impact": "MEDIUM", "category": "business"},
    "2.06": {"name": "Material Impairments", "impact": "HIGH", "category": "financial"},
    "3.01": {"name": "Delisting/Transfer Notice", "impact": "CRITICAL", "category": "compliance"},
    "3.02": {"name": "Unregistered Equity Sales", "impact": "MEDIUM", "category": "financial"},
    "3.03": {"name": "Material Modification to Shareholder Rights", "impact": "HIGH", "category": "governance"},
    "4.01": {"name": "Auditor Changes", "impact": "HIGH", "category": "compliance"},
    "4.02": {"name": "Non-Reliance on Financial Statements", "impact": "CRITICAL", "category": "compliance"},
    "5.01": {"name": "Changes in Control", "impact": "CRITICAL", "category": "governance"},
    "5.02": {"name": "Executive Departure/Appointment", "impact": "HIGH", "category": "governance"},
    "5.03": {"name": "Amendments to Articles/Bylaws", "impact": "MEDIUM", "category": "governance"},
    "5.04": {"name": "Trading Suspension", "impact": "CRITICAL", "category": "compliance"},
    "5.05": {"name": "Amendment to Code of Ethics", "impact": "LOW", "category": "governance"},
    "5.06": {"name": "Change in Shell Company Status", "impact": "MEDIUM", "category": "compliance"},
    "5.07": {"name": "Shareholder Vote Results", "impact": "MEDIUM", "category": "governance"},
    "5.08": {"name": "Shareholder Director Nominations", "impact": "LOW", "category": "governance"},
    "6.01": {"name": "ABS Servicer Information", "impact": "LOW", "category": "financial"},
    "6.02": {"name": "ABS Sales Information", "impact": "LOW", "category": "financial"},
    "6.03": {"name": "ABS Credit Enhancement", "impact": "LOW", "category": "financial"},
    "6.04": {"name": "ABS Failure to Make Distribution", "impact": "MEDIUM", "category": "financial"},
    "6.05": {"name": "ABS Securities Act Updating", "impact": "LOW", "category": "compliance"},
    "7.01": {"name": "Regulation FD Disclosure", "impact": "MEDIUM", "category": "disclosure"},
    "8.01": {"name": "Other Events", "impact": "VARIES", "category": "other"},
    "9.01": {"name": "Financial Statements and Exhibits", "impact": "LOW", "category": "exhibits"},
}

# Critical items that warrant immediate alerts
CRITICAL_ITEMS = ["1.03", "3.01", "4.02", "5.01", "5.04"]
HIGH_IMPACT_ITEMS = ["1.01", "1.02", "2.01", "2.02", "2.04", "2.06", "3.03", "4.01", "5.02"]


@dataclass
class Filing8K:
    """Represents a single 8-K filing"""
    ticker: str
    company_name: str
    cik: str
    filing_date: str
    filing_time: str  # Time of day filed
    accession_number: str
    items: list  # List of item numbers
    item_descriptions: list  # Descriptions of items
    impact_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # Primary category
    url: str
    is_after_hours: bool
    is_friday_night: bool  # "Friday night dump"
    summary: str = ""
    
    def to_dict(self):
        return asdict(self)


@dataclass 
class FilingAlert:
    """Alert for a notable 8-K filing"""
    filing: Filing8K
    alert_type: str  # CRITICAL, HIGH_IMPACT, AFTER_HOURS, FRIDAY_DUMP, EXECUTIVE_CHANGE, etc.
    priority: int  # 1-5 (1 = highest)
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self):
        return {
            "filing": self.filing.to_dict(),
            "alert_type": self.alert_type,
            "priority": self.priority,
            "message": self.message,
            "timestamp": self.timestamp
        }


class SEC8KScanner:
    """Scanner for SEC 8-K filings"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.filings_file = self.cache_dir / "8k_filings.json"
        self.alerts_file = self.cache_dir / "8k_alerts.json"
        self.watchlist_file = self.cache_dir / "8k_watchlist.json"
        
        # Load existing data
        self.filings = self._load_json(self.filings_file, [])
        self.alerts = self._load_json(self.alerts_file, [])
        self.watchlist = self._load_json(self.watchlist_file, [])
        
    def _load_json(self, path: Path, default):
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return default
    
    def _save_json(self, path: Path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_sample_filings(self):
        """Generate realistic sample 8-K filings for testing"""
        import random
        
        companies = [
            ("AAPL", "Apple Inc.", "0000320193"),
            ("MSFT", "Microsoft Corporation", "0000789019"),
            ("GOOGL", "Alphabet Inc.", "0001652044"),
            ("AMZN", "Amazon.com Inc.", "0001018724"),
            ("NVDA", "NVIDIA Corporation", "0001045810"),
            ("META", "Meta Platforms Inc.", "0001326801"),
            ("TSLA", "Tesla Inc.", "0001318605"),
            ("JPM", "JPMorgan Chase & Co.", "0000019617"),
            ("V", "Visa Inc.", "0001403161"),
            ("JNJ", "Johnson & Johnson", "0000200406"),
            ("WMT", "Walmart Inc.", "0000104169"),
            ("PG", "Procter & Gamble Co.", "0000080424"),
            ("XOM", "Exxon Mobil Corporation", "0000034088"),
            ("BAC", "Bank of America Corp.", "0000070858"),
            ("DIS", "Walt Disney Company", "0001744489"),
        ]
        
        filings = []
        now = datetime.now()
        
        # Generate filings over the past 30 days
        for i in range(50):
            company = random.choice(companies)
            ticker, name, cik = company
            
            # Random date in past 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            filing_dt = now - timedelta(days=days_ago, hours=hours_ago)
            
            # Determine filing time characteristics
            filing_hour = filing_dt.hour
            filing_weekday = filing_dt.weekday()
            is_after_hours = filing_hour < 9 or filing_hour >= 16
            is_friday_night = filing_weekday == 4 and filing_hour >= 17
            
            # Select 1-3 items for this filing
            num_items = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
            
            # Bias towards common items
            common_items = ["5.02", "8.01", "9.01", "7.01", "2.02", "1.01", "5.07"]
            rare_items = ["1.03", "4.02", "5.01", "3.01", "5.04", "2.06", "4.01"]
            
            items = []
            for _ in range(num_items):
                if random.random() < 0.1:  # 10% chance of rare item
                    items.append(random.choice(rare_items))
                else:
                    items.append(random.choice(common_items))
            items = list(set(items))  # Remove duplicates
            
            # Determine impact level based on items
            impact = "LOW"
            for item in items:
                if item in CRITICAL_ITEMS:
                    impact = "CRITICAL"
                    break
                elif item in HIGH_IMPACT_ITEMS and impact != "CRITICAL":
                    impact = "HIGH"
                elif ITEM_TYPES.get(item, {}).get("impact") == "MEDIUM" and impact == "LOW":
                    impact = "MEDIUM"
            
            # Get primary category
            categories = [ITEM_TYPES.get(item, {}).get("category", "other") for item in items]
            primary_category = max(set(categories), key=categories.count) if categories else "other"
            
            # Generate accession number
            acc_num = f"{cik.lstrip('0')}-{filing_dt.strftime('%y')}-{random.randint(100000, 999999):06d}"
            
            # Create item descriptions
            item_descs = [ITEM_TYPES.get(item, {}).get("name", "Unknown") for item in items]
            
            # Generate summary based on items
            summary = self._generate_summary(ticker, items, is_after_hours)
            
            filing = Filing8K(
                ticker=ticker,
                company_name=name,
                cik=cik,
                filing_date=filing_dt.strftime("%Y-%m-%d"),
                filing_time=filing_dt.strftime("%H:%M:%S"),
                accession_number=acc_num,
                items=items,
                item_descriptions=item_descs,
                impact_level=impact,
                category=primary_category,
                url=f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_num.replace('-', '')}/",
                is_after_hours=is_after_hours,
                is_friday_night=is_friday_night,
                summary=summary
            )
            filings.append(filing.to_dict())
        
        # Sort by date (newest first)
        filings.sort(key=lambda x: (x["filing_date"], x["filing_time"]), reverse=True)
        return filings
    
    def _generate_summary(self, ticker: str, items: list, after_hours: bool) -> str:
        """Generate human-readable summary for filing"""
        summaries = []
        
        for item in items:
            if item == "5.02":
                summaries.append(f"{ticker} announced executive leadership change")
            elif item == "1.01":
                summaries.append(f"{ticker} entered into material definitive agreement")
            elif item == "2.01":
                summaries.append(f"{ticker} completed acquisition or disposition of assets")
            elif item == "2.02":
                summaries.append(f"{ticker} disclosed preliminary results")
            elif item == "7.01":
                summaries.append(f"{ticker} made Regulation FD disclosure")
            elif item == "8.01":
                summaries.append(f"{ticker} disclosed other material event")
            elif item == "4.01":
                summaries.append(f"{ticker} changed auditors - ATTENTION")
            elif item == "4.02":
                summaries.append(f"{ticker} announced non-reliance on prior financials - RED FLAG")
            elif item == "1.03":
                summaries.append(f"{ticker} filed for bankruptcy protection - CRITICAL")
            elif item == "5.01":
                summaries.append(f"{ticker} announced change in control - MAJOR EVENT")
            elif item == "2.06":
                summaries.append(f"{ticker} disclosed material impairment")
            elif item == "3.01":
                summaries.append(f"{ticker} received delisting notice - CRITICAL")
        
        summary = ". ".join(summaries[:2]) if summaries else f"{ticker} filed 8-K disclosure"
        if after_hours:
            summary += " [AFTER HOURS]"
        return summary
    
    def refresh_filings(self) -> dict:
        """Refresh filings data (simulated)"""
        # In production, this would call SEC EDGAR API
        self.filings = self._generate_sample_filings()
        self._save_json(self.filings_file, self.filings)
        
        # Generate alerts
        self._generate_alerts()
        
        return {
            "status": "success",
            "filings_count": len(self.filings),
            "alerts_count": len(self.alerts),
            "last_updated": datetime.now().isoformat()
        }
    
    def _generate_alerts(self):
        """Generate alerts for notable filings"""
        self.alerts = []
        
        for f in self.filings:
            filing = Filing8K(**f) if isinstance(f, dict) else f
            filing_dict = f if isinstance(f, dict) else f.to_dict()
            
            # Check for critical filings
            if filing_dict["impact_level"] == "CRITICAL":
                alert = FilingAlert(
                    filing=Filing8K(**filing_dict),
                    alert_type="CRITICAL",
                    priority=1,
                    message=f"CRITICAL: {filing_dict['summary']}"
                )
                self.alerts.append(alert.to_dict())
            
            # Check for high impact filings  
            elif filing_dict["impact_level"] == "HIGH":
                alert = FilingAlert(
                    filing=Filing8K(**filing_dict),
                    alert_type="HIGH_IMPACT",
                    priority=2,
                    message=f"High Impact: {filing_dict['summary']}"
                )
                self.alerts.append(alert.to_dict())
            
            # Check for Friday night dumps
            if filing_dict["is_friday_night"]:
                alert = FilingAlert(
                    filing=Filing8K(**filing_dict),
                    alert_type="FRIDAY_DUMP",
                    priority=3,
                    message=f"Friday Night Filing: {filing_dict['ticker']} - often used to bury bad news"
                )
                self.alerts.append(alert.to_dict())
            
            # Check for after-hours high impact
            if filing_dict["is_after_hours"] and filing_dict["impact_level"] in ["HIGH", "CRITICAL"]:
                alert = FilingAlert(
                    filing=Filing8K(**filing_dict),
                    alert_type="AFTER_HOURS",
                    priority=2,
                    message=f"After Hours Material Filing: {filing_dict['summary']}"
                )
                self.alerts.append(alert.to_dict())
            
            # Executive changes get special attention
            if "5.02" in filing_dict["items"]:
                alert = FilingAlert(
                    filing=Filing8K(**filing_dict),
                    alert_type="EXECUTIVE_CHANGE",
                    priority=3,
                    message=f"Executive Change: {filing_dict['company_name']} leadership update"
                )
                self.alerts.append(alert.to_dict())
            
            # Auditor changes are red flags
            if "4.01" in filing_dict["items"]:
                alert = FilingAlert(
                    filing=Filing8K(**filing_dict),
                    alert_type="AUDITOR_CHANGE",
                    priority=2,
                    message=f"Auditor Change Alert: {filing_dict['ticker']} - investigate reason"
                )
                self.alerts.append(alert.to_dict())
        
        # Sort by priority
        self.alerts.sort(key=lambda x: x["priority"])
        self._save_json(self.alerts_file, self.alerts)
    
    def get_filings(self, 
                    ticker: Optional[str] = None,
                    impact: Optional[str] = None,
                    category: Optional[str] = None,
                    item: Optional[str] = None,
                    days: int = 30,
                    limit: int = 50) -> list:
        """Get filtered filings"""
        if not self.filings:
            self.refresh_filings()
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        results = []
        for f in self.filings:
            # Date filter
            if f["filing_date"] < cutoff:
                continue
            
            # Ticker filter
            if ticker and f["ticker"].upper() != ticker.upper():
                continue
            
            # Impact filter
            if impact and f["impact_level"] != impact.upper():
                continue
            
            # Category filter
            if category and f["category"] != category.lower():
                continue
            
            # Item filter
            if item and item not in f["items"]:
                continue
            
            results.append(f)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_alerts(self, priority: Optional[int] = None, limit: int = 20) -> list:
        """Get alerts, optionally filtered by priority"""
        if not self.alerts:
            self._generate_alerts()
        
        if priority:
            return [a for a in self.alerts if a["priority"] <= priority][:limit]
        return self.alerts[:limit]
    
    def get_ticker_history(self, ticker: str, limit: int = 20) -> dict:
        """Get filing history for a specific ticker"""
        ticker = ticker.upper()
        filings = [f for f in self.filings if f["ticker"] == ticker][:limit]
        
        # Calculate statistics
        if filings:
            item_counts = {}
            categories = {}
            for f in filings:
                for item in f["items"]:
                    item_counts[item] = item_counts.get(item, 0) + 1
                categories[f["category"]] = categories.get(f["category"], 0) + 1
            
            stats = {
                "total_filings": len(filings),
                "item_breakdown": item_counts,
                "category_breakdown": categories,
                "after_hours_count": sum(1 for f in filings if f["is_after_hours"]),
                "friday_night_count": sum(1 for f in filings if f["is_friday_night"]),
                "critical_count": sum(1 for f in filings if f["impact_level"] == "CRITICAL"),
                "high_impact_count": sum(1 for f in filings if f["impact_level"] == "HIGH")
            }
        else:
            stats = {"total_filings": 0}
        
        return {
            "ticker": ticker,
            "filings": filings,
            "statistics": stats
        }
    
    def scan_watchlist(self, days: int = 7) -> dict:
        """Scan watchlist for recent filings"""
        if not self.watchlist:
            return {"error": "No watchlist configured. Use 'watchlist add TICKER' to add tickers."}
        
        results = {}
        for ticker in self.watchlist:
            filings = self.get_filings(ticker=ticker, days=days)
            if filings:
                results[ticker] = {
                    "count": len(filings),
                    "filings": filings,
                    "has_critical": any(f["impact_level"] == "CRITICAL" for f in filings),
                    "has_high_impact": any(f["impact_level"] == "HIGH" for f in filings)
                }
        
        return {
            "watchlist": self.watchlist,
            "period_days": days,
            "tickers_with_filings": len(results),
            "results": results
        }
    
    def add_to_watchlist(self, ticker: str) -> dict:
        """Add ticker to watchlist"""
        ticker = ticker.upper()
        if ticker not in self.watchlist:
            self.watchlist.append(ticker)
            self._save_json(self.watchlist_file, self.watchlist)
            return {"status": "added", "ticker": ticker, "watchlist": self.watchlist}
        return {"status": "exists", "ticker": ticker, "watchlist": self.watchlist}
    
    def remove_from_watchlist(self, ticker: str) -> dict:
        """Remove ticker from watchlist"""
        ticker = ticker.upper()
        if ticker in self.watchlist:
            self.watchlist.remove(ticker)
            self._save_json(self.watchlist_file, self.watchlist)
            return {"status": "removed", "ticker": ticker, "watchlist": self.watchlist}
        return {"status": "not_found", "ticker": ticker, "watchlist": self.watchlist}
    
    def get_summary(self) -> dict:
        """Get summary statistics"""
        if not self.filings:
            self.refresh_filings()
        
        # Last 7 days stats
        week_cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week_filings = [f for f in self.filings if f["filing_date"] >= week_cutoff]
        
        impact_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        category_counts = {}
        item_counts = {}
        ticker_counts = {}
        
        for f in week_filings:
            impact_counts[f["impact_level"]] = impact_counts.get(f["impact_level"], 0) + 1
            category_counts[f["category"]] = category_counts.get(f["category"], 0) + 1
            ticker_counts[f["ticker"]] = ticker_counts.get(f["ticker"], 0) + 1
            for item in f["items"]:
                item_counts[item] = item_counts.get(item, 0) + 1
        
        # Most active tickers
        top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Most common items
        top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_items_with_names = [
            {"item": item, "count": count, "name": ITEM_TYPES.get(item, {}).get("name", "Unknown")}
            for item, count in top_items
        ]
        
        return {
            "period": "last_7_days",
            "total_filings": len(week_filings),
            "impact_breakdown": impact_counts,
            "category_breakdown": category_counts,
            "most_active_tickers": top_tickers,
            "most_common_items": top_items_with_names,
            "after_hours_filings": sum(1 for f in week_filings if f["is_after_hours"]),
            "friday_night_filings": sum(1 for f in week_filings if f["is_friday_night"]),
            "active_alerts": len(self.alerts),
            "last_updated": datetime.now().isoformat()
        }
    
    def get_item_info(self, item: str) -> dict:
        """Get information about a specific 8-K item type"""
        if item in ITEM_TYPES:
            info = ITEM_TYPES[item]
            # Get recent filings with this item
            recent = [f for f in self.filings if item in f["items"]][:5]
            return {
                "item": item,
                "name": info["name"],
                "impact": info["impact"],
                "category": info["category"],
                "recent_filings": recent,
                "is_critical": item in CRITICAL_ITEMS,
                "is_high_impact": item in HIGH_IMPACT_ITEMS
            }
        return {"error": f"Unknown item type: {item}"}
    
    def list_item_types(self) -> dict:
        """List all 8-K item types"""
        items_by_category = {}
        for item_num, info in ITEM_TYPES.items():
            cat = info["category"]
            if cat not in items_by_category:
                items_by_category[cat] = []
            items_by_category[cat].append({
                "item": item_num,
                "name": info["name"],
                "impact": info["impact"]
            })
        
        return {
            "total_item_types": len(ITEM_TYPES),
            "by_category": items_by_category,
            "critical_items": CRITICAL_ITEMS,
            "high_impact_items": HIGH_IMPACT_ITEMS
        }
