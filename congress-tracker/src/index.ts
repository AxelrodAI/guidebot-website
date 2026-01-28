/**
 * Congressional Trading Monitor
 * Track stock trades disclosed by Congress members under STOCK Act
 * 
 * Main entry point - exports all modules for programmatic use
 */

export * from './types.js';
export * from './utils.js';
export { CongressTradeFetcher, FetchOptions, fetcher } from './fetcher.js';
export { CongressTradeAnalytics, AnalyticsConfig, analytics } from './analytics.js';
export { CongressDataStorage, storage } from './storage.js';
export { generateDashboard, saveDashboard, DashboardData } from './dashboard.js';

// Quick access functions
import { fetcher } from './fetcher.js';
import { analytics } from './analytics.js';
import { storage } from './storage.js';
import { saveDashboard, DashboardData } from './dashboard.js';

/**
 * Fetch and analyze congressional trades in one call
 */
export async function fetchAndAnalyze(options: {
  days?: number;
  generateDashboard?: boolean;
  dashboardPath?: string;
} = {}): Promise<{
  tradesAdded: number;
  totalTrades: number;
  sentiment: ReturnType<typeof analytics.calculateCongressSentiment>;
  clusters: ReturnType<typeof analytics.detectClusterTrades>;
  alerts: ReturnType<typeof analytics.generateAlerts>;
}> {
  const { days = 90, generateDashboard: genDash = false, dashboardPath = './congress-dashboard.html' } = options;
  
  // Fetch trades
  const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
  const trades = await fetcher.fetchTrades({ startDate, endDate: new Date() });
  const tradesAdded = storage.addTrades(trades);
  
  // Get all stored trades
  const allTrades = storage.getTrades();
  
  // Analyze
  const sentiment = analytics.calculateCongressSentiment(allTrades);
  const clusters = analytics.detectClusterTrades(allTrades);
  const alerts = analytics.generateAlerts(allTrades);
  
  // Store alerts
  storage.addAlerts(alerts);
  
  // Generate dashboard if requested
  if (genDash) {
    const data: DashboardData = {
      trades: allTrades,
      alerts,
      clusters,
      sentiment,
      activeTraders: analytics.getMostActiveTraders(allTrades),
      lastUpdated: new Date()
    };
    saveDashboard(data, dashboardPath);
  }
  
  return {
    tradesAdded,
    totalTrades: allTrades.length,
    sentiment,
    clusters,
    alerts
  };
}

/**
 * Get alerts for a specific ticker
 */
export function getTickerAlerts(ticker: string): {
  trades: ReturnType<typeof storage.getTradesForTicker>;
  relatedClusters: ReturnType<typeof analytics.detectClusterTrades>;
  sentiment: 'bullish' | 'bearish' | 'neutral';
} {
  const trades = storage.getTradesForTicker(ticker);
  const allTrades = storage.getTrades();
  const clusters = analytics.detectClusterTrades(allTrades);
  const relatedClusters = clusters.filter(c => c.ticker.toUpperCase() === ticker.toUpperCase());
  
  // Calculate ticker sentiment
  const buys = trades.filter(t => t.transactionType === 'purchase').length;
  const sells = trades.filter(t => t.transactionType === 'sale').length;
  let sentiment: 'bullish' | 'bearish' | 'neutral' = 'neutral';
  if (buys > sells + 2) sentiment = 'bullish';
  else if (sells > buys + 2) sentiment = 'bearish';
  
  return { trades, relatedClusters, sentiment };
}

/**
 * Get member trading profile
 */
export function getMemberProfile(memberName: string): {
  trades: ReturnType<typeof storage.getTradesForMember>;
  portfolio: ReturnType<typeof analytics.buildMemberPortfolio>;
  tradeCount: number;
} {
  const trades = storage.getTradesForMember(memberName);
  const portfolio = analytics.buildMemberPortfolio(storage.getTrades(), memberName);
  
  return {
    trades,
    portfolio,
    tradeCount: trades.length
  };
}

console.log('Congressional Trading Monitor loaded');
console.log('Use: fetchAndAnalyze(), getTickerAlerts(ticker), getMemberProfile(name)');
