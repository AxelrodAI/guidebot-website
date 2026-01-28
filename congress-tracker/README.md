# Congressional Trading Monitor

Track stock trades disclosed by Congress members under the STOCK Act (Stop Trading on Congressional Knowledge Act).

## Features

- **Trade Fetching**: Fetch periodic transaction reports from House and Senate disclosure sites
- **Cluster Detection**: Alert when multiple Congress members trade the same stock within a window
- **Large Trade Alerts**: Flag trades above configurable thresholds
- **Performance Tracking**: Track Congress portfolios vs market benchmarks
- **Sentiment Analysis**: Overall congressional buying/selling sentiment
- **Dashboard**: Auto-generated HTML dashboard with real-time data

## Installation

```bash
cd congress-tracker
npm install
```

## Usage

### CLI Commands

```bash
# Fetch latest trades from disclosure sites
npm run fetch

# Analyze stored trades
npm run analyze

# Generate alerts
npm run alerts

# Generate HTML dashboard
npm run dashboard

# Run tests with sample data
npm run test
```

### Programmatic Usage

```typescript
import { fetchAndAnalyze, getTickerAlerts, getMemberProfile } from './src/index.js';

// Fetch and analyze recent trades
const results = await fetchAndAnalyze({
  days: 90,
  generateDashboard: true
});

console.log('Sentiment:', results.sentiment.sentiment);
console.log('Clusters:', results.clusters.length);
console.log('Alerts:', results.alerts.length);

// Check specific ticker
const nvdaInfo = getTickerAlerts('NVDA');
console.log('NVDA trades:', nvdaInfo.trades.length);
console.log('NVDA sentiment:', nvdaInfo.sentiment);

// Check specific member
const pelosi = getMemberProfile('Nancy Pelosi');
console.log('Pelosi trades:', pelosi.tradeCount);
```

## Data Sources

The tracker fetches from multiple sources:

1. **House Clerk Financial Disclosures**: https://disclosures-clerk.house.gov/
2. **Senate Electronic Financial Disclosures**: https://efdsearch.senate.gov/
3. **Capitol Trades API** (aggregated): For easier data access
4. **Quiver Quant** (backup): Alternative data source

## Alert Types

### Large Trade Alert
Triggered when a trade exceeds the configured threshold (default: $100,000).

### Cluster Trade Alert
Triggered when 3+ members trade the same stock within 14 days. This is often a signal of coordinated activity or shared information.

### Sector Activity Alert
Triggered when there's unusual buying or selling activity in a specific sector.

### Late Filing Alert
Flags trades disclosed more than 45 days after the transaction date (STOCK Act violation).

## Configuration

Edit `src/analytics.ts` to adjust thresholds:

```typescript
const DEFAULT_CONFIG = {
  clusterWindowDays: 14,      // Window for cluster detection
  clusterMinMembers: 3,        // Minimum members for cluster alert
  largeTradeThreshold: 100000, // Minimum for "large trade" alert
  lateFilingDays: 45          // STOCK Act deadline
};
```

## Dashboard

The dashboard auto-refreshes every 5 minutes and displays:

- Overall Congress sentiment (bullish/bearish/neutral)
- Active alerts by severity
- Cluster trades (multiple members)
- Most active traders
- Party breakdown (D vs R)
- Recent trades table
- Top bought/sold tickers

## STOCK Act Background

The STOCK Act (2012) requires members of Congress to:
- Report stock trades within 45 days
- Disclose periodic transaction reports
- Avoid trading on non-public information

Trades are reported in ranges, not exact amounts:
- $1,001 - $15,000
- $15,001 - $50,000
- $50,001 - $100,000
- $100,001 - $250,000
- $250,001 - $500,000
- $500,001 - $1,000,000
- $1,000,001 - $5,000,000
- And up...

## Why Track Congressional Trades?

Studies have shown that Congress members' portfolios have historically outperformed the market. Tracking their trades can reveal:

1. **Sector Exposure**: What industries is Congress bullish/bearish on?
2. **Committee Relevance**: Are Finance committee members trading banks?
3. **Timing**: Trades before major legislation or announcements
4. **Clustering**: Multiple members trading the same stock

## Limitations

- Data is delayed (trades disclosed up to 45 days after)
- Amounts are ranges, not exact figures
- Some trades may be made by spouses/dependents
- Not all trades are reported (mutual funds often exempt)

## License

MIT
