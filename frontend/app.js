/**
 * DWCOA Financial Dashboard Application
 */

// Configuration
const API_BASE = '/api';  // Relative path, works with CloudFront

// State
let authToken = null;
let userRole = null;
let categories = [];

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount || 0);
}

function formatPercent(value) {
    return (value * 100).toFixed(1) + '%';
}

function formatDate(dateStr) {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// API functions
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE + endpoint;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    if (response.status === 401) {
        logout();
        throw new Error('Session expired');
    }

    return response;
}

async function login(password) {
    const response = await fetch(API_BASE + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Login failed');
    }

    const data = await response.json();
    authToken = data.token;
    userRole = data.role;

    // Store in localStorage
    localStorage.setItem('dwcoa_token', authToken);
    localStorage.setItem('dwcoa_role', userRole);

    return data;
}

function logout() {
    authToken = null;
    userRole = null;
    localStorage.removeItem('dwcoa_token');
    localStorage.removeItem('dwcoa_role');

    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('login-modal').classList.remove('hidden');
}

async function checkAuth() {
    const token = localStorage.getItem('dwcoa_token');
    const role = localStorage.getItem('dwcoa_role');

    if (!token) return false;

    try {
        const response = await fetch(API_BASE + '/auth/verify', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            authToken = token;
            userRole = role;
            return true;
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }

    localStorage.removeItem('dwcoa_token');
    localStorage.removeItem('dwcoa_role');
    return false;
}

// Dashboard functions
async function loadDashboard() {
    try {
        const response = await apiRequest('/dashboard');
        const data = await response.json();

        renderDashboard(data);
    } catch (e) {
        console.error('Failed to load dashboard:', e);
        alert('Failed to load dashboard: ' + e.message);
    }
}

function renderDashboard(data) {
    // Last updated
    document.getElementById('last-updated').textContent =
        data.last_updated ? `Last updated: ${formatDate(data.last_updated)}` : 'No data uploaded';

    // User role
    const roleEl = document.getElementById('user-role');
    roleEl.textContent = userRole === 'admin' ? 'Admin' : 'Board';

    // Show admin controls if admin
    if (userRole === 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
    }

    // Account balances
    const accountsGrid = document.getElementById('accounts-grid');
    accountsGrid.innerHTML = data.accounts.map(acc => `
        <div class="account-card">
            <div class="name">${acc.name}</div>
            <div class="balance">${formatCurrency(acc.balance)}</div>
        </div>
    `).join('');

    document.getElementById('total-cash').textContent = formatCurrency(data.total_cash);

    // Income summary
    const income = data.income_summary;
    document.getElementById('income-ytd-budget').textContent = formatCurrency(income.ytd_budget);
    document.getElementById('income-ytd-actual').textContent = formatCurrency(income.ytd_actual);

    const incomeTable = document.querySelector('#income-table tbody');
    incomeTable.innerHTML = income.categories.map(cat => `
        <tr>
            <td>${cat.category}</td>
            <td>${formatCurrency(cat.ytd_budget)}</td>
            <td>${formatCurrency(cat.ytd_actual)}</td>
        </tr>
    `).join('');

    // Expense summary
    const expense = data.expense_summary;
    document.getElementById('expense-ytd-budget').textContent = formatCurrency(expense.ytd_budget);
    document.getElementById('expense-ytd-actual').textContent = formatCurrency(expense.ytd_actual);
    document.getElementById('expense-remaining').textContent = formatCurrency(expense.remaining);
    document.getElementById('expense-remaining').className = expense.remaining >= 0 ? 'positive' : 'negative';

    const expenseTable = document.querySelector('#expense-table tbody');
    expenseTable.innerHTML = expense.categories.map(cat => `
        <tr>
            <td>${cat.category}</td>
            <td>${formatCurrency(cat.ytd_budget)}</td>
            <td>${formatCurrency(cat.ytd_actual)}</td>
            <td class="${cat.remaining >= 0 ? 'positive' : 'negative'}">${formatCurrency(cat.remaining)}</td>
        </tr>
    `).join('');

    // Dues status
    const duesTable = document.querySelector('#dues-table tbody');
    duesTable.innerHTML = data.dues_status.map(unit => `
        <tr>
            <td>${unit.unit}</td>
            <td>${formatPercent(unit.ownership_pct)}</td>
            <td>${formatCurrency(unit.expected_annual)}</td>
            <td>${formatCurrency(unit.paid_ytd)}</td>
            <td class="${unit.outstanding > 0 ? 'negative' : 'positive'}">${formatCurrency(unit.outstanding)}</td>
        </tr>
    `).join('');

    // Review count
    document.getElementById('review-count').textContent =
        `${data.review_count} transaction(s) need review`;
}

// Upload functions
async function uploadCSV(file) {
    const formData = new FormData();
    formData.append('file', file);

    // Read file as text for JSON body
    const text = await file.text();

    const response = await apiRequest('/transactions/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file: text })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Upload failed');
    }

    return await response.json();
}

