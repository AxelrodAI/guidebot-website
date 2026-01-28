/**
 * Centralized Ticker Data Service
 * Single source of truth for all ticker data across guidebot tools
 * Uses Yahoo Finance API for real market data
 */

const TickerService = {
    // Cache configuration
    cache: new Map(),
    cacheTimeout: 60000, // 1 minute cache
    
    // Yahoo Finance base URLs
    QUOTE_URL: 'https://query1.finance.yahoo.com/v8/finance/chart/',
    SEARCH_URL: 'https://query1.finance.yahoo.com/v1/finance/search',
    QUOTE_SUMMARY_URL: 'https://query1.finance.yahoo.com/v10/finance/quoteSummary/',
    
    /**
     * Get cached data or fetch new
     */
    _getCached(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            console.log(`[TickerService] Cache hit: ${key}`);
            return cached.data;
        }
        return null;
    },
    
    /**
     * Store data in cache
     */
    _setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    },
    
    /**
     * Clear expired cache entries
     */
    clearExpiredCache() {
        const now = Date.now();
        for (const [key, value] of this.cache.entries()) {
            if (now - value.timestamp > this.cacheTimeout) {
                this.cache.delete(key);
            }
        }
    },
    
    /**
     * Get real-time quote for a ticker
     * @param {string} ticker - Stock symbol (e.g., 'AAPL')
     * @returns {Promise<Object>} Quote data
     */
    async getQuote(ticker) {
        const cacheKey = `quote_${ticker.toUpperCase()}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;
        
        try {
            const url = `${this.QUOTE_URL}${ticker.toUpperCase()}?interval=1d&range=1d`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to fetch quote for ${ticker}`);
            }
            
            const data = await response.json();
            
            if (data.chart?.error) {
                throw new Error(data.chart.error.description || 'Invalid ticker');
            }
            
            const result = data.chart?.result?.[0];
            if (!result) {
                throw new Error(`No data found for ${ticker}`);
            }
            
            const meta = result.meta;
            const quote = result.indicators?.quote?.[0] || {};
            
            const quoteData = {
                ticker: meta.symbol,
                name: meta.shortName || meta.longName || ticker,
                exchange: meta.exchangeName,
                currency: meta.currency,
                price: meta.regularMarketPrice,
                previousClose: meta.previousClose,
                change: meta.regularMarketPrice - meta.previousClose,
                changePercent: ((meta.regularMarketPrice - meta.previousClose) / meta.previousClose * 100),
                open: quote.open?.[0],
                high: quote.high?.[0],
                low: quote.low?.[0],
                volume: quote.volume?.[0],
                marketCap: meta.marketCap,
                fiftyTwoWeekHigh: meta.fiftyTwoWeekHigh,
                fiftyTwoWeekLow: meta.fiftyTwoWeekLow,
                timestamp: Date.now(),
                raw: meta
            };
            
            this._setCache(cacheKey, quoteData);
            console.log(`[TickerService] Fetched quote: ${ticker}`, quoteData);
            return quoteData;
            
        } catch (error) {
            console.error(`[TickerService] Error fetching quote for ${ticker}:`, error);
            throw error;
        }
    },
    
    /**
     * Get historical price data
     * @param {string} ticker - Stock symbol
     * @param {string} period - Time period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'
     * @param {string} interval - Data interval: '1m', '5m', '15m', '1h', '1d', '1wk', '1mo'
     * @returns {Promise<Object>} Historical data
     */
    async getHistorical(ticker, period = '1mo', interval = '1d') {
        const cacheKey = `historical_${ticker.toUpperCase()}_${period}_${interval}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;
        
        try {
            const url = `${this.QUOTE_URL}${ticker.toUpperCase()}?interval=${interval}&range=${period}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to fetch historical data`);
            }
            
            const data = await response.json();
            
            if (data.chart?.error) {
                throw new Error(data.chart.error.description || 'Failed to fetch historical data');
            }
            
            const result = data.chart?.result?.[0];
            if (!result) {
                throw new Error(`No historical data found for ${ticker}`);
            }
            
            const timestamps = result.timestamp || [];
            const quote = result.indicators?.quote?.[0] || {};
            const adjClose = result.indicators?.adjclose?.[0]?.adjclose || quote.close;
            
            const historicalData = {
                ticker: result.meta.symbol,
                period,
                interval,
                currency: result.meta.currency,
                dataPoints: timestamps.map((ts, i) => ({
                    date: new Date(ts * 1000).toISOString(),
                    timestamp: ts,
                    open: quote.open?.[i],
                    high: quote.high?.[i],
                    low: quote.low?.[i],
                    close: quote.close?.[i],
                    adjClose: adjClose?.[i],
                    volume: quote.volume?.[i]
                })).filter(dp => dp.close !== null),
                timestamp: Date.now()
            };
            
            this._setCache(cacheKey, historicalData);
            console.log(`[TickerService] Fetched historical: ${ticker} (${period})`, historicalData.dataPoints.length, 'points');
            return historicalData;
            
        } catch (error) {
            console.error(`[TickerService] Error fetching historical for ${ticker}:`, error);
            throw error;
        }
    },
    
    /**
     * Get fundamental data for a ticker
     * @param {string} ticker - Stock symbol
     * @returns {Promise<Object>} Fundamental data
     */
    async getFundamentals(ticker) {
        const cacheKey = `fundamentals_${ticker.toUpperCase()}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;
        
        try {
            // Get quote summary with key stats
            const modules = 'defaultKeyStatistics,financialData,summaryDetail,price';
            const url = `${this.QUOTE_SUMMARY_URL}${ticker.toUpperCase()}?modules=${modules}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to fetch fundamentals`);
            }
            
            const data = await response.json();
            
            if (data.quoteSummary?.error) {
                throw new Error(data.quoteSummary.error.description || 'Failed to fetch fundamentals');
            }
            
            const result = data.quoteSummary?.result?.[0];
            if (!result) {
                throw new Error(`No fundamental data found for ${ticker}`);
            }
            
            const stats = result.defaultKeyStatistics || {};
            const financial = result.financialData || {};
            const summary = result.summaryDetail || {};
            const price = result.price || {};
            
            const fundamentals = {
                ticker: ticker.toUpperCase(),
                name: price.shortName || price.longName || ticker,
                sector: price.sector,
                industry: price.industry,
                
                // Valuation
                marketCap: price.marketCap?.raw,
                enterpriseValue: stats.enterpriseValue?.raw,
                trailingPE: summary.trailingPE?.raw,
                forwardPE: summary.forwardPE?.raw,
                priceToBook: stats.priceToBook?.raw,
                priceToSales: stats.priceToSalesTrailing12Months?.raw,
                
                // Profitability
                profitMargins: financial.profitMargins?.raw,
                operatingMargins: financial.operatingMargins?.raw,
                returnOnEquity: financial.returnOnEquity?.raw,
                returnOnAssets: financial.returnOnAssets?.raw,
                
                // Growth & Revenue
                revenueGrowth: financial.revenueGrowth?.raw,
                earningsGrowth: financial.earningsGrowth?.raw,
                totalRevenue: financial.totalRevenue?.raw,
                
                // Dividends
                dividendYield: summary.dividendYield?.raw,
                dividendRate: summary.dividendRate?.raw,
                payoutRatio: summary.payoutRatio?.raw,
                
                // Short Interest (key for short-interest-tracker!)
                sharesShort: stats.sharesShort?.raw,
                sharesShortPriorMonth: stats.sharesShortPriorMonth?.raw,
                shortRatio: stats.shortRatio?.raw, // Days to cover
                shortPercentOfFloat: stats.shortPercentOfFloat?.raw,
                sharesOutstanding: stats.sharesOutstanding?.raw,
                floatShares: stats.floatShares?.raw,
                
                // Other
                beta: stats.beta?.raw,
                fiftyTwoWeekChange: stats.fiftyTwoWeekChange?.raw,
                
                timestamp: Date.now()
            };
            
            this._setCache(cacheKey, fundamentals);
            console.log(`[TickerService] Fetched fundamentals: ${ticker}`, fundamentals);
            return fundamentals;
            
        } catch (error) {
            console.error(`[TickerService] Error fetching fundamentals for ${ticker}:`, error);
            throw error;
        }
    },
    
    /**
     * Search for tickers (autocomplete)
     * @param {string} query - Search query
     * @returns {Promise<Array>} Matching tickers
     */
    async searchTickers(query) {
        if (!query || query.length < 1) return [];
        
        const cacheKey = `search_${query.toLowerCase()}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;
        
        try {
            const url = `${this.SEARCH_URL}?q=${encodeURIComponent(query)}&quotesCount=10&newsCount=0`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Search failed`);
            }
            
            const data = await response.json();
            
            const results = (data.quotes || [])
                .filter(q => q.quoteType === 'EQUITY' || q.quoteType === 'ETF')
                .map(q => ({
                    ticker: q.symbol,
                    name: q.shortname || q.longname || q.symbol,
                    exchange: q.exchange,
                    type: q.quoteType,
                    score: q.score
                }));
            
            this._setCache(cacheKey, results);
            console.log(`[TickerService] Search "${query}":`, results.length, 'results');
            return results;
            
        } catch (error) {
            console.error(`[TickerService] Search error:`, error);
            return [];
        }
    },
    
    /**
     * Get short interest data specifically
     * Combines fundamentals with calculated metrics
     * @param {string} ticker - Stock symbol
     * @returns {Promise<Object>} Short interest data
     */
    async getShortInterest(ticker) {
        try {
            const [quote, fundamentals] = await Promise.all([
                this.getQuote(ticker),
                this.getFundamentals(ticker)
            ]);
            
            // Calculate SI % of float if not provided
            let siPercent = fundamentals.shortPercentOfFloat;
            if (!siPercent && fundamentals.sharesShort && fundamentals.floatShares) {
                siPercent = fundamentals.sharesShort / fundamentals.floatShares;
            }
            
            // Calculate week-over-week change
            let siChange = 0;
            if (fundamentals.sharesShort && fundamentals.sharesShortPriorMonth) {
                siChange = ((fundamentals.sharesShort - fundamentals.sharesShortPriorMonth) / fundamentals.sharesShortPriorMonth) * 100;
            }
            
            return {
                ticker: ticker.toUpperCase(),
                company: quote.name,
                price: quote.price,
                priceChange: quote.changePercent,
                
                // Short Interest metrics
                siPercent: siPercent ? siPercent * 100 : null,
                siShares: fundamentals.sharesShort,
                siSharesPrior: fundamentals.sharesShortPriorMonth,
                siChange: siChange,
                daysTocover: fundamentals.shortRatio,
                
                // Float data
                floatShares: fundamentals.floatShares,
                sharesOutstanding: fundamentals.sharesOutstanding,
                
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error(`[TickerService] Error getting short interest for ${ticker}:`, error);
            throw error;
        }
    },
    
    /**
     * Batch fetch quotes for multiple tickers
     * @param {Array<string>} tickers - Array of ticker symbols
     * @returns {Promise<Object>} Map of ticker to quote data
     */
    async getBatchQuotes(tickers) {
        const results = {};
        const fetchPromises = tickers.map(async (ticker) => {
            try {
                results[ticker] = await this.getQuote(ticker);
            } catch (error) {
                results[ticker] = { error: error.message, ticker };
            }
        });
        
        await Promise.all(fetchPromises);
        return results;
    },
    
    /**
     * Format number for display
     */
    formatNumber(num, decimals = 2) {
        if (num === null || num === undefined) return 'N/A';
        if (num >= 1e12) return (num / 1e12).toFixed(decimals) + 'T';
        if (num >= 1e9) return (num / 1e9).toFixed(decimals) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(decimals) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(decimals) + 'K';
        return num.toFixed(decimals);
    },
    
    /**
     * Format percentage for display
     */
    formatPercent(num, decimals = 2) {
        if (num === null || num === undefined) return 'N/A';
        return num.toFixed(decimals) + '%';
    }
};

// Export for both module and browser use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TickerService;
}
