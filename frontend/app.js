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
        minute: '2-digit',
        timeZone: 'America/Los_Angeles'
    }) + ' PT';
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
async function loadDashboard(asOfDate = null) {
    try {
        let url = '/dashboard';
        if (asOfDate) {
            url += `?as_of_date=${asOfDate}`;
        }
        const response = await apiRequest(url);
        const data = await response.json();

        renderDashboard(data);
    } catch (e) {
        console.error('Failed to load dashboard:', e);
        alert('Failed to load dashboard: ' + e.message);
    }
}

function getTodayString() {
    return new Date().toISOString().split('T')[0];
}

function renderDashboard(data) {
    // Last updated
    document.getElementById('last-updated').textContent =
        data.last_updated ? `Last updated: ${formatDate(data.last_updated)}` : 'No data uploaded';

    // Update date picker and snapshot label
    const snapshotDate = data.as_of_date || getTodayString();
    const datePickerEl = document.getElementById('snapshot-date');
    const snapshotLabelEl = document.getElementById('snapshot-label');

    if (datePickerEl) {
        datePickerEl.value = snapshotDate;
    }

    if (snapshotLabelEl) {
        const today = getTodayString();
        if (snapshotDate === today) {
            snapshotLabelEl.textContent = '(Current)';
        } else {
            const d = new Date(snapshotDate + 'T00:00:00');
            const formatted = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            snapshotLabelEl.textContent = `Showing ${data.year} data through ${formatted}`;
        }
    }

    // User role - show badge and control admin visibility
    const roleEl = document.getElementById('user-role');
    roleEl.textContent = userRole === 'admin' ? 'Admin' : 'Homeowner';

    // Show/hide admin controls based on role
    if (userRole === 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
    } else {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.add('hidden'));
    }

    // Account balances - find each account by name
    const findBalance = (name) => {
        const acc = data.accounts.find(a => a.name === name);
        return acc ? acc.balance : 0;
    };

    document.getElementById('balance-checking').textContent = formatCurrency(findBalance('Checking'));
    document.getElementById('balance-savings').textContent = formatCurrency(findBalance('Savings'));
    document.getElementById('balance-reserve').textContent = formatCurrency(findBalance('Reserve Fund'));

    // Reserve YTD change (net of contributions - expenses)
    const reserve = data.reserve_fund || { net: 0 };
    const ytdChangeEl = document.getElementById('reserve-ytd-change');
    const ytdPrefix = reserve.net >= 0 ? '+' : '';
    ytdChangeEl.textContent = `YTD: ${ytdPrefix}${formatCurrency(reserve.net)}`;
    ytdChangeEl.className = `ytd-change ${reserve.net >= 0 ? 'positive' : 'negative'}`;

    document.getElementById('total-cash').textContent = formatCurrency(data.total_cash);

    // Income & Dues summary
    const duesBudget = data.dues_status.reduce((sum, u) => sum + u.expected_ytd, 0);
    const duesActual = data.dues_status.reduce((sum, u) => sum + u.paid_ytd, 0);
    const duesRemaining = duesBudget - duesActual;

    document.getElementById('dues-budget').textContent = formatCurrency(duesBudget);
    document.getElementById('dues-actual').textContent = formatCurrency(duesActual);
    const duesRemainingEl = document.getElementById('dues-remaining');
    duesRemainingEl.textContent = formatCurrency(duesRemaining);
    duesRemainingEl.className = duesRemaining >= 0 ? 'positive' : 'negative';

    // Dues table (compact)
    const duesTable = document.querySelector('#dues-table tbody');
    duesTable.innerHTML = data.dues_status.map(unit => `
        <tr>
            <td>${unit.unit}</td>
            <td>${formatPercent(unit.ownership_pct)}</td>
            <td>${formatCurrency(unit.expected_ytd)}</td>
            <td>${formatCurrency(unit.paid_ytd)}</td>
            <td class="${unit.outstanding > 0 ? 'negative' : 'positive'}">${formatCurrency(unit.outstanding)}</td>
        </tr>
    `).join('');

    // Expense summary
    const expense = data.expense_summary;
    document.getElementById('expense-budget').textContent = formatCurrency(expense.ytd_budget);
    document.getElementById('expense-actual').textContent = formatCurrency(expense.ytd_actual);
    const expenseRemainingEl = document.getElementById('expense-remaining');
    expenseRemainingEl.textContent = formatCurrency(expense.remaining);
    expenseRemainingEl.className = expense.remaining >= 0 ? 'positive' : 'negative';

    const expenseTable = document.querySelector('#expense-table tbody');
    expenseTable.innerHTML = expense.categories.map(cat => `
        <tr>
            <td>${cat.category}</td>
            <td>${formatCurrency(cat.ytd_budget)}</td>
            <td>${formatCurrency(cat.ytd_actual)}</td>
            <td class="${cat.remaining >= 0 ? 'positive' : 'negative'}">${formatCurrency(cat.remaining)}</td>
        </tr>
    `).join('');

    // Review button - show count and gray out if zero
    const reviewBtn = document.getElementById('review-btn');
    if (reviewBtn) {
        reviewBtn.textContent = `Review Transactions (${data.review_count})`;
        if (data.review_count === 0) {
            reviewBtn.classList.add('grayed');
        } else {
            reviewBtn.classList.remove('grayed');
        }
    }
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
    // Get the selected date from the date picker
    const snapshotDateEl = document.getElementById('snapshot-date');
    const asOfDate = snapshotDateEl ? snapshotDateEl.value : getTodayString();

    const response = await apiRequest(`/reports/pdf?as_of_date=${asOfDate}`);
    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `DWCOA_Report_${asOfDate}.pdf`;
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
        <tr data-category-id="${b.category_id}" data-year="${year}" data-txn-count="${b.transaction_count || 0}">
            <td>
                <input type="text" class="name-input" value="${b.category_name}" placeholder="Category name">
            </td>
            <td>
                <span class="type-text">${b.category_type}</span>
            </td>
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
            <td class="action-buttons">
                <button class="btn-primary save-budget-btn">Save</button>
                <button class="btn-secondary retire-btn">Retire</button>
            </td>
        </tr>
    `).join('');

    // Add save handlers
    tbody.querySelectorAll('.save-budget-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.target.closest('tr');
            const categoryId = parseInt(row.dataset.categoryId);
            const year = parseInt(row.dataset.year);
            const name = row.querySelector('.name-input').value.trim();
            const amount = parseFloat(row.querySelector('.amount-input').value);
            const timing = row.querySelector('.timing-select').value;

            if (!name) {
                showBudgetStatus('Category name is required', 'error');
                return;
            }

            try {
                // Update category name (type is fixed for existing categories)
                await apiRequest(`/categories/${categoryId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ name })
                });

                // Update budget
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

    // Add retire handlers
    tbody.querySelectorAll('.retire-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.target.closest('tr');
            const categoryId = parseInt(row.dataset.categoryId);
            const txnCount = parseInt(row.dataset.txnCount) || 0;
            const name = row.querySelector('.name-input').value;

            let message = `Retire category "${name}"?`;
            if (txnCount > 0) {
                message = `Category "${name}" has ${txnCount} transaction(s). Retiring will hide it from dropdowns but preserve historical data. Continue?`;
            }

            if (!confirm(message)) {
                return;
            }

            try {
                await apiRequest(`/categories/${categoryId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ active: false })
                });
                showBudgetStatus(`Category "${name}" retired`, 'success');
                // Reload budgets to reflect change
                const year = parseInt(row.dataset.year);
                await loadBudgets(year);
            } catch (e) {
                showBudgetStatus('Error retiring: ' + e.message, 'error');
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
        await initTransactionsTable();
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
            await initTransactionsTable();
        } catch (e) {
            errorEl.textContent = e.message;
            errorEl.classList.remove('hidden');
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', logout);

    // Date picker - initialize with today and auto-load on change
    const snapshotDateEl = document.getElementById('snapshot-date');
    const resetTodayBtn = document.getElementById('reset-today-btn');

    if (snapshotDateEl) {
        snapshotDateEl.value = getTodayString();

        // Auto-load when date changes
        snapshotDateEl.addEventListener('change', async () => {
            await loadDashboard(snapshotDateEl.value);
        });
    }

    // Reset to Today button
    if (resetTodayBtn) {
        resetTodayBtn.addEventListener('click', async () => {
            if (snapshotDateEl) {
                snapshotDateEl.value = getTodayString();
            }
            await loadDashboard();
        });
    }

    // File chooser and upload
    const fileInput = document.getElementById('csv-file');
    const chooseFileBtn = document.getElementById('choose-file-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const statusEl = document.getElementById('upload-status');

    if (chooseFileBtn && fileInput) {
        chooseFileBtn.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                uploadBtn.disabled = false;
                chooseFileBtn.textContent = fileInput.files[0].name;
            } else {
                uploadBtn.disabled = true;
                chooseFileBtn.textContent = 'Choose File';
            }
        });
    }

    if (uploadBtn) {
        uploadBtn.addEventListener('click', async () => {
            if (!fileInput || !fileInput.files.length) return;

            try {
                if (statusEl) statusEl.textContent = 'Uploading...';
                uploadBtn.disabled = true;
                const result = await uploadCSV(fileInput.files[0]);
                if (statusEl) statusEl.textContent = `${result.stats.total_rows} rows, ${result.stats.needs_review} need review`;
                fileInput.value = '';
                chooseFileBtn.textContent = 'Choose File';
                await loadDashboard();
                // Refresh transactions table
                if (transactionsTable) {
                    const transactions = await loadTransactions();
                    transactionsTable.setData(transactions);
                }
            } catch (e) {
                if (statusEl) statusEl.textContent = 'Error: ' + e.message;
                uploadBtn.disabled = false;
            }
        });
    }

    // Downloads
    const downloadCsvBtn = document.getElementById('download-csv-btn');
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    const printBtn = document.getElementById('print-btn');

    if (downloadCsvBtn) downloadCsvBtn.addEventListener('click', downloadCSV);
    if (downloadPdfBtn) downloadPdfBtn.addEventListener('click', downloadPDF);
    if (printBtn) printBtn.addEventListener('click', () => window.print());

    // Transaction Viewer export
    const exportTransactionsBtn = document.getElementById('export-transactions-btn');
    if (exportTransactionsBtn) {
        exportTransactionsBtn.addEventListener('click', exportFilteredTransactions);
    }

    // Review
    const reviewBtn = document.getElementById('review-btn');
    if (reviewBtn) {
        reviewBtn.addEventListener('click', async () => {
            await loadReviewQueue();
            const reviewModal = document.getElementById('review-modal');
            if (reviewModal) reviewModal.classList.remove('hidden');
        });
    }

    const closeReviewBtn = document.getElementById('close-review-btn');
    if (closeReviewBtn) {
        closeReviewBtn.addEventListener('click', () => {
            document.getElementById('review-modal').classList.add('hidden');
            loadDashboard();  // Refresh counts
        });
    }

    // Budget management
    const manageBudgetsBtn = document.getElementById('manage-budgets-btn');
    const copyBudgetsBtn = document.getElementById('copy-budgets-btn');
    const closeBudgetBtn = document.getElementById('close-budget-btn');
    const budgetYearEl = document.getElementById('budget-year');

    if (manageBudgetsBtn && budgetYearEl) {
        manageBudgetsBtn.addEventListener('click', async () => {
            const year = parseInt(budgetYearEl.value);
            await loadBudgets(year);
            document.getElementById('budget-modal').classList.remove('hidden');
        });

        // Auto-load when year selection changes
        budgetYearEl.addEventListener('change', async () => {
            const year = parseInt(budgetYearEl.value);
            await loadBudgets(year);
        });
    }

    if (copyBudgetsBtn) {
        copyBudgetsBtn.addEventListener('click', async () => {
            const copyFromEl = document.getElementById('copy-from-year');
            const copyToEl = document.getElementById('copy-to-year');
            if (!copyFromEl || !copyToEl) return;

            const fromYear = parseInt(copyFromEl.value);
            const toYear = parseInt(copyToEl.value);

            if (fromYear === toYear) {
                showBudgetStatus('From and To years must be different', 'error');
                return;
            }

            if (!confirm(`Copy all budgets from ${fromYear} to ${toYear}? This will overwrite existing ${toYear} budgets.`)) {
                return;
            }

            await copyBudgets(fromYear, toYear);
        });
    }

    if (closeBudgetBtn) {
        closeBudgetBtn.addEventListener('click', () => {
            document.getElementById('budget-modal').classList.add('hidden');
            loadDashboard();  // Refresh dashboard with any changes
        });
    }

    // Add Category button
    const addCategoryBtn = document.getElementById('add-category-btn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', () => {
            addNewCategoryRow();
        });
    }
});

// Add new category row to the budget table
function addNewCategoryRow() {
    const tbody = document.getElementById('budget-edit-body');
    const year = parseInt(document.getElementById('budget-year').value);

    // Check if there's already a new row being added
    if (tbody.querySelector('tr.new-category-row')) {
        showBudgetStatus('Please save or cancel the current new category first', 'error');
        return;
    }

    const newRow = document.createElement('tr');
    newRow.className = 'new-category-row';
    newRow.dataset.year = year;
    newRow.innerHTML = `
        <td>
            <input type="text" class="name-input" placeholder="Category name" autofocus>
        </td>
        <td>
            <select class="type-select">
                <option value="Expense">Expense</option>
                <option value="Income">Income</option>
                <option value="Transfer">Transfer</option>
            </select>
        </td>
        <td>
            <select class="timing-select">
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
            </select>
        </td>
        <td>
            <input type="number" class="amount-input" value="0" step="0.01" min="0">
        </td>
        <td class="action-buttons">
            <button class="btn-primary create-category-btn">Create</button>
            <button class="btn-secondary cancel-category-btn">Cancel</button>
        </td>
    `;

    tbody.appendChild(newRow);

    // Focus the name input
    newRow.querySelector('.name-input').focus();

    // Create button handler
    newRow.querySelector('.create-category-btn').addEventListener('click', async () => {
        const name = newRow.querySelector('.name-input').value.trim();
        const type = newRow.querySelector('.type-select').value;
        const timing = newRow.querySelector('.timing-select').value;
        const amount = parseFloat(newRow.querySelector('.amount-input').value) || 0;

        if (!name) {
            showBudgetStatus('Category name is required', 'error');
            return;
        }

        try {
            // Create the category
            const catResponse = await apiRequest('/categories', {
                method: 'POST',
                body: JSON.stringify({ name, type, timing })
            });

            if (!catResponse.ok) {
                const error = await catResponse.json();
                throw new Error(error.message || 'Failed to create category');
            }

            const category = await catResponse.json();

            // Create budget for this category
            await apiRequest('/budgets', {
                method: 'POST',
                body: JSON.stringify({
                    year: year,
                    category_id: category.id,
                    annual_amount: amount,
                    timing: timing
                })
            });

            showBudgetStatus(`Category "${name}" created!`, 'success');

            // Reload budgets to show new category in proper order
            await loadBudgets(year);
        } catch (e) {
            showBudgetStatus('Error: ' + e.message, 'error');
        }
    });

    // Cancel button handler
    newRow.querySelector('.cancel-category-btn').addEventListener('click', () => {
        newRow.remove();
    });
}

// Transaction Viewer - Tabulator
let transactionsTable = null;

async function loadTransactions() {
    try {
        // Get all transactions (no pagination from server, let Tabulator handle it)
        const response = await apiRequest('/transactions?limit=10000');
        const data = await response.json();
        return data.transactions;
    } catch (e) {
        console.error('Failed to load transactions:', e);
        return [];
    }
}

async function initTransactionsTable() {
    const transactions = await loadTransactions();

    transactionsTable = new Tabulator("#transactions-table", {
        data: transactions,
        layout: "fitColumns",
        responsiveLayout: "collapse",
        pagination: true,
        paginationSize: 25,
        paginationSizeSelector: [25, 50, 100],
        initialSort: [{ column: "post_date", dir: "desc" }],
        placeholder: "No transactions uploaded",
        columns: [
            {
                title: "Post Date",
                field: "post_date",
                sorter: "date",
                headerFilter: "input",
                width: 120
            },
            {
                title: "Account",
                field: "account_name",
                sorter: "string",
                headerFilter: "input",
                width: 120
            },
            {
                title: "Category",
                field: "category",
                sorter: "string",
                headerFilter: "input",
                formatter: function(cell) {
                    const val = cell.getValue();
                    return val || '<span class="uncategorized">Uncategorized</span>';
                }
            },
            {
                title: "Description",
                field: "description",
                sorter: "string",
                headerFilter: "input"
            },
            {
                title: "Debit",
                field: "debit",
                sorter: "number",
                hozAlign: "right",
                formatter: "money",
                formatterParams: { symbol: "$", precision: 2 },
                width: 110
            },
            {
                title: "Credit",
                field: "credit",
                sorter: "number",
                hozAlign: "right",
                formatter: "money",
                formatterParams: { symbol: "$", precision: 2 },
                width: 110
            }
        ]
    });
}

function exportFilteredTransactions() {
    if (transactionsTable) {
        transactionsTable.download("csv", "dwcoa_transactions_filtered.csv");
    }
}