// Download functions
async function downloadCSV() {
    const response = await apiRequest('/transactions/download');
    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dwcoa_transactions.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

async function downloadPDF() {
    const response = await apiRequest('/reports/pdf');
    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dwcoa_report.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Review functions
async function loadReviewQueue() {
    const response = await apiRequest('/review');
    const data = await response.json();

    // Load categories for dropdown
    const catResponse = await apiRequest('/categories');
    const catData = await catResponse.json();
    categories = catData.categories;

    renderReviewQueue(data.transactions);
}

function renderReviewQueue(transactions) {
    const reviewList = document.getElementById('review-list');

    if (transactions.length === 0) {
        reviewList.innerHTML = '<p>No transactions need review.</p>';
        return;
    }

    const categoryOptions = categories
        .filter(c => c.active)
        .map(c => `<option value="${c.id}">${c.name}</option>`)
        .join('');

    reviewList.innerHTML = transactions.map(txn => `
        <div class="review-item" data-id="${txn.id}">
            <div>
                <div class="description">${txn.description}</div>
                <div class="meta">${txn.account_name} | ${txn.post_date} | ${formatCurrency(txn.credit || txn.debit)}</div>
                ${txn.auto_category ? `<div class="meta">Suggested: ${txn.auto_category} (${txn.confidence}%)</div>` : ''}
            </div>
            <select class="category-select">
                <option value="">Select category...</option>
                ${categoryOptions}
            </select>
            <button class="btn-primary save-category-btn">Save</button>
        </div>
    `).join('');

    // Add event listeners
    reviewList.querySelectorAll('.save-category-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const item = e.target.closest('.review-item');
            const txnId = item.dataset.id;
            const categoryId = item.querySelector('.category-select').value;

            if (!categoryId) {
                alert('Please select a category');
                return;
            }

            try {
                await apiRequest(`/transactions/${txnId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({
                        category_id: parseInt(categoryId),
                        needs_review: false
                    })
                });

                item.remove();

                // Check if queue is empty
                if (reviewList.children.length === 0) {
                    reviewList.innerHTML = '<p>All transactions reviewed!</p>';
                }
            } catch (e) {
                alert('Failed to save: ' + e.message);
            }
        });
    });
}

// Budget management functions
async function loadBudgets(year) {
    try {
        const response = await apiRequest(`/budgets?year=${year}`);
        const data = await response.json();
        renderBudgetTable(data.budgets, year);
    } catch (e) {
        showBudgetStatus('Error loading budgets: ' + e.message, 'error');
    }
}

function renderBudgetTable(budgets, year) {
    const tbody = document.getElementById('budget-edit-body');

    if (!budgets || budgets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5">No budgets found for ${year}. Copy from a previous year or add categories.</td></tr>`;
        return;
    }

    tbody.innerHTML = budgets.map(b => `
        <tr data-category-id="${b.category_id}" data-year="${year}">
            <td>${b.category_name}</td>
            <td>${b.category_type}</td>
            <td>
                <select class="timing-select">
                    <option value="monthly" ${b.effective_timing === 'monthly' ? 'selected' : ''}>Monthly</option>
                    <option value="quarterly" ${b.effective_timing === 'quarterly' ? 'selected' : ''}>Quarterly</option>
                    <option value="annual" ${b.effective_timing === 'annual' ? 'selected' : ''}>Annual</option>
                </select>
            </td>
            <td>
                <input type="number" class="amount-input" value="${b.annual_amount || 0}" step="0.01" min="0">
            </td>
            <td>
                <button class="btn-primary save-budget-btn">Save</button>
            </td>
        </tr>
    `).join('');

    // Add save handlers
    tbody.querySelectorAll('.save-budget-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.target.closest('tr');
            const categoryId = parseInt(row.dataset.categoryId);
            const year = parseInt(row.dataset.year);
            const amount = parseFloat(row.querySelector('.amount-input').value);
            const timing = row.querySelector('.timing-select').value;

            try {
                await apiRequest('/budgets', {
                    method: 'POST',
                    body: JSON.stringify({
                        year: year,
                        category_id: categoryId,
                        annual_amount: amount,
                        timing: timing
                    })
                });
                showBudgetStatus('Budget saved!', 'success');
            } catch (e) {
                showBudgetStatus('Error saving: ' + e.message, 'error');
            }
        });
    });
}

async function copyBudgets(fromYear, toYear) {
    try {
        const response = await apiRequest('/budgets/copy', {
            method: 'POST',
            body: JSON.stringify({
                from_year: fromYear,
                to_year: toYear
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Copy failed');
        }

        const data = await response.json();
        showBudgetStatus(data.message, 'success');

        // Reload the target year
        document.getElementById('budget-year').value = toYear;
        await loadBudgets(toYear);
    } catch (e) {
        showBudgetStatus('Error copying budgets: ' + e.message, 'error');
    }
}

function showBudgetStatus(message, type) {
    const statusEl = document.getElementById('budget-status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.classList.remove('hidden');

    // Auto-hide after 3 seconds
    setTimeout(() => {
        statusEl.classList.add('hidden');
    }, 3000);
}

// Event handlers
document.addEventListener('DOMContentLoaded', async () => {
    // Check existing auth
    const isAuthenticated = await checkAuth();

    if (isAuthenticated) {
        document.getElementById('login-modal').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        await loadDashboard();
    }

    // Login form
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('login-error');

        try {
            await login(password);
            document.getElementById('login-modal').classList.add('hidden');
            document.getElementById('dashboard').classList.remove('hidden');
            await loadDashboard();
        } catch (e) {
            errorEl.textContent = e.message;
            errorEl.classList.remove('hidden');
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', logout);

    // Upload
    document.getElementById('upload-btn').addEventListener('click', async () => {
        const fileInput = document.getElementById('csv-file');
        const statusEl = document.getElementById('upload-status');

        if (!fileInput.files.length) {
            alert('Please select a CSV file');
            return;
        }

        try {
            statusEl.textContent = 'Uploading...';
            const result = await uploadCSV(fileInput.files[0]);
            statusEl.textContent = `Success! ${result.stats.total_rows} transactions, ${result.stats.needs_review} need review`;
            await loadDashboard();
        } catch (e) {
            statusEl.textContent = 'Error: ' + e.message;
        }
    });

    // Downloads
    document.getElementById('download-csv-btn').addEventListener('click', downloadCSV);
    document.getElementById('download-pdf-btn').addEventListener('click', downloadPDF);
    document.getElementById('print-btn').addEventListener('click', () => window.print());

    // Review
    document.getElementById('review-btn').addEventListener('click', async () => {
        await loadReviewQueue();
        document.getElementById('review-modal').classList.remove('hidden');
    });

    document.getElementById('close-review-btn').addEventListener('click', () => {
        document.getElementById('review-modal').classList.add('hidden');
        loadDashboard();  // Refresh counts
    });

    // Budget management
    document.getElementById('manage-budgets-btn').addEventListener('click', async () => {
        const year = parseInt(document.getElementById('budget-year').value);
        await loadBudgets(year);
        document.getElementById('budget-modal').classList.remove('hidden');
    });

    document.getElementById('load-budgets-btn').addEventListener('click', async () => {
        const year = parseInt(document.getElementById('budget-year').value);
        await loadBudgets(year);
    });

    document.getElementById('copy-budgets-btn').addEventListener('click', async () => {
        const fromYear = parseInt(document.getElementById('copy-from-year').value);
        const toYear = parseInt(document.getElementById('copy-to-year').value);

        if (fromYear === toYear) {
            showBudgetStatus('From and To years must be different', 'error');
            return;
        }

        if (!confirm(`Copy all budgets from ${fromYear} to ${toYear}? This will overwrite existing ${toYear} budgets.`)) {
            return;
        }

        await copyBudgets(fromYear, toYear);
    });

    document.getElementById('close-budget-btn').addEventListener('click', () => {
        document.getElementById('budget-modal').classList.add('hidden');
        loadDashboard();  // Refresh dashboard with any changes
    });
});
