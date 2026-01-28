/**
 * Guide Bot - Authentication Module
 * Handles login, signup, and token management
 */

const API_BASE = 'http://localhost:8000';

// ============ UI HELPERS ============

function showError(message) {
    const errorEl = document.getElementById('error-message');
    const successEl = document.getElementById('success-message');
    
    if (successEl) successEl.classList.add('hidden');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }
}

function showSuccess(message) {
    const errorEl = document.getElementById('error-message');
    const successEl = document.getElementById('success-message');
    
    if (errorEl) errorEl.classList.add('hidden');
    if (successEl) {
        successEl.textContent = message;
        successEl.classList.remove('hidden');
    }
}

function clearMessages() {
    const errorEl = document.getElementById('error-message');
    const successEl = document.getElementById('success-message');
    
    if (errorEl) errorEl.classList.add('hidden');
    if (successEl) successEl.classList.add('hidden');
}

function setLoading(isLoading) {
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    
    if (submitBtn) submitBtn.disabled = isLoading;
    if (btnText) btnText.classList.toggle('opacity-50', isLoading);
    if (btnSpinner) btnSpinner.classList.toggle('hidden', !isLoading);
}

// ============ TOKEN MANAGEMENT ============

function saveToken(token) {
    localStorage.setItem('token', token);
}

function getToken() {
    return localStorage.getItem('token');
}

function removeToken() {
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
}

function saveUserEmail(email) {
    localStorage.setItem('userEmail', email);
}

function getUserEmail() {
    return localStorage.getItem('userEmail');
}

// ============ API HELPERS ============

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const token = getToken();
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    
    if (token && !options.skipAuth) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(url, {
            ...options,
            headers,
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // Handle 401 - token expired
            if (response.status === 401 && !options.skipAuth) {
                removeToken();
                window.location.href = 'login.html';
                return;
            }
            
            throw new Error(data.detail || data.message || 'Request failed');
        }
        
        return data;
    } catch (error) {
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Cannot connect to server. Is the backend running?');
        }
        throw error;
    }
}

// ============ AUTH FUNCTIONS ============

async function handleLogin(email, password) {
    clearMessages();
    setLoading(true);
    
    try {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true,
        });
        
        saveToken(data.access_token);
        saveUserEmail(email);
        showSuccess('Login successful! Redirecting...');
        
        setTimeout(() => {
            window.location.href = 'dashboard.html';
        }, 500);
        
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

async function handleSignup(email, password) {
    clearMessages();
    setLoading(true);
    
    try {
        const data = await apiRequest('/auth/signup', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true,
        });
        
        saveToken(data.access_token);
        saveUserEmail(email);
        showSuccess('Account created! Redirecting to dashboard...');
        
        setTimeout(() => {
            window.location.href = 'dashboard.html';
        }, 500);
        
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

function handleLogout() {
    removeToken();
    window.location.href = 'login.html';
}

// ============ USER INFO ============

async function getCurrentUser() {
    try {
        return await apiRequest('/auth/me');
    } catch (error) {
        console.error('Failed to get current user:', error);
        return null;
    }
}
