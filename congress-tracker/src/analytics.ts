/**
 * Congressional Trade Analytics
 * Analyze patterns, detect clusters, track performance
 */

import { 
  StockTrade, 
  ClusterTradeEvent, 
  PerformanceMetrics, 
  MemberPortfolio,
  TradeAlert 
} from './types.js';
import { 
  getMidpointAmount, 
  daysBetween, 
  groupTradesByTicker, 
  groupTradesByMember,
  isLargeTrade,
  getTickerSector,
  formatCurrency,
  formatDate,
  generateId
} from './utils.js';

export interface AnalyticsConfig {
  clusterWindowDays: number;
  clusterMinMembers: number;
  largeTradeThreshold: number;
  lateFilingDays: number;
}

const DEFAULT_CONFIG: AnalyticsConfig = {
  clusterWindowDays: 14,
  clusterMinMembers: 3,
  largeTradeThreshold: 100000,
  lateFilingDays: 45 // STOCK Act requires disclosure within 45 days
};

export class CongressTradeAnalytics {
  private config: AnalyticsConfig;
  
  constructor(config: Partial<AnalyticsConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }
  
  /**
   * Detect cluster trades - multiple members trading same stock within window
   */
  detectClusterTrades(trades: StockTrade[]): ClusterTradeEvent[] {
    const clusters: ClusterTradeEvent[] = [];
    const byTicker = groupTradesByTicker(trades);
    
    for (const [ticker, tickerTrades] of byTicker) {
      // Sort by date
      const sorted = [...tickerTrades].sort(
        (a, b) => a.transactionDate.getTime() - b.transactionDate.getTime()
      );
      
      // Sliding window to find clusters
      for (let i = 0; i < sorted.length; i++) {
        const windowStart = sorted[i].transactionDate;
        const windowEnd = new Date(windowStart.getTime() + this.config.clusterWindowDays * 24 * 60 * 60 * 1000);
        
        const windowTrades = sorted.filter(
          t => t.transactionDate >= windowStart && t.transactionDate <= windowEnd
        );
        
        // Get unique members in window
        const members = new Set(windowTrades.map(t => t.memberName));
        
        if (members.size >= this.config.clusterMinMembers) {
          // Determine direction (buy/sell/mixed)
          const buys = windowTrades.filter(t => t.transactionType === 'purchase').length;
          const sells = windowTrades.filter(t => t.transactionType === 'sale').length;
          let direction: 'buy' | 'sell' | 'mixed' = 'mixed';
          if (buys > 0 && sells === 0) direction = 'buy';
          else if (sells > 0 && buys === 0) direction = 'sell';
          
          // Calculate totals
          let totalMin = 0, totalMax = 0;
          for (const t of windowTrades) {
            totalMin += t.amountMin;
            totalMax += t.amountMax;
          }
          
          clusters.push({
            ticker,
            companyName: windowTrades[0].companyName,
            windowDays: this.config.clusterWindowDays,
            trades: windowTrades,
            memberCount: members.size,
            totalAmountMin: totalMin,
            totalAmountMax: totalMax,
            direction,
            firstTradeDate: windowTrades[0].transactionDate,
            lastTradeDate: windowTrades[windowTrades.length - 1].transactionDate
          });
          
          // Skip processed trades in window
          i += windowTrades.length - 1;
        }
      }
    }
    
    // Sort by member count (most significant first)
    clusters.sort((a, b) => b.memberCount - a.memberCount);
    
    return clusters;
  }
  
  /**
   * Find large trades above threshold
   */
  findLargeTrades(trades: StockTrade[]): StockTrade[] {
    return trades
      .filter(t => isLargeTrade(t, this.config.largeTradeThreshold))
      .sort((a, b) => b.amountMin - a.amountMin);
  }
  
