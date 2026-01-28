/**
 * Reusable Ticker Input Component with Autocomplete
 * Works with TickerService for search functionality
 * Drop into any tool for consistent ticker search experience
 */

class TickerInput {
    /**
     * Create a ticker input with autocomplete
     * @param {HTMLElement|string} element - Container element or selector
     * @param {Object} options - Configuration options
     * @param {Function} options.onSelect - Callback when ticker is selected: (ticker, data) => {}
     * @param {Function} options.onChange - Callback on input change
     * @param {string} options.placeholder - Input placeholder text
     * @param {boolean} options.showPrice - Show price in dropdown
     * @param {number} options.debounceMs - Debounce delay for search
     */
    constructor(element, options = {}) {
        this.container = typeof element === 'string' 
            ? document.querySelector(element) 
            : element;
            
        if (!this.container) {
            throw new Error('TickerInput: Container element not found');
        }
        
        this.options = {
            onSelect: options.onSelect || (() => {}),
            onChange: options.onChange || (() => {}),
            placeholder: options.placeholder || 'Search ticker (e.g., AAPL)',
            showPrice: options.showPrice !== false,
            debounceMs: options.debounceMs || 200,
            minChars: options.minChars || 1
        };
        
        this.searchTimeout = null;
        this.selectedTicker = null;
        this.results = [];
        this.highlightedIndex = -1;
        
        this._render();
        this._attachEvents();
    }
    
