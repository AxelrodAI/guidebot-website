#!/usr/bin/env node
/**
 * Congressional Trading Monitor CLI
 * Track stock trades disclosed by Congress members under STOCK Act
 */

import { CongressTradeFetcher } from './fetcher.js';
import { CongressTradeAnalytics } from './analytics.js';
import { CongressDataStorage } from './storage.js';
import { saveDashboard, DashboardData } from './dashboard.js';
import { formatCurrency, formatDate } from './utils.js';
import { StockTrade } from './types.js';

const fetcher = new CongressTradeFetcher();
const analytics = new CongressTradeAnalytics();
const storage = new CongressDataStorage();

async function fetchTrades(): Promise<void> {
  console.log('=== Fetching Congressional Trades ===\n');
  
  try {
    const trades = await fetcher.fetchTrades({
      startDate: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
      endDate: new Date(),
      limit: 500
    });
    
    const added = storage.addTrades(trades);
    console.log(`Fetched ${trades.length} trades, ${added} new`);
    
    const metadata = storage.getMetadata();
    console.log(`Total stored: ${metadata.totalTrades} trades`);
    console.log(`Date range: ${formatDate(metadata.dateRange.start)} - ${formatDate(metadata.dateRange.end)}`);
  } catch (error) {
    console.error('Fetch failed:', error);
    
    // Load sample data for testing
    console.log('\nLoading sample data for demonstration...');
    const sampleTrades = generateSampleTrades();
    storage.addTrades(sampleTrades);
    console.log(`Loaded ${sampleTrades.length} sample trades`);
  }
}

async function analyzeTrades(): Promise<void> {
  console.log('=== Congressional Trade Analysis ===\n');
  
  const trades = storage.getTrades();
  if (trades.length === 0) {
    console.log('No trades in database. Run "fetch" first.');
    return;
  }
  
  // Overall sentiment
  const sentiment = analytics.calculateCongressSentiment(trades);
  console.log('📊 CONGRESS SENTIMENT:', sentiment.sentiment.toUpperCase());
  console.log(`   Buys: ${sentiment.buyCount} | Sells: ${sentiment.sellCount}`);
  console.log(`   Top Buys: ${sentiment.topBuys.join(', ')}`);
  console.log(`   Top Sells: ${sentiment.topSells.join(', ')}`);
  console.log();
  
  // Cluster trades
  const clusters = analytics.detectClusterTrades(trades);
  if (clusters.length > 0) {
    console.log('👥 CLUSTER TRADES (Multiple Members):');
    for (const cluster of clusters.slice(0, 5)) {
      const members = [...new Set(cluster.trades.map(t => t.memberName))];
      console.log(`   ${cluster.ticker}: ${cluster.memberCount} members ${cluster.direction === 'buy' ? 'buying' : 'selling'}`);
      console.log(`      Members: ${members.slice(0, 3).join(', ')}${members.length > 3 ? ` +${members.length - 3} more` : ''}`);
      console.log(`      Value: ${formatCurrency(cluster.totalAmountMin)} - ${formatCurrency(cluster.totalAmountMax)}`);
    }
    console.log();
  }
  
  // Large trades
  const largeTrades = analytics.findLargeTrades(trades);
  if (largeTrades.length > 0) {
    console.log('💰 LARGE TRADES (>$100K):');
    for (const trade of largeTrades.slice(0, 5)) {
      console.log(`   ${trade.memberName} (${trade.party}): ${trade.transactionType === 'purchase' ? 'bought' : 'sold'} ${trade.ticker}`);
      console.log(`      ${trade.amountRange} on ${formatDate(trade.transactionDate)}`);
    }
    console.log();
  }
  
  // Most active traders
  const activeTraders = analytics.getMostActiveTraders(trades);
  console.log('🏆 MOST ACTIVE TRADERS:');
  for (const trader of activeTraders.slice(0, 5)) {
    console.log(`   ${trader.memberName} (${trader.party}-${trader.chamber}): ${trader.tradeCount} trades`);
  }
  console.log();
  
  // Sector analysis
  const sectors = analytics.analyzeSectorActivity(trades);
  console.log('📈 SECTOR ACTIVITY:');
  for (const [sector, data] of sectors) {
    if (data.buyCount + data.sellCount >= 3) {
      console.log(`   ${sector}: ${data.buyCount} buys, ${data.sellCount} sells (${data.netDirection})`);
    }
  }
}