  /**
   * Analyze sector activity
   */
  analyzeSectorActivity(trades: StockTrade[]): Map<string, {
    buyCount: number;
    sellCount: number;
    netDirection: 'bullish' | 'bearish' | 'neutral';
    totalValueMin: number;
    totalValueMax: number;
    topTickers: string[];
  }> {
    const sectors = new Map<string, {
      buyCount: number;
      sellCount: number;
      netDirection: 'bullish' | 'bearish' | 'neutral';
      totalValueMin: number;
      totalValueMax: number;
      trades: StockTrade[];
    }>();
    
    for (const trade of trades) {
      const sector = getTickerSector(trade.ticker);
      const existing = sectors.get(sector) || {
        buyCount: 0,
        sellCount: 0,
        netDirection: 'neutral' as const,
        totalValueMin: 0,
        totalValueMax: 0,
        trades: []
      };
      
      if (trade.transactionType === 'purchase') {
        existing.buyCount++;
        existing.totalValueMin += trade.amountMin;
        existing.totalValueMax += trade.amountMax;
      } else if (trade.transactionType === 'sale') {
        existing.sellCount++;
        existing.totalValueMin -= trade.amountMin;
        existing.totalValueMax -= trade.amountMax;
      }
      
      existing.trades.push(trade);
      sectors.set(sector, existing);
    }
    
    // Calculate net direction and top tickers
    const result = new Map<string, {
      buyCount: number;
      sellCount: number;
      netDirection: 'bullish' | 'bearish' | 'neutral';
      totalValueMin: number;
      totalValueMax: number;
      topTickers: string[];
    }>();
    
    for (const [sector, data] of sectors) {
      const netBuys = data.buyCount - data.sellCount;
      let netDirection: 'bullish' | 'bearish' | 'neutral' = 'neutral';
      if (netBuys > 2) netDirection = 'bullish';
      else if (netBuys < -2) netDirection = 'bearish';
      
      // Get top tickers by trade count
      const tickerCounts = new Map<string, number>();
      for (const t of data.trades) {
        tickerCounts.set(t.ticker, (tickerCounts.get(t.ticker) || 0) + 1);
      }
      const topTickers = [...tickerCounts.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([ticker]) => ticker);
      
      result.set(sector, {
        buyCount: data.buyCount,
        sellCount: data.sellCount,
        netDirection,
        totalValueMin: Math.abs(data.totalValueMin),
        totalValueMax: Math.abs(data.totalValueMax),
        topTickers
      });
    }
    
    return result;
  }
  
  /**
   * Build member portfolio based on trade history
   */
  buildMemberPortfolio(trades: StockTrade[], memberName: string): MemberPortfolio | null {
    const memberTrades = trades.filter(t => t.memberName === memberName);
    if (memberTrades.length === 0) return null;
    
    const firstTrade = memberTrades[0];
    const positions = new Map<string, {
      ticker: string;
      companyName: string;
      netValueMin: number;
      netValueMax: number;
      lastTradeDate: Date;
      lastTradeType: 'purchase' | 'sale';
    }>();
    
    // Build positions from trade history
    for (const trade of memberTrades) {
      const existing = positions.get(trade.ticker) || {
        ticker: trade.ticker,
        companyName: trade.companyName,
        netValueMin: 0,
        netValueMax: 0,
        lastTradeDate: trade.transactionDate,
        lastTradeType: trade.transactionType as 'purchase' | 'sale'
      };
      
      if (trade.transactionType === 'purchase') {
        existing.netValueMin += trade.amountMin;
        existing.netValueMax += trade.amountMax;
      } else if (trade.transactionType === 'sale') {
        existing.netValueMin -= trade.amountMin;
        existing.netValueMax -= trade.amountMax;
      }
      
      if (trade.transactionDate > existing.lastTradeDate) {
        existing.lastTradeDate = trade.transactionDate;
        existing.lastTradeType = trade.transactionType as 'purchase' | 'sale';
      }
      
      positions.set(trade.ticker, existing);
    }
    
    // Convert to portfolio positions (only include net long positions)
    const portfolioPositions = [...positions.values()]
      .filter(p => p.netValueMin > 0)
      .map(p => ({
        ticker: p.ticker,
        companyName: p.companyName,
        estimatedValueMin: p.netValueMin,
        estimatedValueMax: p.netValueMax,
        lastTradeDate: p.lastTradeDate,
        lastTradeType: p.lastTradeType
      }));
    
    // Calculate totals
    const totalMin = portfolioPositions.reduce((sum, p) => sum + p.estimatedValueMin, 0);
    const totalMax = portfolioPositions.reduce((sum, p) => sum + p.estimatedValueMax, 0);
    
    // Recent activity
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const ninetyDaysAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
    
    const tradeCount30d = memberTrades.filter(t => t.transactionDate >= thirtyDaysAgo).length;
    const tradeCount90d = memberTrades.filter(t => t.transactionDate >= ninetyDaysAgo).length;
    
    // Most traded tickers
    const tickerCounts = new Map<string, number>();
    for (const t of memberTrades) {
      tickerCounts.set(t.ticker, (tickerCounts.get(t.ticker) || 0) + 1);
    }
    const mostTradedTickers = [...tickerCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([ticker]) => ticker);
    
    return {
      memberId: firstTrade.memberId,
      memberName,
      party: firstTrade.party,
      chamber: firstTrade.chamber,
      positions: portfolioPositions,
      totalEstimatedValue: { min: totalMin, max: totalMax },
      tradeCount30d,
      tradeCount90d,
      mostTradedTickers
    };
  }
  
