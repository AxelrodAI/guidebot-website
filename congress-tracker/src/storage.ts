/**
 * Data Storage for Congress Tracker
 * Persists trades, alerts, and analytics to disk
 */

import * as fs from 'fs';
import * as path from 'path';
import { StockTrade, TradeAlert, DataStore, CongressMember } from './types.js';

const DATA_DIR = process.env.CONGRESS_TRACKER_DATA || './data';

export class CongressDataStorage {
  private dataDir: string;
  private store: DataStore;
  
  constructor(dataDir: string = DATA_DIR) {
    this.dataDir = dataDir;
    this.ensureDataDir();
    this.store = this.loadStore();
  }
  
  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }
  
  private getStorePath(): string {
    return path.join(this.dataDir, 'congress-data.json');
  }
  
  private loadStore(): DataStore {
    const storePath = this.getStorePath();
    
    if (fs.existsSync(storePath)) {
      try {
        const data = JSON.parse(fs.readFileSync(storePath, 'utf-8'));
        // Convert date strings back to Date objects
        return {
          ...data,
          trades: data.trades.map((t: any) => ({
            ...t,
            transactionDate: new Date(t.transactionDate),
            disclosureDate: new Date(t.disclosureDate)
          })),
          alerts: data.alerts.map((a: any) => ({
            ...a,
            timestamp: new Date(a.timestamp),
            trades: a.trades.map((t: any) => ({
              ...t,
              transactionDate: new Date(t.transactionDate),
              disclosureDate: new Date(t.disclosureDate)
            }))
          })),
          lastFetch: new Date(data.lastFetch),
          metadata: {
            ...data.metadata,
            dateRange: {
              start: new Date(data.metadata.dateRange.start),
              end: new Date(data.metadata.dateRange.end)
            }
          }
        };
      } catch (error) {
        console.warn('Failed to load existing data store, creating new one');
      }
    }
    
    return this.createEmptyStore();
  }
  
  private createEmptyStore(): DataStore {
    return {
      trades: [],
      members: [],
      alerts: [],
      lastFetch: new Date(0),
      metadata: {
        totalTrades: 0,
        dateRange: {
          start: new Date(),
          end: new Date()
        }
      }
    };
  }
  
  private saveStore(): void {
    const storePath = this.getStorePath();
    fs.writeFileSync(storePath, JSON.stringify(this.store, null, 2));
  }
  
  /**
   * Add new trades (deduplicates automatically)
   */
  addTrades(trades: StockTrade[]): number {
    const existingIds = new Set(this.store.trades.map(t => t.id));
    let added = 0;
    
    for (const trade of trades) {
      if (!existingIds.has(trade.id)) {
        this.store.trades.push(trade);
        existingIds.add(trade.id);
        added++;
      }
    }
    
    // Update metadata
    this.store.metadata.totalTrades = this.store.trades.length;
    if (this.store.trades.length > 0) {
      const dates = this.store.trades.map(t => t.transactionDate.getTime());
      this.store.metadata.dateRange = {
        start: new Date(Math.min(...dates)),
        end: new Date(Math.max(...dates))
      };
    }
    
    this.store.lastFetch = new Date();
    this.saveStore();
    
    return added;
  }
  
  /**
   * Get all trades
   */
  getTrades(): StockTrade[] {
    return [...this.store.trades];
  }
  
  /**
   * Get trades within date range
   */
  getTradesInRange(startDate: Date, endDate: Date): StockTrade[] {
    return this.store.trades.filter(
      t => t.transactionDate >= startDate && t.transactionDate <= endDate
    );
  }
  
  /**
   * Get trades for specific ticker
   */
  getTradesForTicker(ticker: string): StockTrade[] {
    return this.store.trades.filter(
      t => t.ticker.toUpperCase() === ticker.toUpperCase()
    );
  }
  
  /**
   * Get trades for specific member
   */
  getTradesForMember(memberName: string): StockTrade[] {
    const lower = memberName.toLowerCase();
    return this.store.trades.filter(
      t => t.memberName.toLowerCase().includes(lower)
    );
  }
  
  /**
   * Add alerts
   */
  addAlerts(alerts: TradeAlert[]): void {
    // Keep only recent alerts (last 30 days)
    const cutoff = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    this.store.alerts = this.store.alerts.filter(a => a.timestamp >= cutoff);
    
    // Add new alerts
    const existingIds = new Set(this.store.alerts.map(a => a.id));
    for (const alert of alerts) {
      if (!existingIds.has(alert.id)) {
        this.store.alerts.push(alert);
      }
    }
    
    this.saveStore();
  }
  
  /**
   * Get alerts
   */
  getAlerts(limit?: number): TradeAlert[] {
    const sorted = [...this.store.alerts].sort(
      (a, b) => b.timestamp.getTime() - a.timestamp.getTime()
    );
    return limit ? sorted.slice(0, limit) : sorted;
  }
  
  /**
   * Update members
   */
  updateMembers(members: CongressMember[]): void {
    this.store.members = members;
    this.saveStore();
  }
  
  /**
   * Get members
   */
  getMembers(): CongressMember[] {
    return [...this.store.members];
  }
  
  /**
   * Get store metadata
   */
  getMetadata(): DataStore['metadata'] & { lastFetch: Date } {
    return {
      ...this.store.metadata,
      lastFetch: this.store.lastFetch
    };
  }
  
  /**
   * Export data to CSV
   */
  exportToCSV(filepath: string): void {
    const headers = [
      'Transaction Date',
      'Disclosure Date',
      'Member',
      'Party',
      'Chamber',
      'Ticker',
      'Company',
      'Type',
      'Amount Range',
      'Asset Type',
      'Owner'
    ];
    
    const rows = this.store.trades.map(t => [
      t.transactionDate.toISOString().split('T')[0],
      t.disclosureDate.toISOString().split('T')[0],
      t.memberName,
      t.party,
      t.chamber,
      t.ticker,
      t.companyName,
      t.transactionType,
      t.amountRange,
      t.assetType,
      t.owner
    ]);
    
    const csv = [
      headers.join(','),
      ...rows.map(r => r.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    fs.writeFileSync(filepath, csv);
  }
  
  /**
   * Clear all data
   */
  clearData(): void {
    this.store = this.createEmptyStore();
    this.saveStore();
  }
}

export const storage = new CongressDataStorage();
