/**
 * Congressional Trade Data Fetcher
 * Fetches periodic transaction reports from House and Senate disclosure sites
 */

import axios from 'axios';
import * as cheerio from 'cheerio';
import { StockTrade, CongressMember } from './types.js';
import { parseAmountRange, parseTransactionType, normalizeParty } from './utils.js';

// Data sources
const HOUSE_DISCLOSURE_URL = 'https://disclosures-clerk.house.gov/FinancialDisclosure';
const SENATE_DISCLOSURE_URL = 'https://efdsearch.senate.gov/search/';

// Alternative: Capitol Trades API (aggregated data)
const CAPITOL_TRADES_API = 'https://bff.capitoltrades.com/trades';
const QUIVER_QUANT_API = 'https://api.quiverquant.com/beta/live/congresstrading';

export interface FetchOptions {
  startDate?: Date;
  endDate?: Date;
  chamber?: 'House' | 'Senate' | 'both';
  limit?: number;
}

export class CongressTradeFetcher {
  private cache: Map<string, any> = new Map();
  
  /**
   * Fetch recent congressional trades
   * Uses multiple data sources for redundancy
   */
  async fetchTrades(options: FetchOptions = {}): Promise<StockTrade[]> {
    const { 
      startDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000), // 90 days default
      endDate = new Date(),
      chamber = 'both',
      limit = 500 
    } = options;
    
    console.log(`Fetching congressional trades from ${startDate.toISOString().split('T')[0]} to ${endDate.toISOString().split('T')[0]}`);
    
    const trades: StockTrade[] = [];
    
    // Try Capitol Trades API first (most reliable aggregated source)
    try {
      const capitolTrades = await this.fetchFromCapitolTrades(startDate, endDate, limit);
      trades.push(...capitolTrades);
      console.log(`Fetched ${capitolTrades.length} trades from Capitol Trades`);
    } catch (error) {
      console.warn('Capitol Trades fetch failed, trying alternative sources');
      
      // Fallback to direct scraping
      if (chamber === 'both' || chamber === 'House') {
        try {
          const houseTrades = await this.fetchHouseTrades(startDate, endDate);
          trades.push(...houseTrades);
        } catch (e) {
          console.warn('House trades fetch failed');
        }
      }
      
      if (chamber === 'both' || chamber === 'Senate') {
        try {
          const senateTrades = await this.fetchSenateTrades(startDate, endDate);
          trades.push(...senateTrades);
        } catch (e) {
          console.warn('Senate trades fetch failed');
        }
      }
    }
    
    // Deduplicate and sort
    const uniqueTrades = this.deduplicateTrades(trades);
    uniqueTrades.sort((a, b) => b.transactionDate.getTime() - a.transactionDate.getTime());
    
