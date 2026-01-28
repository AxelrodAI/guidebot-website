/**
 * Utility functions for Congress Tracker
 */

import { StockTrade } from './types.js';

/**
 * Parse STOCK Act amount ranges into min/max values
 */
export function parseAmountRange(range: string): { min: number; max: number } {
  if (!range) return { min: 0, max: 0 };
  
  // Common STOCK Act ranges
  const ranges: Record<string, { min: number; max: number }> = {
    '$1,001 - $15,000': { min: 1001, max: 15000 },
    '$15,001 - $50,000': { min: 15001, max: 50000 },
    '$50,001 - $100,000': { min: 50001, max: 100000 },
    '$100,001 - $250,000': { min: 100001, max: 250000 },
    '$250,001 - $500,000': { min: 250001, max: 500000 },
    '$500,001 - $1,000,000': { min: 500001, max: 1000000 },
    '$1,000,001 - $5,000,000': { min: 1000001, max: 5000000 },
    '$5,000,001 - $25,000,000': { min: 5000001, max: 25000000 },
    '$25,000,001 - $50,000,000': { min: 25000001, max: 50000000 },
    'Over $50,000,000': { min: 50000001, max: 100000000 }
  };
  
  // Normalize the range string
  const normalized = range.replace(/\s+/g, ' ').trim();
  
  if (ranges[normalized]) {
    return ranges[normalized];
  }
  
  // Try to parse custom format
  const match = range.match(/\$?([\d,]+)\s*[-–]\s*\$?([\d,]+)/);
  if (match) {
    return {
      min: parseInt(match[1].replace(/,/g, ''), 10),
      max: parseInt(match[2].replace(/,/g, ''), 10)
    };
  }
  
  return { min: 0, max: 0 };
}

/**
 * Parse transaction type from various formats
 */
export function parseTransactionType(type: string): StockTrade['transactionType'] {
  if (!type) return 'purchase';
  const lower = type.toLowerCase();
  
  if (lower.includes('sale') || lower.includes('sell') || lower.includes('sold')) {
    return 'sale';
  }
  if (lower.includes('exchange') || lower.includes('swap')) {
    return 'exchange';
  }
  return 'purchase';
}

/**
 * Normalize party affiliation
 */
export function normalizeParty(party?: string): 'D' | 'R' | 'I' {
  if (!party) return 'I';
  const first = party.charAt(0).toUpperCase();
  if (first === 'D') return 'D';
  if (first === 'R') return 'R';
  return 'I';
}

/**
 * Calculate midpoint of amount range for estimates
 */
export function getMidpointAmount(trade: StockTrade): number {
  return (trade.amountMin + trade.amountMax) / 2;
}

/**
 * Format currency for display
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
}

/**
 * Format date for display
 */
export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Calculate days between two dates
 */
export function daysBetween(date1: Date, date2: Date): number {
  const oneDay = 24 * 60 * 60 * 1000;
  return Math.round(Math.abs((date1.getTime() - date2.getTime()) / oneDay));
}

/**
 * Group trades by ticker
 */
export function groupTradesByTicker(trades: StockTrade[]): Map<string, StockTrade[]> {
  const groups = new Map<string, StockTrade[]>();
  
  for (const trade of trades) {
    const existing = groups.get(trade.ticker) || [];
    existing.push(trade);
    groups.set(trade.ticker, existing);
  }
  
  return groups;
}

/**
 * Group trades by member
 */
export function groupTradesByMember(trades: StockTrade[]): Map<string, StockTrade[]> {
  const groups = new Map<string, StockTrade[]>();
  
  for (const trade of trades) {
    const existing = groups.get(trade.memberName) || [];
    existing.push(trade);
    groups.set(trade.memberName, existing);
  }
  
  return groups;
}

/**
 * Calculate filing delay (days between transaction and disclosure)
 */
export function getFilingDelay(trade: StockTrade): number {
  return daysBetween(trade.transactionDate, trade.disclosureDate);
}

/**
 * Check if trade is considered "large"
 */
export function isLargeTrade(trade: StockTrade, threshold: number = 100000): boolean {
  return trade.amountMin >= threshold;
}

/**
 * Get sector for a ticker (simplified - would use real lookup in production)
 */
export function getTickerSector(ticker: string): string {
  const sectors: Record<string, string> = {
    // Tech
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
    'META': 'Technology', 'AMZN': 'Technology', 'NVDA': 'Technology', 'AMD': 'Technology',
    'INTC': 'Technology', 'CRM': 'Technology', 'ORCL': 'Technology', 'IBM': 'Technology',
    
    // Finance
    'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
    'MS': 'Financials', 'C': 'Financials', 'BRK.A': 'Financials', 'BRK.B': 'Financials',
    
    // Healthcare
    'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'MRK': 'Healthcare',
    'ABBV': 'Healthcare', 'LLY': 'Healthcare', 'BMY': 'Healthcare', 'AMGN': 'Healthcare',
    
    // Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy',
    'EOG': 'Energy', 'PXD': 'Energy', 'MPC': 'Energy', 'VLO': 'Energy',
    
    // Defense
    'LMT': 'Defense', 'RTX': 'Defense', 'NOC': 'Defense', 'BA': 'Defense',
    'GD': 'Defense', 'LHX': 'Defense',
    
    // Consumer
    'WMT': 'Consumer', 'COST': 'Consumer', 'TGT': 'Consumer', 'HD': 'Consumer',
    'MCD': 'Consumer', 'SBUX': 'Consumer', 'NKE': 'Consumer', 'DIS': 'Consumer'
  };
  
  return sectors[ticker.toUpperCase()] || 'Unknown';
}

/**
 * Generate unique ID
 */
export function generateId(prefix: string = ''): string {
  return `${prefix}${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
