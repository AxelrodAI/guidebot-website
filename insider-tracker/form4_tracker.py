"""
SEC Form 4 Insider Trading Monitor

Monitors SEC EDGAR for Form 4 filings (insider transactions).
Parses buyer vs seller, flags cluster buying, alerts on C-suite purchases.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json
import os
import time
import re

from config import (
    SEC_EDGAR_BASE_URL, SEC_EDGAR_FILINGS_URL,
    SEC_HEADERS, CSUITE_TITLES, CSUITE_PURCHASE_ALERT_THRESHOLD,
    CLUSTER_BUYING_WINDOW_DAYS, CLUSTER_BUYING_MIN_INSIDERS,
    SENTIMENT_WEIGHTS, CACHE_DIR, CACHE_EXPIRY_HOURS, OUTPUT_DIR
)


@dataclass
class InsiderTransaction:
    """Represents a single insider transaction from Form 4"""
    filing_date: str
    company_name: str
    ticker: str
    cik: str
    insider_name: str
    insider_title: str
    transaction_type: str  # 'P' = Purchase, 'S' = Sale, 'A' = Award, etc.
    transaction_code: str
    shares: float
    price: float
    value: float
    shares_owned_after: float
    is_direct: bool  # Direct vs indirect ownership
    form_url: str
    
    @property
    def is_purchase(self) -> bool:
        return self.transaction_type in ('P', 'A', 'M', 'C', 'G')
    
    @property
    def is_sale(self) -> bool:
        return self.transaction_type in ('S', 'D', 'F')
    
    @property
    def is_csuite(self) -> bool:
        title_upper = self.insider_title.upper()
        return any(t.upper() in title_upper for t in CSUITE_TITLES)
    
    @property
    def is_large_purchase(self) -> bool:
        return self.is_purchase and self.value >= CSUITE_PURCHASE_ALERT_THRESHOLD


@dataclass  
class CompanyInsiderSentiment:
    """Aggregated insider sentiment for a company"""
    ticker: str
    company_name: str
    transactions: List[InsiderTransaction] = field(default_factory=list)
    
    @property
    def total_purchases(self) -> int:
        return sum(1 for t in self.transactions if t.is_purchase)
    
    @property
    def total_sales(self) -> int:
        return sum(1 for t in self.transactions if t.is_sale)
    
    @property
    def purchase_value(self) -> float:
        return sum(t.value for t in self.transactions if t.is_purchase)
    
    @property
    def sale_value(self) -> float:
        return sum(t.value for t in self.transactions if t.is_sale)
    
    @property
    def net_value(self) -> float:
        return self.purchase_value - self.sale_value
    
    @property
    def sentiment_score(self) -> float:
        """Calculate insider sentiment score (-100 to +100)"""
        if not self.transactions:
            return 0.0
            
        score = 0.0
        for t in self.transactions:
            if t.is_purchase:
                base = SENTIMENT_WEIGHTS["purchase"]
                if t.is_csuite:
                    base = SENTIMENT_WEIGHTS["csuite_purchase"]
                if t.is_large_purchase:
                    base *= SENTIMENT_WEIGHTS["large_purchase"]
                score += base * (t.value / 100000)  # Scale by $100k units
            elif t.is_sale:
                base = SENTIMENT_WEIGHTS["sale"]
                if t.is_csuite:
                    base = SENTIMENT_WEIGHTS["csuite_sale"]
                score += base * (t.value / 100000)
        
        # Check for cluster buying
        if self.has_cluster_buying():
            score *= SENTIMENT_WEIGHTS["cluster_buying"]
        
        # Normalize to -100 to +100 range
        return max(-100, min(100, score * 10))
    
    def has_cluster_buying(self) -> bool:
        """Check if multiple insiders bought in the same week"""
        if len(self.transactions) < CLUSTER_BUYING_MIN_INSIDERS:
            return False
            
        purchases = [t for t in self.transactions if t.is_purchase]
        if len(purchases) < CLUSTER_BUYING_MIN_INSIDERS:
            return False
            
        # Group by week
        insiders_by_week = defaultdict(set)
        for t in purchases:
            try:
                date = datetime.strptime(t.filing_date, "%Y-%m-%d")
                week_key = date.strftime("%Y-W%W")
                insiders_by_week[week_key].add(t.insider_name)
            except:
                continue
                
        return any(len(insiders) >= CLUSTER_BUYING_MIN_INSIDERS 
                   for insiders in insiders_by_week.values())


class Form4Tracker:
    """Main tracker for SEC Form 4 filings"""
    
    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(SEC_HEADERS)
        
    def get_recent_filings(self, count: int = 100) -> List[Dict]:
        """Fetch recent Form 4 filings from SEC EDGAR API"""
        cache_file = os.path.join(CACHE_DIR, "recent_filings.json")
        
        # Check cache
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            age_hours = (time.time() - mtime) / 3600
            if age_hours < CACHE_EXPIRY_HOURS:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        filings = []
        try:
            # Use SEC EDGAR submissions API - get from a list of major companies
            # This is more reliable than the RSS feed
            sample_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 
                            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'V', 'MA', 'UNH', 'JNJ',
                            'PG', 'HD', 'DIS', 'NFLX']
            
            for ticker in sample_tickers[:min(count//5, 20)]:
                try:
                    cik = self._get_cik_from_ticker(ticker)
                    if not cik:
                        continue
                    
                    url = f"{SEC_EDGAR_FILINGS_URL}/CIK{cik.zfill(10)}.json"
                    response = self.session.get(url, timeout=15)
                    if response.status_code != 200:
                        continue
                    
                    data = response.json()
                    recent = data.get('filings', {}).get('recent', {})
                    forms = recent.get('form', [])
                    dates = recent.get('filingDate', [])
                    company_name = data.get('name', ticker)
                    
                    for i, form in enumerate(forms[:10]):
                        if form in ('4', '4/A'):
                            filings.append({
                                'title': f"4 - {company_name} ({ticker})",
                                'ticker': ticker,
                                'date': dates[i] if i < len(dates) else '',
                                'company': company_name,
                                'cik': cik
                            })
                    
                    time.sleep(0.1)  # Be nice to SEC servers
                    
                except Exception:
                    continue
            
            # Sort by date descending
            filings.sort(key=lambda x: x.get('date', ''), reverse=True)
            filings = filings[:count]
            
            # Save to cache
            with open(cache_file, 'w') as f:
                json.dump(filings, f, indent=2)
                
        except Exception as e:
            print(f"Error fetching filings: {e}")
            
        return filings
    
    def get_company_filings(self, ticker: str, days: int = 90) -> List[Dict]:
        """Get Form 4 filings for a specific company"""
        # First, look up CIK from ticker
        cik = self._get_cik_from_ticker(ticker)
        if not cik:
            print(f"Could not find CIK for ticker: {ticker}")
            return []
        
        cache_file = os.path.join(CACHE_DIR, f"filings_{ticker}.json")
        
        # Check cache
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            age_hours = (time.time() - mtime) / 3600
            if age_hours < CACHE_EXPIRY_HOURS:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        filings = []
        try:
            # Get company submissions
            url = f"{SEC_EDGAR_FILINGS_URL}/CIK{cik.zfill(10)}.json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            recent = data.get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            accessions = recent.get('accessionNumber', [])
            primary_docs = recent.get('primaryDocument', [])
            
            # Use extended lookback to handle SEC data lag (data may be up to 60 days behind)
            effective_days = days + 60
            cutoff_date = (datetime.now() - timedelta(days=effective_days)).strftime("%Y-%m-%d")
            
            for i, form in enumerate(forms):
                if form in ('4', '4/A'):
                    filing_date = dates[i] if i < len(dates) else ''
                    if filing_date >= cutoff_date:
                        accession = accessions[i].replace('-', '') if i < len(accessions) else ''
                        primary_doc = primary_docs[i] if i < len(primary_docs) else ''
                        
                        filings.append({
                            'form': form,
                            'date': filing_date,
                            'accession': accession,
                            'cik': cik,
                            'ticker': ticker.upper(),
                            'company': data.get('name', ''),
                            'url': f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}"
                        })
            
            # Save to cache
            with open(cache_file, 'w') as f:
                json.dump(filings, f, indent=2)
                
        except Exception as e:
            print(f"Error fetching company filings: {e}")
            
        return filings
    
    def parse_form4(self, filing_url: str) -> List[InsiderTransaction]:
        """Parse a Form 4 XML filing and extract transactions"""
        transactions = []
        
        try:
            # The SEC URLs may have xslF345X05/ prefix for HTML transforms
            # We need the raw XML which is at the base path
            xml_url = filing_url
            
            # Remove xslF345X05/ transform prefix if present
            if '/xslF345X05/' in xml_url:
                xml_url = xml_url.replace('/xslF345X05/', '/')
            
            # Ensure it ends with .xml
            if not xml_url.endswith('.xml'):
                xml_url = xml_url.replace('.htm', '.xml').replace('.html', '.xml')
            
            response = self.session.get(xml_url, timeout=30)
            
            if response.status_code != 200 or not response.text.strip().startswith('<?xml'):
                # Try alternate XML filename patterns
                base_url = filing_url.rsplit('/', 1)[0]
                if '/xslF345X05' in base_url:
                    base_url = base_url.rsplit('/xslF345X05', 1)[0]
                    
                for pattern in ['form4.xml', 'primary_doc.xml']:
                    try:
                        alt_response = self.session.get(f"{base_url}/{pattern}", timeout=10)
                        if alt_response.status_code == 200 and alt_response.text.strip().startswith('<?xml'):
                            response = alt_response
                            break
                    except:
                        continue
            
            if response.status_code != 200 or not response.text.strip().startswith('<?xml'):
                return transactions
            
            root = ET.fromstring(response.content)
            
            # Extract issuer info
            issuer = root.find('.//issuer')
            company_name = ""
            ticker = ""
            cik = ""
            if issuer is not None:
                name_elem = issuer.find('issuerName')
                ticker_elem = issuer.find('issuerTradingSymbol')
                cik_elem = issuer.find('issuerCik')
                company_name = name_elem.text if name_elem is not None else ""
                ticker = ticker_elem.text if ticker_elem is not None else ""
                cik = cik_elem.text if cik_elem is not None else ""
            
            # Extract reporter (insider) info
            reporter = root.find('.//reportingOwner')
            insider_name = ""
            insider_title = ""
            if reporter is not None:
                owner_id = reporter.find('.//reportingOwnerId')
                if owner_id is not None:
                    name_elem = owner_id.find('rptOwnerName')
                    insider_name = name_elem.text if name_elem is not None else ""
                
                relationship = reporter.find('.//reportingOwnerRelationship')
                if relationship is not None:
                    title_elem = relationship.find('officerTitle')
                    if title_elem is not None and title_elem.text:
                        insider_title = title_elem.text
                    else:
                        # Check for director/officer flags
                        is_director = relationship.find('isDirector')
                        is_officer = relationship.find('isOfficer')
                        if is_director is not None and is_director.text == '1':
                            insider_title = "Director"
                        elif is_officer is not None and is_officer.text == '1':
                            insider_title = "Officer"
            
            # Extract non-derivative transactions
            for trans in root.findall('.//nonDerivativeTransaction'):
                tx = self._parse_transaction(trans, filing_url, company_name, 
                                            ticker, cik, insider_name, insider_title)
                if tx:
                    transactions.append(tx)
            
            # Also check derivative transactions
            for trans in root.findall('.//derivativeTransaction'):
                tx = self._parse_transaction(trans, filing_url, company_name,
                                            ticker, cik, insider_name, insider_title,
                                            is_derivative=True)
                if tx:
                    transactions.append(tx)
                    
        except Exception as e:
            print(f"Error parsing Form 4: {e}")
            
        return transactions
    
    def _parse_transaction(self, trans_elem, filing_url: str, company_name: str,
                          ticker: str, cik: str, insider_name: str, 
                          insider_title: str, is_derivative: bool = False) -> Optional[InsiderTransaction]:
        """Parse a single transaction element"""
        try:
            # Transaction coding
            coding = trans_elem.find('.//transactionCoding')
            if coding is None:
                return None
                
            tx_code = coding.find('transactionCode')
            tx_type = tx_code.text if tx_code is not None else ''
            
            # Transaction amounts
            amounts = trans_elem.find('.//transactionAmounts')
            if amounts is None:
                return None
            
            shares_elem = amounts.find('transactionShares/value')
            price_elem = amounts.find('transactionPricePerShare/value')
            
            shares = float(shares_elem.text) if shares_elem is not None and shares_elem.text else 0
            price = float(price_elem.text) if price_elem is not None and price_elem.text else 0
            value = shares * price
            
            # Post-transaction amounts
            post = trans_elem.find('.//postTransactionAmounts')
            shares_owned = 0
            if post is not None:
                owned_elem = post.find('sharesOwnedFollowingTransaction/value')
                shares_owned = float(owned_elem.text) if owned_elem is not None and owned_elem.text else 0
            
            # Ownership nature (direct vs indirect)
            ownership = trans_elem.find('.//ownershipNature/directOrIndirectOwnership/value')
            is_direct = ownership is not None and ownership.text == 'D'
            
            # Transaction date
            date_elem = trans_elem.find('.//transactionDate/value')
            filing_date = date_elem.text if date_elem is not None else ''
            
            return InsiderTransaction(
                filing_date=filing_date,
                company_name=company_name,
                ticker=ticker.upper() if ticker else '',
                cik=cik,
                insider_name=insider_name,
                insider_title=insider_title,
                transaction_type=tx_type,
                transaction_code=tx_type,
                shares=shares,
                price=price,
                value=value,
                shares_owned_after=shares_owned,
                is_direct=is_direct,
                form_url=filing_url
            )
            
        except Exception as e:
            print(f"Error parsing transaction: {e}")
            return None
    
    def _get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Look up CIK from ticker symbol"""
        cache_file = os.path.join(CACHE_DIR, "ticker_cik_map.json")
        
        # Load or create ticker->CIK mapping
        ticker_map = {}
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                ticker_map = json.load(f)
        
        ticker = ticker.upper()
        if ticker in ticker_map:
            return ticker_map[ticker]
        
        # Common tickers with known CIKs (fallback)
        known_ciks = {
            'AAPL': '320193', 'MSFT': '789019', 'GOOGL': '1652044', 'GOOG': '1652044',
            'AMZN': '1018724', 'NVDA': '1045810', 'META': '1326801', 'TSLA': '1318605',
            'JPM': '19617', 'BAC': '70858', 'WFC': '72971', 'GS': '886982',
            'MS': '895421', 'V': '1403161', 'MA': '1141391', 'UNH': '731766',
            'JNJ': '200406', 'PG': '80424', 'HD': '354950', 'DIS': '1744489',
            'NFLX': '1065280', 'INTC': '50863', 'AMD': '2488', 'CRM': '1108524',
            'ORCL': '1341439', 'CSCO': '858877', 'IBM': '51143', 'QCOM': '804328',
            'TXN': '97476', 'AVGO': '1441634', 'ADBE': '796343', 'NOW': '1373715',
            'EWBC': '913005', 'WMT': '104169', 'KO': '21344', 'PEP': '77476',
            'COST': '909832', 'MCD': '63908', 'NKE': '320187', 'SBUX': '829224'
        }
        
        if ticker in known_ciks:
            ticker_map[ticker] = known_ciks[ticker]
            with open(cache_file, 'w') as f:
                json.dump(ticker_map, f)
            return known_ciks[ticker]
        
        try:
            # Try SEC company tickers JSON from multiple URLs
            urls = [
                "https://www.sec.gov/files/company_tickers.json",
                "https://data.sec.gov/submissions/company_tickers.json"
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        for entry in data.values():
                            t = entry.get('ticker', '').upper()
                            c = str(entry.get('cik_str', ''))
                            ticker_map[t] = c
                        
                        # Save cache
                        with open(cache_file, 'w') as f:
                            json.dump(ticker_map, f)
                        
                        return ticker_map.get(ticker)
                except:
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error looking up CIK: {e}")
            return None
    
    def get_sentiment(self, ticker: str, days: int = 90) -> CompanyInsiderSentiment:
        """Get insider sentiment for a company"""
        sentiment = CompanyInsiderSentiment(ticker=ticker.upper(), company_name="")
        
        filings = self.get_company_filings(ticker, days)
        
        for filing in filings:
            if not sentiment.company_name and filing.get('company'):
                sentiment.company_name = filing['company']
            
            transactions = self.parse_form4(filing['url'])
            sentiment.transactions.extend(transactions)
        
        return sentiment
    
    def scan_recent(self, count: int = 50) -> Dict[str, CompanyInsiderSentiment]:
        """Scan recent Form 4 filings and aggregate by company"""
        sentiments: Dict[str, CompanyInsiderSentiment] = {}
        
        filings = self.get_recent_filings(count)
        
        for filing in filings:
            ticker = filing.get('ticker')
            if not ticker:
                continue
            
            if ticker not in sentiments:
                sentiments[ticker] = CompanyInsiderSentiment(
                    ticker=ticker,
                    company_name=filing.get('title', '').split(' - ', 1)[-1].split(' (')[0]
                )
            
            # Note: For full parsing, we'd need to fetch each filing's XML
            # This is a lightweight scan that just shows recent activity
        
        return sentiments
    
    def get_alerts(self, ticker: str = None, days: int = 30) -> List[Dict]:
        """Generate alerts for significant insider activity"""
        alerts = []
        
        if ticker:
            sentiment = self.get_sentiment(ticker, days)
            sentiments = {ticker: sentiment}
        else:
            # Scan recent filings
            sentiments = self.scan_recent(100)
        
        for tick, sent in sentiments.items():
            # C-Suite large purchases
            for t in sent.transactions:
                if t.is_csuite and t.is_large_purchase:
                    alerts.append({
                        'type': 'CSUITE_LARGE_PURCHASE',
                        'ticker': tick,
                        'company': sent.company_name,
                        'insider': t.insider_name,
                        'title': t.insider_title,
                        'value': t.value,
                        'shares': t.shares,
                        'date': t.filing_date,
                        'url': t.form_url,
                        'priority': 'HIGH'
                    })
            
            # Cluster buying
            if sent.has_cluster_buying():
                buyers = list(set(t.insider_name for t in sent.transactions if t.is_purchase))
                alerts.append({
                    'type': 'CLUSTER_BUYING',
                    'ticker': tick,
                    'company': sent.company_name,
                    'insiders': buyers,
                    'total_value': sent.purchase_value,
                    'priority': 'HIGH'
                })
            
            # Strong sentiment signals
            if sent.sentiment_score >= 50:
                alerts.append({
                    'type': 'BULLISH_SENTIMENT',
                    'ticker': tick,
                    'company': sent.company_name,
                    'sentiment_score': sent.sentiment_score,
                    'purchases': sent.total_purchases,
                    'sales': sent.total_sales,
                    'net_value': sent.net_value,
                    'priority': 'MEDIUM'
                })
            elif sent.sentiment_score <= -50:
                alerts.append({
                    'type': 'BEARISH_SENTIMENT',
                    'ticker': tick,
                    'company': sent.company_name,
                    'sentiment_score': sent.sentiment_score,
                    'purchases': sent.total_purchases,
                    'sales': sent.total_sales,
                    'net_value': sent.net_value,
                    'priority': 'MEDIUM'
                })
        
        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        alerts.sort(key=lambda x: priority_order.get(x.get('priority', 'LOW'), 2))
        
        return alerts
    
    def export_to_json(self, ticker: str, days: int = 90) -> str:
        """Export sentiment data to JSON file"""
        sentiment = self.get_sentiment(ticker, days)
        
        output = {
            'ticker': sentiment.ticker,
            'company': sentiment.company_name,
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'summary': {
                'sentiment_score': round(sentiment.sentiment_score, 2),
                'total_transactions': len(sentiment.transactions),
                'purchases': sentiment.total_purchases,
                'sales': sentiment.total_sales,
                'purchase_value': round(sentiment.purchase_value, 2),
                'sale_value': round(sentiment.sale_value, 2),
                'net_value': round(sentiment.net_value, 2),
                'has_cluster_buying': sentiment.has_cluster_buying()
            },
            'transactions': [
                {
                    'date': t.filing_date,
                    'insider': t.insider_name,
                    'title': t.insider_title,
                    'type': 'BUY' if t.is_purchase else 'SELL',
                    'shares': t.shares,
                    'price': t.price,
                    'value': t.value,
                    'is_csuite': t.is_csuite,
                    'is_large': t.is_large_purchase,
                    'shares_after': t.shares_owned_after
                }
                for t in sentiment.transactions
            ]
        }
        
        filename = os.path.join(OUTPUT_DIR, f"insider_{ticker}_{datetime.now().strftime('%Y%m%d')}.json")
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        return filename


if __name__ == "__main__":
    tracker = Form4Tracker()
    
    # Test with a sample ticker
    print("Testing Insider Trading Monitor...")
    print("="*50)
    
    # Get recent filings
    print("\nRecent Form 4 Filings:")
    filings = tracker.get_recent_filings(10)
    for f in filings[:5]:
        print(f"  - {f['date']}: {f['title'][:60]}...")
    
    print("\nInsider Trading Monitor initialized successfully!")