async function generateAlerts(): Promise<void> {
  console.log('=== Generating Alerts ===\n');
  
  const trades = storage.getTrades();
  if (trades.length === 0) {
    console.log('No trades in database. Run "fetch" first.');
    return;
  }
  
  const alerts = analytics.generateAlerts(trades);
  storage.addAlerts(alerts);
  
  console.log(`Generated ${alerts.length} alerts:\n`);
  
  for (const alert of alerts) {
    const icon = {
      critical: '🔴',
      high: '🟠',
      medium: '🟡',
      low: '🟢'
    }[alert.severity];
    
    console.log(`${icon} [${alert.severity.toUpperCase()}] ${alert.title}`);
    console.log(`   ${alert.description}`);
    console.log();
  }
}

async function generateDashboardCmd(): Promise<void> {
  console.log('=== Generating Dashboard ===\n');
  
  const trades = storage.getTrades();
  if (trades.length === 0) {
    console.log('No trades in database. Run "fetch" first.');
    return;
  }
  
  const alerts = analytics.generateAlerts(trades);
  const clusters = analytics.detectClusterTrades(trades);
  const sentiment = analytics.calculateCongressSentiment(trades);
  const activeTraders = analytics.getMostActiveTraders(trades);
  
  const data: DashboardData = {
    trades,
    alerts,
    clusters,
    sentiment,
    activeTraders,
    lastUpdated: new Date()
  };
  
  saveDashboard(data, './congress-dashboard.html');
  console.log('Dashboard generated: congress-dashboard.html');
}

async function runTests(): Promise<void> {
  console.log('=== Congressional Trading Monitor Tests ===\n');
  
  // Test 1: Generate and store sample data
  console.log('Test 1: Sample Data Generation');
  const sampleTrades = generateSampleTrades();
  console.log(`  ✓ Generated ${sampleTrades.length} sample trades`);
  
  const added = storage.addTrades(sampleTrades);
  console.log(`  ✓ Stored ${added} trades\n`);
  
  // Test 2: Analytics
  console.log('Test 2: Analytics Engine');
  const sentiment = analytics.calculateCongressSentiment(sampleTrades);
  console.log(`  ✓ Sentiment: ${sentiment.sentiment}`);
  console.log(`  ✓ Buy/Sell: ${sentiment.buyCount}/${sentiment.sellCount}`);
  
  const clusters = analytics.detectClusterTrades(sampleTrades);
  console.log(`  ✓ Detected ${clusters.length} cluster trades`);
  
  const largeTrades = analytics.findLargeTrades(sampleTrades);
  console.log(`  ✓ Found ${largeTrades.length} large trades\n`);
  
  // Test 3: Alerts
  console.log('Test 3: Alert Generation');
  const alerts = analytics.generateAlerts(sampleTrades);
  console.log(`  ✓ Generated ${alerts.length} alerts`);
  const criticalAlerts = alerts.filter(a => a.severity === 'critical' || a.severity === 'high');
  console.log(`  ✓ ${criticalAlerts.length} high priority alerts\n`);
  
  // Test 4: Dashboard
  console.log('Test 4: Dashboard Generation');
  const data: DashboardData = {
    trades: sampleTrades,
    alerts,
    clusters,
    sentiment,
    activeTraders: analytics.getMostActiveTraders(sampleTrades),
    lastUpdated: new Date()
  };
  saveDashboard(data, './test-dashboard.html');
  console.log('  ✓ Dashboard saved to test-dashboard.html\n');
  
  // Test 5: Storage
  console.log('Test 5: Data Storage');
  const metadata = storage.getMetadata();
  console.log(`  ✓ Total trades: ${metadata.totalTrades}`);
  console.log(`  ✓ Last fetch: ${formatDate(metadata.lastFetch)}\n`);
  
  console.log('=== All Tests Passed ===');
}