  /**
   * Generate alerts from trade analysis
   */
  generateAlerts(trades: StockTrade[]): TradeAlert[] {
    const alerts: TradeAlert[] = [];
    
    // Alert 1: Large trades
    const largeTrades = this.findLargeTrades(trades);
    for (const trade of largeTrades.slice(0, 10)) { // Top 10 largest
      alerts.push({
        id: generateId('alert-large-'),
        type: 'large_trade',
        severity: trade.amountMin >= 1000000 ? 'critical' : trade.amountMin >= 500000 ? 'high' : 'medium',
        timestamp: new Date(),
        title: `Large ${trade.transactionType} by ${trade.memberName}`,
        description: `${trade.memberName} (${trade.party}-${trade.chamber}) ${trade.transactionType === 'purchase' ? 'bought' : 'sold'} ${trade.ticker} (${trade.companyName}) for ${trade.amountRange}`,
        trades: [trade],
        ticker: trade.ticker
      });
    }
    
    // Alert 2: Cluster trades
    const clusters = this.detectClusterTrades(trades);
    for (const cluster of clusters.slice(0, 5)) { // Top 5 clusters
      const membersList = [...new Set(cluster.trades.map(t => t.memberName))].slice(0, 5);
      alerts.push({
        id: generateId('alert-cluster-'),
        type: 'cluster_trade',
        severity: cluster.memberCount >= 5 ? 'critical' : cluster.memberCount >= 4 ? 'high' : 'medium',
        timestamp: new Date(),
        title: `${cluster.memberCount} Congress members ${cluster.direction === 'buy' ? 'buying' : cluster.direction === 'sell' ? 'selling' : 'trading'} ${cluster.ticker}`,
        description: `Multiple members traded ${cluster.ticker} (${cluster.companyName}) within ${cluster.windowDays} days. Members: ${membersList.join(', ')}${cluster.memberCount > 5 ? ` and ${cluster.memberCount - 5} more` : ''}. Total value: ${formatCurrency(cluster.totalAmountMin)} - ${formatCurrency(cluster.totalAmountMax)}`,
        trades: cluster.trades,
        memberCount: cluster.memberCount,
        ticker: cluster.ticker
      });
    }
    
    // Alert 3: Sector concentration
    const sectorActivity = this.analyzeSectorActivity(trades);
    for (const [sector, data] of sectorActivity) {
      if (data.netDirection !== 'neutral' && (data.buyCount + data.sellCount) >= 10) {
        alerts.push({
          id: generateId('alert-sector-'),
          type: 'sector_activity',
          severity: (data.buyCount + data.sellCount) >= 20 ? 'high' : 'medium',
          timestamp: new Date(),
          title: `Congress ${data.netDirection} on ${sector}`,
          description: `${sector} sector seeing significant congressional activity: ${data.buyCount} buys, ${data.sellCount} sells. Top tickers: ${data.topTickers.join(', ')}`,
          trades: [],
          sector
        });
      }
    }
    
    // Sort by severity and timestamp
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    alerts.sort((a, b) => {
      const sevDiff = severityOrder[a.severity] - severityOrder[b.severity];
      if (sevDiff !== 0) return sevDiff;
      return b.timestamp.getTime() - a.timestamp.getTime();
    });
    
    return alerts;
  }
  