    /**
     * Render the input component
     */
    _render() {
        this.container.innerHTML = `
            <div class="ticker-input-wrapper">
                <input 
                    type="text" 
                    class="ticker-input-field" 
                    placeholder="${this.options.placeholder}"
                    autocomplete="off"
                    spellcheck="false"
                >
                <div class="ticker-input-icon">🔍</div>
                <div class="ticker-input-loading" style="display: none;">
                    <span class="ticker-spinner"></span>
                </div>
                <div class="ticker-input-dropdown" style="display: none;"></div>
            </div>
        `;
        
        this.input = this.container.querySelector('.ticker-input-field');
        this.dropdown = this.container.querySelector('.ticker-input-dropdown');
        this.loadingIcon = this.container.querySelector('.ticker-input-loading');
        this.searchIcon = this.container.querySelector('.ticker-input-icon');
        
        // Inject styles if not already present
        if (!document.getElementById('ticker-input-styles')) {
            const styles = document.createElement('style');
            styles.id = 'ticker-input-styles';
            styles.textContent = `
                .ticker-input-wrapper {
                    position: relative;
                    width: 100%;
                }
                
                .ticker-input-field {
                    width: 100%;
                    padding: 10px 40px 10px 12px;
                    font-size: 14px;
                    border: 1px solid var(--border-color, #30363d);
                    border-radius: 6px;
                    background: var(--bg-tertiary, #21262d);
                    color: var(--text-primary, #f0f6fc);
                    outline: none;
                    transition: border-color 0.2s, box-shadow 0.2s;
                }
                
                .ticker-input-field:focus {
                    border-color: var(--accent-blue, #58a6ff);
                    box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
                }
                
                .ticker-input-field::placeholder {
                    color: var(--text-secondary, #8b949e);
                }
                
                .ticker-input-icon,
                .ticker-input-loading {
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 14px;
                    color: var(--text-secondary, #8b949e);
                }
                
                .ticker-spinner {
                    display: inline-block;
                    width: 14px;
                    height: 14px;
                    border: 2px solid var(--text-secondary, #8b949e);
                    border-top-color: transparent;
                    border-radius: 50%;
                    animation: ticker-spin 0.8s linear infinite;
                }
                
                @keyframes ticker-spin {
                    to { transform: rotate(360deg); }
                }
                
                .ticker-input-dropdown {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    margin-top: 4px;
                    background: var(--bg-secondary, #161b22);
                    border: 1px solid var(--border-color, #30363d);
                    border-radius: 6px;
                    max-height: 300px;
                    overflow-y: auto;
                    z-index: 1000;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
                }
                
                .ticker-input-item {
                    display: flex;
                    align-items: center;
                    padding: 10px 12px;
                    cursor: pointer;
                    border-bottom: 1px solid var(--border-color, #30363d);
                    transition: background 0.15s;
                }
                
                .ticker-input-item:last-child {
                    border-bottom: none;
                }
                
                .ticker-input-item:hover,
                .ticker-input-item.highlighted {
                    background: var(--bg-tertiary, #21262d);
                }
                
                .ticker-input-item-symbol {
                    font-weight: 600;
                    color: var(--accent-blue, #58a6ff);
                    min-width: 70px;
                }
                
                .ticker-input-item-name {
                    flex: 1;
                    color: var(--text-primary, #f0f6fc);
                    font-size: 13px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    margin-right: 8px;
                }
                
                .ticker-input-item-exchange {
                    font-size: 11px;
                    color: var(--text-secondary, #8b949e);
                    padding: 2px 6px;
                    background: var(--bg-tertiary, #21262d);
                    border-radius: 4px;
                }
                
                .ticker-input-no-results {
                    padding: 16px 12px;
                    text-align: center;
                    color: var(--text-secondary, #8b949e);
                    font-size: 13px;
                }
                
                .ticker-input-error {
                    padding: 12px;
                    color: var(--accent-red, #f85149);
                    font-size: 13px;
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    /**
     * Attach event listeners
     */
    _attachEvents() {
        // Input typing
        this.input.addEventListener('input', (e) => {
            this._onInput(e.target.value);
        });
        
        // Keyboard navigation
        this.input.addEventListener('keydown', (e) => {
            this._onKeyDown(e);
        });
        
        // Focus/blur
        this.input.addEventListener('focus', () => {
            if (this.results.length > 0) {
                this._showDropdown();
            }
        });
        
        this.input.addEventListener('blur', () => {
            // Delay to allow click on dropdown
            setTimeout(() => this._hideDropdown(), 150);
        });
        
        // Click outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this._hideDropdown();
            }
        });
    }
    
    /**
     * Handle input changes
     */
    _onInput(value) {
        this.options.onChange(value);
        
        clearTimeout(this.searchTimeout);
        
        if (value.length < this.options.minChars) {
            this._hideDropdown();
            return;
        }
        
        this._showLoading();
        
        this.searchTimeout = setTimeout(async () => {
            await this._search(value);
        }, this.options.debounceMs);
    }
    
    /**
     * Perform search
     */
    async _search(query) {
        try {
            // Check if TickerService is available
            if (typeof TickerService === 'undefined') {
                throw new Error('TickerService not loaded');
            }
            
            this.results = await TickerService.searchTickers(query);
            this._hideLoading();
            
            if (this.results.length > 0) {
                this._renderResults();
                this._showDropdown();
            } else {
                this._renderNoResults();
                this._showDropdown();
            }
            
        } catch (error) {
            console.error('[TickerInput] Search error:', error);
            this._hideLoading();
            this._renderError(error.message);
            this._showDropdown();
        }
    }
    
    /**
     * Render search results
     */
    _renderResults() {
        this.dropdown.innerHTML = this.results.map((result, index) => `
            <div class="ticker-input-item" data-index="${index}" data-ticker="${result.ticker}">
                <span class="ticker-input-item-symbol">${result.ticker}</span>
                <span class="ticker-input-item-name">${result.name}</span>
                <span class="ticker-input-item-exchange">${result.exchange || result.type}</span>
            </div>
        `).join('');
        
        // Attach click handlers
        this.dropdown.querySelectorAll('.ticker-input-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this._selectResult(index);
            });
        });
    }
    
    /**
     * Render no results message
     */
    _renderNoResults() {
        this.dropdown.innerHTML = `
            <div class="ticker-input-no-results">
                No tickers found. Try a different search.
            </div>
        `;
    }
    
    /**
     * Render error message
     */
    _renderError(message) {
        this.dropdown.innerHTML = `
            <div class="ticker-input-error">
                ⚠️ ${message}
            </div>
        `;
    }
    
    /**
     * Handle keyboard navigation
     */
    _onKeyDown(e) {
        if (this.results.length === 0) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.highlightedIndex = Math.min(this.highlightedIndex + 1, this.results.length - 1);
                this._updateHighlight();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.highlightedIndex = Math.max(this.highlightedIndex - 1, 0);
                this._updateHighlight();
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.highlightedIndex >= 0) {
                    this._selectResult(this.highlightedIndex);
                } else if (this.results.length > 0) {
                    this._selectResult(0);
                }
                break;
                
            case 'Escape':
                this._hideDropdown();
                break;
        }
    }
    
    /**
     * Update highlight styling
     */
    _updateHighlight() {
        this.dropdown.querySelectorAll('.ticker-input-item').forEach((item, index) => {
            item.classList.toggle('highlighted', index === this.highlightedIndex);
        });
        
        // Scroll into view if needed
        const highlighted = this.dropdown.querySelector('.highlighted');
        if (highlighted) {
            highlighted.scrollIntoView({ block: 'nearest' });
        }
    }
    
    /**
     * Select a result
     */
    _selectResult(index) {
        const result = this.results[index];
        if (!result) return;
        
        this.selectedTicker = result.ticker;
        this.input.value = result.ticker;
        this._hideDropdown();
        
        // Call the onSelect callback
        this.options.onSelect(result.ticker, result);
    }
    
    /**
     * Show/hide helpers
     */
    _showDropdown() {
        this.dropdown.style.display = 'block';
    }
    
    _hideDropdown() {
        this.dropdown.style.display = 'none';
        this.highlightedIndex = -1;
    }
    
    _showLoading() {
        this.searchIcon.style.display = 'none';
        this.loadingIcon.style.display = 'block';
    }
    
    _hideLoading() {
        this.loadingIcon.style.display = 'none';
        this.searchIcon.style.display = 'block';
    }
    
    /**
     * Public API
     */
    getValue() {
        return this.selectedTicker || this.input.value;
    }
    
    setValue(ticker) {
        this.input.value = ticker;
        this.selectedTicker = ticker;
    }
    
    clear() {
        this.input.value = '';
        this.selectedTicker = null;
        this.results = [];
        this._hideDropdown();
    }
    
    focus() {
        this.input.focus();
    }
    
    disable() {
        this.input.disabled = true;
    }
    
    enable() {
        this.input.disabled = false;
    }
}

// Export for both module and browser use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TickerInput;
}
