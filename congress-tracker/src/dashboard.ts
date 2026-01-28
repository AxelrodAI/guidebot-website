/**
 * Dashboard Generator for Congress Tracker
 * Generates HTML dashboard with trade data and analytics
 */

import * as fs from 'fs';
import { StockTrade, TradeAlert, ClusterTradeEvent, MemberPortfolio } from './types.js';
import { formatCurrency, formatDate, getTickerSector } from './utils.js';
import { CongressTradeAnalytics } from './analytics.js';

export interface DashboardData {
  trades: StockTrade[];
  alerts: TradeAlert[];
  clusters: ClusterTradeEvent[];
  sentiment: {
    sentiment: 'bullish' | 'bearish' | 'neutral';
    buyCount: number;
    sellCount: number;
    topBuys: string[];
    topSells: string[];
  };
  activeTraders: {
    memberName: string;
    party: 'D' | 'R' | 'I';
    chamber: 'House' | 'Senate';
    tradeCount: number;
    totalValueMin: number;
    totalValueMax: number;
  }[];
  lastUpdated: Date;
}

export function generateDashboard(data: DashboardData): string {
  const { trades, alerts, clusters, sentiment, activeTraders, lastUpdated } = data;
  
  // Recent trades (last 20)
  const recentTrades = trades.slice(0, 20);
  
  // Party breakdown
  const dems = trades.filter(t => t.party === 'D');
  const reps = trades.filter(t => t.party === 'R');
  
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="300">
  <title>Congressional Trading Monitor</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0a0a0f;
      color: #e0e0e0;
      line-height: 1.6;
    }
    .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px 0;
      border-bottom: 1px solid #2a2a35;
      margin-bottom: 20px;
    }
    h1 { color: #fff; font-size: 1.8rem; }
    .subtitle { color: #888; font-size: 0.9rem; }
    .last-updated { color: #666; font-size: 0.85rem; }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
    .card {
      background: #12121a;
      border-radius: 12px;
      padding: 20px;
      border: 1px solid #2a2a35;
    }
    .card-title {
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #888;
      margin-bottom: 10px;
    }
    .card-value {
      font-size: 2rem;
      font-weight: 600;
      color: #fff;
    }
    .card-subtitle { font-size: 0.85rem; color: #666; margin-top: 5px; }
    
    .sentiment-bullish { color: #00c853; }
    .sentiment-bearish { color: #ff5252; }
    .sentiment-neutral { color: #ffc107; }
    
    .party-d { color: #4dabf7; }
    .party-r { color: #ff6b6b; }
    .party-i { color: #a9e34b; }
    
    .alert-card {
      background: linear-gradient(135deg, #1a1a25 0%, #12121a 100%);
      border-left: 4px solid;
      margin-bottom: 12px;
    }
    .alert-critical { border-left-color: #ff5252; }
    .alert-high { border-left-color: #ffc107; }
    .alert-medium { border-left-color: #4dabf7; }
    .alert-low { border-left-color: #666; }
    .alert-title { font-weight: 600; color: #fff; margin-bottom: 5px; }
    .alert-desc { font-size: 0.9rem; color: #aaa; }
    
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2a2a35; }
    th { color: #888; font-weight: 500; font-size: 0.85rem; text-transform: uppercase; }
    tr:hover { background: rgba(255,255,255,0.02); }
    
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 500;
    }
    .badge-buy { background: rgba(0,200,83,0.2); color: #00c853; }
    .badge-sell { background: rgba(255,82,82,0.2); color: #ff5252; }
    
    .ticker { font-family: 'Monaco', 'Consolas', monospace; font-weight: 600; }
    .amount { color: #888; font-size: 0.9rem; }
    
    .cluster-card {
      background: linear-gradient(135deg, #1a1a25 0%, #12121a 100%);
      border: 1px solid #2a2a35;
      border-radius: 8px;
      padding: 15px;
      margin-bottom: 12px;
    }
    .cluster-header { display: flex; justify-content: space-between; align-items: center; }
    .cluster-ticker { font-size: 1.2rem; font-weight: 600; }
    .cluster-count { color: #ffc107; font-weight: 500; }
    .cluster-members { font-size: 0.85rem; color: #888; margin-top: 8px; }
    
    .section { margin-bottom: 30px; }
    .section-title { font-size: 1.2rem; font-weight: 600; color: #fff; margin-bottom: 15px; }
    
    .top-tickers { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
    .top-ticker {
      background: #1a1a25;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.85rem;
    }
    
    footer {
      text-align: center;
      padding: 20px;
      color: #666;
      font-size: 0.85rem;
      border-top: 1px solid #2a2a35;
      margin-top: 20px;
    }
    
    @media (max-width: 768px) {
      .grid { grid-template-columns: 1fr; }
      table { font-size: 0.85rem; }
      th, td { padding: 8px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>📊 Congressional Trading Monitor</h1>
        <div class="subtitle">STOCK Act Disclosure Tracker</div>
      </div>
      <div class="last-updated">
        Last updated: ${formatDate(lastUpdated)}<br>
        ${trades.length} trades tracked
      </div>
    </header>
    
    <!-- Summary Cards -->
    <div class="grid">
      <div class="card">
        <div class="card-title">Congress Sentiment</div>
        <div class="card-value sentiment-${sentiment.sentiment}">${sentiment.sentiment.toUpperCase()}</div>
        <div class="card-subtitle">${sentiment.buyCount} buys / ${sentiment.sellCount} sells</div>
      </div>
      
      <div class="card">
        <div class="card-title">Active Alerts</div>
        <div class="card-value">${alerts.filter(a => a.severity === 'critical' || a.severity === 'high').length}</div>
        <div class="card-subtitle">${alerts.filter(a => a.severity === 'critical').length} critical, ${alerts.filter(a => a.severity === 'high').length} high priority</div>
      </div>
      
      <div class="card">
        <div class="card-title">Cluster Trades</div>
        <div class="card-value">${clusters.length}</div>
        <div class="card-subtitle">Multiple members trading same stock</div>
      </div>
      
      <div class="card">
        <div class="card-title">Party Breakdown</div>
        <div class="card-value">
          <span class="party-d">${dems.length}D</span> / <span class="party-r">${reps.length}R</span>
        </div>
        <div class="card-subtitle">Democratic vs Republican trades</div>
      </div>
    </div>
    
    <!-- Top Traded -->
    <div class="card" style="margin-bottom: 20px;">
      <div class="card-title">Most Bought by Congress</div>
      <div class="top-tickers">
        ${sentiment.topBuys.map(t => `<span class="top-ticker badge-buy">${t}</span>`).join('')}
      </div>
      <div class="card-title" style="margin-top: 15px;">Most Sold by Congress</div>
      <div class="top-tickers">
        ${sentiment.topSells.map(t => `<span class="top-ticker badge-sell">${t}</span>`).join('')}
      </div>
    </div>
    
    <!-- Alerts -->
    <div class="section">
      <div class="section-title">🚨 Recent Alerts</div>
      ${alerts.slice(0, 5).map(alert => `
        <div class="card alert-card alert-${alert.severity}">
          <div class="alert-title">${alert.title}</div>
          <div class="alert-desc">${alert.description}</div>
        </div>
      `).join('')}
    </div>
    
    <!-- Cluster Trades -->
    ${clusters.length > 0 ? `
    <div class="section">
      <div class="section-title">👥 Cluster Trades (Multiple Members)</div>
      ${clusters.slice(0, 5).map(cluster => {
        const members = [...new Set(cluster.trades.map(t => `${t.memberName} (${t.party})`))];
        return `
          <div class="cluster-card">
            <div class="cluster-header">
              <div>
                <span class="cluster-ticker ticker">${cluster.ticker}</span>
                <span class="amount">${cluster.companyName}</span>
              </div>
              <div class="cluster-count">${cluster.memberCount} members ${cluster.direction === 'buy' ? 'buying' : cluster.direction === 'sell' ? 'selling' : 'trading'}</div>
            </div>
            <div class="cluster-members">${members.slice(0, 5).join(', ')}${members.length > 5 ? ` +${members.length - 5} more` : ''}</div>
            <div class="amount">${formatCurrency(cluster.totalAmountMin)} - ${formatCurrency(cluster.totalAmountMax)} total</div>
          </div>
        `;
      }).join('')}
    </div>
    ` : ''}
    
    <!-- Most Active Traders -->
    <div class="section">
      <div class="section-title">🏆 Most Active Traders</div>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Member</th>
              <th>Party</th>
              <th>Chamber</th>
              <th>Trades</th>
              <th>Total Value</th>
            </tr>
          </thead>
          <tbody>
            ${activeTraders.slice(0, 10).map(trader => `
              <tr>
                <td>${trader.memberName}</td>
                <td><span class="party-${trader.party.toLowerCase()}">${trader.party}</span></td>
                <td>${trader.chamber}</td>
                <td>${trader.tradeCount}</td>
                <td class="amount">${formatCurrency(trader.totalValueMin)} - ${formatCurrency(trader.totalValueMax)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- Recent Trades -->
    <div class="section">
      <div class="section-title">📋 Recent Trades</div>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Member</th>
              <th>Ticker</th>
              <th>Type</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            ${recentTrades.map(trade => `
              <tr>
                <td>${formatDate(trade.transactionDate)}</td>
                <td>
                  ${trade.memberName}
                  <span class="party-${trade.party.toLowerCase()}">(${trade.party})</span>
                </td>
                <td><span class="ticker">${trade.ticker}</span></td>
                <td><span class="badge badge-${trade.transactionType === 'purchase' ? 'buy' : 'sell'}">${trade.transactionType === 'purchase' ? 'BUY' : 'SELL'}</span></td>
                <td class="amount">${trade.amountRange}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
    
    <footer>
      Congressional Trading Monitor • STOCK Act Disclosure Tracker<br>
      Data sourced from public congressional financial disclosures
    </footer>
  </div>
</body>
</html>`;

  return html;
}

export function saveDashboard(data: DashboardData, filepath: string): void {
  const html = generateDashboard(data);
  fs.writeFileSync(filepath, html);
  console.log(`Dashboard saved to ${filepath}`);
}