  /**
   * Find late filings (potential STOCK Act violations)
   */
  findLateFilings(trades: StockTrade[]): StockTrade[] {
    return trades.filter(t => {
      const delay = daysBetween(t.transactionDate, t.disclosureDate);
      return delay > this.config.lateFilingDays;
    }).sort((a, b) => {
      const delayA = daysBetween(a.transactionDate, a.disclosureDate);
      const delayB = daysBetween(b.transactionDate, b.disclosureDate);
      return delayB - delayA;
    });
  }
  
  /**
   * Calculate overall Congress sentiment
   */
  calculateCongressSentiment(trades: StockTrade[]): {
    sentiment: 'bullish' | 'bearish' | 'neutral';
    buyCount: number;
    sellCount: number;
    netBuyValue: { min: number; max: number };
    topBuys: string[];
    topSells: string[];
  } {
    let buyCount = 0, sellCount = 0;
    let buyValueMin = 0, buyValueMax = 0;
    let sellValueMin = 0, sellValueMax = 0;
    
    const buys = new Map<string, number>();
    const sells = new Map<string, number>();
    
    for (const trade of trades) {
      if (trade.transactionType === 'purchase') {
        buyCount++;
        buyValueMin += trade.amountMin;
        buyValueMax += trade.amountMax;
        buys.set(trade.ticker, (buys.get(trade.ticker) || 0) + 1);
      } else if (trade.transactionType === 'sale') {
        sellCount++;
        sellValueMin += trade.amountMin;
        sellValueMax += trade.amountMax;
        sells.set(trade.ticker, (sells.get(trade.ticker) || 0) + 1);
      }
    }
    
    const netMin = buyValueMin - sellValueMin;
    const netMax = buyValueMax - sellValueMax;
    const midpoint = (netMin + netMax) / 2;
    
    let sentiment: 'bullish' | 'bearish' | 'neutral' = 'neutral';
    if (midpoint > 1000000) sentiment = 'bullish';
    else if (midpoint < -1000000) sentiment = 'bearish';
    
    const topBuys = [...buys.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([t]) => t);
    const topSells = [...sells.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([t]) => t);
    
    return {
      sentiment,
      buyCount,
      sellCount,
      netBuyValue: { min: netMin, max: netMax },
      topBuys,
      topSells
    };
  }
  
  /**
   * Get most active traders
   */
  getMostActiveTraders(trades: StockTrade[], limit: number = 10): {
    memberName: string;
    party: 'D' | 'R' | 'I';
    chamber: 'House' | 'Senate';
    tradeCount: number;
    totalValueMin: number;
    totalValueMax: number;
  }[] {
    const byMember = groupTradesByMember(trades);
    
    const traders = [...byMember.entries()].map(([name, memberTrades]) => {
      const first = memberTrades[0];
      let totalMin = 0, totalMax = 0;
      for (const t of memberTrades) {
        totalMin += t.amountMin;
        totalMax += t.amountMax;
      }
      
      return {
        memberName: name,
        party: first.party,
        chamber: first.chamber,
        tradeCount: memberTrades.length,
        totalValueMin: totalMin,
        totalValueMax: totalMax
      };
    });
    
    return traders.sort((a, b) => b.tradeCount - a.tradeCount).slice(0, limit);
  }
}

export const analytics = new CongressTradeAnalytics();