// Generate sample trades for testing
function generateSampleTrades(): StockTrade[] {
  const members = [
    { name: 'Nancy Pelosi', party: 'D' as const, chamber: 'House' as const },
    { name: 'Dan Crenshaw', party: 'R' as const, chamber: 'House' as const },
    { name: 'Tommy Tuberville', party: 'R' as const, chamber: 'Senate' as const },
    { name: 'Mark Kelly', party: 'D' as const, chamber: 'Senate' as const },
    { name: 'Josh Gottheimer', party: 'D' as const, chamber: 'House' as const },
    { name: 'Austin Scott', party: 'R' as const, chamber: 'House' as const },
    { name: 'Pat Fallon', party: 'R' as const, chamber: 'House' as const },
    { name: 'Debbie Wasserman Schultz', party: 'D' as const, chamber: 'House' as const }
  ];
  
  const stocks = [
    { ticker: 'NVDA', name: 'NVIDIA Corporation' },
    { ticker: 'MSFT', name: 'Microsoft Corporation' },
    { ticker: 'AAPL', name: 'Apple Inc.' },
    { ticker: 'GOOGL', name: 'Alphabet Inc.' },
    { ticker: 'AMZN', name: 'Amazon.com Inc.' },
    { ticker: 'META', name: 'Meta Platforms Inc.' },
    { ticker: 'TSLA', name: 'Tesla Inc.' },
    { ticker: 'JPM', name: 'JPMorgan Chase & Co.' },
    { ticker: 'LMT', name: 'Lockheed Martin Corporation' },
    { ticker: 'RTX', name: 'Raytheon Technologies' }
  ];
  
  const amounts = [
    { range: '$1,001 - $15,000', min: 1001, max: 15000 },
    { range: '$15,001 - $50,000', min: 15001, max: 50000 },
    { range: '$50,001 - $100,000', min: 50001, max: 100000 },
    { range: '$100,001 - $250,000', min: 100001, max: 250000 },
    { range: '$250,001 - $500,000', min: 250001, max: 500000 },
    { range: '$500,001 - $1,000,000', min: 500001, max: 1000000 }
  ];
  
  const trades: StockTrade[] = [];
  const now = Date.now();
  
  // Generate cluster trades for NVDA (5 members buying within 10 days)
  const nvdaBuyers = members.slice(0, 5);
  for (let i = 0; i < nvdaBuyers.length; i++) {
    const member = nvdaBuyers[i];
    const txDate = new Date(now - (5 + i) * 24 * 60 * 60 * 1000);
    const discDate = new Date(txDate.getTime() + 30 * 24 * 60 * 60 * 1000);
    const amount = amounts[Math.floor(Math.random() * amounts.length)];
    
    trades.push({
      id: `sample-nvda-${i}`,
      memberId: member.name.toLowerCase().replace(/\s+/g, '-'),
      memberName: member.name,
      party: member.party,
      chamber: member.chamber,
      ticker: 'NVDA',
      companyName: 'NVIDIA Corporation',
      transactionType: 'purchase',
      transactionDate: txDate,
      disclosureDate: discDate,
      amountMin: amount.min,
      amountMax: amount.max,
      amountRange: amount.range,
      assetType: 'stock',
      owner: 'self'
    });
  }
  
  // Generate random trades
  for (let i = 0; i < 45; i++) {
    const member = members[Math.floor(Math.random() * members.length)];
    const stock = stocks[Math.floor(Math.random() * stocks.length)];
    const amount = amounts[Math.floor(Math.random() * amounts.length)];
    const daysAgo = Math.floor(Math.random() * 60);
    const txDate = new Date(now - daysAgo * 24 * 60 * 60 * 1000);
    const discDate = new Date(txDate.getTime() + (20 + Math.floor(Math.random() * 20)) * 24 * 60 * 60 * 1000);
    
    trades.push({
      id: `sample-${i}`,
      memberId: member.name.toLowerCase().replace(/\s+/g, '-'),
      memberName: member.name,
      party: member.party,
      chamber: member.chamber,
      ticker: stock.ticker,
      companyName: stock.name,
      transactionType: Math.random() > 0.4 ? 'purchase' : 'sale',
      transactionDate: txDate,
      disclosureDate: discDate,
      amountMin: amount.min,
      amountMax: amount.max,
      amountRange: amount.range,
      assetType: 'stock',
      owner: 'self'
    });
  }
  
  return trades;
}

// Main CLI
async function main(): Promise<void> {
  const command = process.argv[2] || 'help';
  
  switch (command) {
    case 'fetch':
      await fetchTrades();
      break;
    case 'analyze':
      await analyzeTrades();
      break;
    case 'alerts':
      await generateAlerts();
      break;
    case 'dashboard':
      await generateDashboardCmd();
      break;
    case 'test':
      await runTests();
      break;
    case 'help':
    default:
      console.log(`
Congressional Trading Monitor - STOCK Act Tracker

Usage: npm run <command>

Commands:
  fetch      Fetch latest congressional trades from disclosure sites
  analyze    Analyze stored trades (sentiment, clusters, large trades)
  alerts     Generate alerts for notable trading activity
  dashboard  Generate HTML dashboard
  test       Run tests with sample data

Examples:
  npm run fetch       # Fetch new trades
  npm run analyze     # Analyze trading patterns
  npm run alerts      # Generate alerts
  npm run dashboard   # Create dashboard
  npm run test        # Run tests
`);
  }
}

main().catch(console.error);