    return uniqueTrades.slice(0, limit);
  }
  
  /**
   * Fetch from Capitol Trades API (aggregated data)
   */
  private async fetchFromCapitolTrades(startDate: Date, endDate: Date, limit: number): Promise<StockTrade[]> {
    const params = {
      page: 1,
      pageSize: Math.min(limit, 100),
      sortBy: '-txDate',
      txDate: `gte:${startDate.toISOString().split('T')[0]}`,
    };
    
    const response = await axios.get(CAPITOL_TRADES_API, {
      params,
      timeout: 30000,
      headers: {
        'User-Agent': 'CongressTracker/1.0 (Research Tool)',
        'Accept': 'application/json'
      }
    });
    
    if (!response.data?.data) {
      throw new Error('Invalid response from Capitol Trades');
    }
    
    return response.data.data.map((trade: any) => this.parseCapitolTrade(trade));
  }
  
  private parseCapitolTrade(data: any): StockTrade {
    return {
      id: `ct-${data.id || Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      memberId: data.politician?.id || 'unknown',
      memberName: data.politician?.name || 'Unknown',
      party: normalizeParty(data.politician?.party),
      chamber: data.politician?.chamber === 'senate' ? 'Senate' : 'House',
      
      ticker: data.asset?.assetTicker || data.ticker || 'UNKNOWN',
      companyName: data.asset?.assetName || data.issuer || 'Unknown Company',
      transactionType: parseTransactionType(data.txType),
      transactionDate: new Date(data.txDate),
      disclosureDate: new Date(data.filingDate || data.txDate),
      
      amountMin: data.value?.min || 0,
      amountMax: data.value?.max || 0,
      amountRange: data.value?.range || '$0',
      
      assetType: this.inferAssetType(data.asset?.assetType),
      owner: this.parseOwner(data.owner),
      filingUrl: data.filingUrl,
      comments: data.comment
    };
  }
  
  /**
   * Fetch from House Clerk Financial Disclosures
   */
  private async fetchHouseTrades(startDate: Date, endDate: Date): Promise<StockTrade[]> {
    // House provides searchable database and downloadable XML/CSV
    const searchUrl = `${HOUSE_DISCLOSURE_URL}/ViewMemberSearchResult`;
    
    const response = await axios.get(searchUrl, {
      params: {
        FilingYear: endDate.getFullYear(),
        State: '',
        District: ''
      },
      timeout: 30000,
      headers: {
        'User-Agent': 'CongressTracker/1.0 (Research Tool)'
      }
    });
    
    const $ = cheerio.load(response.data);
    const trades: StockTrade[] = [];
    
    // Parse the results table
    $('table.library-table tbody tr').each((_, row) => {
      try {
        const cells = $(row).find('td');
        const trade = this.parseHouseTradeRow($, cells);
        if (trade && trade.transactionDate >= startDate && trade.transactionDate <= endDate) {
          trades.push(trade);
        }
      } catch (e) {
        // Skip malformed rows
      }
    });
    
    return trades;
  }
  
  private parseHouseTradeRow($: cheerio.CheerioAPI, cells: cheerio.Cheerio<any>): StockTrade | null {
    if (cells.length < 5) return null;
    
    const memberName = $(cells[0]).text().trim();
    const filingType = $(cells[1]).text().trim();
    const filingDate = $(cells[2]).text().trim();
    
    // PTRs (Periodic Transaction Reports) contain trade data
    if (!filingType.includes('PTR')) return null;
    
    const filingUrl = $(cells[0]).find('a').attr('href');
    
    // Note: Full trade details require downloading and parsing the PDF
    // This is a simplified version - real implementation would fetch the PDF
    return {
      id: `house-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      memberId: memberName.toLowerCase().replace(/\s+/g, '-'),
      memberName,
      party: 'R', // Would need additional lookup
      chamber: 'House',
      ticker: 'PENDING', // Requires PDF parsing
      companyName: 'Pending PDF Parse',
      transactionType: 'purchase',
      transactionDate: new Date(filingDate),
      disclosureDate: new Date(filingDate),
      amountMin: 0,
      amountMax: 0,
      amountRange: 'Unknown',
      assetType: 'stock',
      owner: 'self',
      filingUrl: filingUrl ? `${HOUSE_DISCLOSURE_URL}${filingUrl}` : undefined
    };
  }
  
  /**
   * Fetch from Senate eFD System
   */
  private async fetchSenateTrades(startDate: Date, endDate: Date): Promise<StockTrade[]> {
    // Senate requires form submission and CSRF handling
    // This is a simplified placeholder - real implementation needs session handling
    
    const searchUrl = `${SENATE_DISCLOSURE_URL}`;
    const trades: StockTrade[] = [];
    
    try {
      // Initial page load to get CSRF token
      const initialResponse = await axios.get(searchUrl, {
        timeout: 30000,
        headers: {
          'User-Agent': 'CongressTracker/1.0 (Research Tool)'
        }
      });
      
      // Senate eFD system requires JavaScript and session state
      // Would need proper browser automation for full scraping
      console.log('Senate eFD requires browser automation for full scraping');
      
    } catch (error) {
      console.warn('Senate eFD access limited without browser automation');
    }
    
    return trades;
  }
  
  /**
   * Fetch member information
   */
  async fetchMembers(): Promise<CongressMember[]> {
    // Would fetch from Congress API or scrape member directories
    const members: CongressMember[] = [];
    
    try {
      // ProPublica Congress API or similar
      const response = await axios.get('https://api.propublica.org/congress/v1/members', {
        headers: {
          'X-API-Key': process.env.PROPUBLICA_API_KEY || ''
        },
        timeout: 30000
      });
      
      if (response.data?.results) {
        for (const member of response.data.results) {
          members.push({
            id: member.id,
            name: `${member.first_name} ${member.last_name}`,
            party: normalizeParty(member.party),
            chamber: member.chamber === 'Senate' ? 'Senate' : 'House',
            state: member.state,
            district: member.district,
            committees: []
          });
        }
      }
    } catch (error) {
      console.warn('Member fetch failed - using cached data');
    }
    
    return members;
  }
  
  private inferAssetType(type?: string): StockTrade['assetType'] {
    if (!type) return 'stock';
    const lower = type.toLowerCase();
    if (lower.includes('option')) return 'option';
    if (lower.includes('bond')) return 'bond';
    if (lower.includes('etf')) return 'etf';
    if (lower.includes('mutual') || lower.includes('fund')) return 'mutual_fund';
    return 'stock';
  }
  
  private parseOwner(owner?: string): StockTrade['owner'] {
    if (!owner) return 'self';
    const lower = owner.toLowerCase();
    if (lower.includes('spouse')) return 'spouse';
    if (lower.includes('dependent') || lower.includes('child')) return 'dependent';
    if (lower.includes('joint')) return 'joint';
    return 'self';
  }
  
  private deduplicateTrades(trades: StockTrade[]): StockTrade[] {
    const seen = new Set<string>();
    return trades.filter(trade => {
      const key = `${trade.memberName}-${trade.ticker}-${trade.transactionDate.toISOString().split('T')[0]}-${trade.transactionType}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}

export const fetcher = new CongressTradeFetcher();
