/**
 * Guide Bot - Dashboard Module
 * Handles portfolio management and file downloads
 */

// ============ INITIALIZATION ============

async function initDashboard() {
    // Display user email
    const userEmailEl = document.getElementById('user-email');
    const email = getUserEmail();
    if (userEmailEl && email) {
        userEmailEl.textContent = email;
    }
    
    // Load portfolio
    await loadPortfolio();
    
    // Setup add ticker form
    setupAddTickerForm();
}

// ============ PORTFOLIO MANAGEMENT ============

async function loadPortfolio() {
    const loadingEl = document.getElementById('loading-state');
    const emptyEl = document.getElementById('empty-state');
    const listEl = document.getElementById('ticker-list');
    
    try {
        const data = await apiRequest('/portfolio');
        
        loadingEl.classList.add('hidden');
        
        if (data.tickers.length === 0) {
            emptyEl.classList.remove('hidden');
            listEl.classList.add('hidden');
        } else {
            emptyEl.classList.add('hidden');
            listEl.classList.remove('hidden');
            renderTickerList(data.tickers);
        }
    } catch (error) {
        loadingEl.classList.add('hidden');
        showError(`Failed to load portfolio: ${error.message}`);
    }
}

function renderTickerList(tickers) {
    const listEl = document.getElementById('ticker-list');
    
    listEl.innerHTML = tickers.map(ticker => `
        <div class="flex items-center justify-between px-6 py-4 hover:bg-gray-700/50 transition-colors" data-ticker="${ticker.ticker}">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-lg bg-brand-600/20 flex items-center justify-center">
                    <span class="text-brand-400 font-bold text-lg">${ticker.ticker.charAt(0)}</span>
                </div>
                <div>
                    <h3 class="text-white font-semibold">${ticker.ticker}</h3>
                    <p class="text-gray-500 text-sm">Added ${formatDate(ticker.added_at)}</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="generateAndDownload('${ticker.ticker}')" 
                    class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                    </svg>
                    Excel
                </button>
                <button onclick="removeTicker('${ticker.ticker}')" 
                    class="rounded-lg p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Remove ticker">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ============ ADD TICKER ============

function setupAddTickerForm() {
    const form = document.getElementById('add-ticker-form');
    const input = document.getElementById('ticker-input');
    
    // Auto uppercase
    input.addEventListener('input', (e) => {
        e.target.value = e.target.value.toUpperCase();
    });
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTicker();
    });
}

async function addTicker() {
    const input = document.getElementById('ticker-input');
    const btn = document.getElementById('add-ticker-btn');
    const btnText = document.getElementById('add-btn-text');
    const btnSpinner = document.getElementById('add-btn-spinner');
    
    const ticker = input.value.trim().toUpperCase();
    
    if (!ticker) {
        showError('Please enter a ticker symbol');
        return;
    }
    
    if (!/^[A-Z]{1,5}$/.test(ticker)) {
        showError('Invalid ticker format. Use 1-5 letters.');
        return;
    }
    
    clearMessages();
    btn.disabled = true;
    btnText.textContent = 'Adding...';
    btnSpinner.classList.remove('hidden');
    
    try {
        await apiRequest('/portfolio/ticker', {
            method: 'POST',
            body: JSON.stringify({ ticker }),
        });
        
        showSuccess(`${ticker} added to your portfolio!`);
        input.value = '';
        await loadPortfolio();
        
    } catch (error) {
        showError(error.message);
    } finally {
        btn.disabled = false;
        btnText.textContent = '+ Add Ticker';
        btnSpinner.classList.add('hidden');
    }
}

// ============ REMOVE TICKER ============

async function removeTicker(ticker) {
    if (!confirm(`Remove ${ticker} from your portfolio?`)) {
        return;
    }
    
    clearMessages();
    
    // Optimistic UI update
    const tickerEl = document.querySelector(`[data-ticker="${ticker}"]`);
    if (tickerEl) {
        tickerEl.style.opacity = '0.5';
        tickerEl.style.pointerEvents = 'none';
    }
    
    try {
        await apiRequest(`/portfolio/ticker/${ticker}`, {
            method: 'DELETE',
        });
        
        showSuccess(`${ticker} removed from portfolio`);
        await loadPortfolio();
        
    } catch (error) {
        showError(error.message);
        // Restore UI
        if (tickerEl) {
            tickerEl.style.opacity = '1';
            tickerEl.style.pointerEvents = 'auto';
        }
    }
}

// ============ DOWNLOAD EXCEL ============

function openDownloadModal(ticker) {
    const modal = document.getElementById('download-modal');
    const modalTicker = document.getElementById('modal-ticker');
    const modalLoading = document.getElementById('modal-loading');
    const modalSuccess = document.getElementById('modal-success');
    const modalError = document.getElementById('modal-error');
    
    modalTicker.textContent = ticker;
    modalLoading.classList.remove('hidden');
    modalSuccess.classList.add('hidden');
    modalError.classList.add('hidden');
    modal.classList.remove('hidden');
}

function closeDownloadModal() {
    const modal = document.getElementById('download-modal');
    modal.classList.add('hidden');
}

function showModalSuccess() {
    const modalLoading = document.getElementById('modal-loading');
    const modalSuccess = document.getElementById('modal-success');
    
    modalLoading.classList.add('hidden');
    modalSuccess.classList.remove('hidden');
}

function showModalError(message) {
    const modalLoading = document.getElementById('modal-loading');
    const modalError = document.getElementById('modal-error');
    const modalErrorMessage = document.getElementById('modal-error-message');
    
    modalLoading.classList.add('hidden');
    modalError.classList.remove('hidden');
    modalErrorMessage.textContent = message;
}

async function generateAndDownload(ticker) {
    openDownloadModal(ticker);
    
    try {
        // First, generate the file
        const genResult = await apiRequest(`/generate/${ticker}`, {
            method: 'POST',
            body: JSON.stringify({ force_regenerate: false }),
        });
        
        if (genResult.status === 'failed') {
            throw new Error(genResult.message || 'Failed to generate file');
        }
        
        // Now download
        await downloadFile(ticker);
        showModalSuccess();
        
        // Refresh portfolio to update cache status
        await loadPortfolio();
        
    } catch (error) {
        showModalError(error.message);
    }
}

async function downloadFile(ticker) {
    const token = getToken();
    const url = `${API_BASE}/download/${ticker}`;
    
    // Create a temporary link to trigger download
    const response = await fetch(url, {
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Download failed');
    }
    
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `${ticker}_analysis.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeDownloadModal();
    }
});
