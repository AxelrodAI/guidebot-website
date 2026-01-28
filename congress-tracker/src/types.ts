/**
 * Congressional Trading Monitor - Type Definitions
 * Tracks stock trades disclosed under STOCK Act
 */

export interface CongressMember {
  id: string;
  name: string;
  party: 'D' | 'R' | 'I';
  chamber: 'House' | 'Senate';
  state: string;
  district?: string;
  committees: string[];
}

export interface StockTrade {
  id: string;
  memberId: string;
  memberName: string;
  party: 'D' | 'R' | 'I';
  chamber: 'House' | 'Senate';
  
  // Trade details
  ticker: string;
  companyName: string;
  transactionType: 'purchase' | 'sale' | 'exchange';
  transactionDate: Date;
  disclosureDate: Date;
  
  // Amount range (STOCK Act uses ranges, not exact amounts)
  amountMin: number;
  amountMax: number;
  amountRange: string; // e.g., "$15,001 - $50,000"
  
  // Additional metadata
  assetType: 'stock' | 'option' | 'bond' | 'etf' | 'mutual_fund' | 'other';
  owner: 'self' | 'spouse' | 'dependent' | 'joint';
  filingUrl?: string;
  comments?: string;
}

export interface MemberPortfolio {
  memberId: string;
  memberName: string;
  party: 'D' | 'R' | 'I';
  chamber: 'House' | 'Senate';
  
  positions: PortfolioPosition[];
  totalEstimatedValue: {
    min: number;
    max: number;
  };
  
  // Performance metrics
  tradeCount30d: number;
  tradeCount90d: number;
  mostTradedTickers: string[];
}

export interface PortfolioPosition {
  ticker: string;
  companyName: string;
  estimatedShares?: number;
  estimatedValueMin: number;
  estimatedValueMax: number;
  lastTradeDate: Date;
  lastTradeType: 'purchase' | 'sale';
}

export interface TradeAlert {
  id: string;
  type: 'large_trade' | 'cluster_trade' | 'sector_activity' | 'timing_suspicious' | 'committee_related';
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: Date;
  
  // Alert details
  title: string;
  description: string;
  trades: StockTrade[];
  
  // For cluster trades
  memberCount?: number;
  
  // Related context
  ticker?: string;
  sector?: string;
  potentialCatalyst?: string;
}

export interface ClusterTradeEvent {
  ticker: string;
  companyName: string;
  windowDays: number;
  trades: StockTrade[];
  memberCount: number;
  totalAmountMin: number;
  totalAmountMax: number;
  direction: 'buy' | 'sell' | 'mixed';
  firstTradeDate: Date;
  lastTradeDate: Date;
}

export interface PerformanceMetrics {
  memberId: string;
  memberName: string;
  period: '30d' | '90d' | '1y' | 'all';
  
  // Trading activity
  totalTrades: number;
  buyCount: number;
  sellCount: number;
  
  // Performance vs benchmark (S&P 500)
  portfolioReturnEstimate: number; // Based on midpoint of ranges
  benchmarkReturn: number;
  alphaEstimate: number;
  
  // Trade success metrics
  profitableTrades?: number;
  unprofitableTrades?: number;
}

export interface DailyMarketComparison {
  date: Date;
  
  // Congress activity
  congressBuyCount: number;
  congressSellCount: number;
  congressNetBuys: number;
  
  // Market data
  spyReturn: number;
  spyClose: number;
  
  // Sentiment
  congressSentiment: 'bullish' | 'bearish' | 'neutral';
}

export interface TrackerConfig {
  dataDir: string;
  alertThresholds: {
    largeTradeMin: number; // Minimum amount for "large trade" alert
    clusterWindowDays: number; // Window for detecting cluster trades
    clusterMinMembers: number; // Minimum members for cluster alert
  };
  watchlist: string[]; // Tickers to specifically monitor
  watchedMembers: string[]; // Specific members to monitor closely
}

export interface DataStore {
  trades: StockTrade[];
  members: CongressMember[];
  alerts: TradeAlert[];
  lastFetch: Date;
  metadata: {
    totalTrades: number;
    dateRange: {
      start: Date;
      end: Date;
    };
  };
}
