-- DWCOA Financial Tracker Database Schema
-- SQLite database stored in S3

-- Accounts table: Maps masked account numbers to friendly names
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    masked_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE
);

-- Categories table: Income, expense, and transfer categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('Income', 'Expense', 'Transfer', 'Internal')),
    default_account TEXT CHECK (default_account IN ('Savings', 'Checking', 'Reserve Fund', 'Any', NULL)),
    timing TEXT NOT NULL DEFAULT 'monthly' CHECK (timing IN ('monthly', 'quarterly', 'annual')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Units table: Condo units with ownership percentages
CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL UNIQUE,
    ownership_pct REAL NOT NULL CHECK (ownership_pct > 0 AND ownership_pct <= 1)
);

-- Budgets table: Annual budget amounts per category
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    annual_amount REAL NOT NULL DEFAULT 0,
    timing TEXT CHECK (timing IN ('monthly', 'quarterly', 'annual', NULL)),
    UNIQUE(year, category_id)
);

-- Transactions table: All financial transactions
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    account_name TEXT NOT NULL,
    post_date TEXT NOT NULL,
    check_number TEXT,
    description TEXT NOT NULL,
    debit REAL,
    credit REAL,
    status TEXT NOT NULL DEFAULT 'Posted',
    balance REAL NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    auto_category_id INTEGER REFERENCES categories(id),
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    needs_review INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Categorization rules table: Pattern matching for auto-categorization
CREATE TABLE IF NOT EXISTS categorize_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    confidence INTEGER NOT NULL DEFAULT 90 CHECK (confidence >= 0 AND confidence <= 100),
    priority INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- App configuration table
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(post_date);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_name);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_review ON transactions(needs_review) WHERE needs_review = 1;
CREATE INDEX IF NOT EXISTS idx_rules_active ON categorize_rules(active, priority DESC);
CREATE INDEX IF NOT EXISTS idx_budgets_year ON budgets(year);

-- View: Transaction summary with category names
CREATE VIEW IF NOT EXISTS v_transaction_summary AS
SELECT
    t.id,
    t.account_name,
    t.post_date,
    t.description,
    t.debit,
    t.credit,
    c.name as category,
    c.type as category_type,
    ac.name as auto_category,
    t.confidence,
    t.needs_review
FROM transactions t
LEFT JOIN categories c ON t.category_id = c.id
LEFT JOIN categories ac ON t.auto_category_id = ac.id
ORDER BY t.post_date DESC;

-- View: Budget status with YTD calculations
CREATE VIEW IF NOT EXISTS v_budget_summary AS
SELECT
    b.year,
    c.id as category_id,
    c.name as category,
    c.type as category_type,
    b.annual_amount,
    COALESCE(b.timing, c.timing) as timing
FROM budgets b
JOIN categories c ON b.category_id = c.id
WHERE c.active = 1;

-- View: Dues status by unit
CREATE VIEW IF NOT EXISTS v_unit_summary AS
SELECT
    u.id,
    u.number as unit,
    u.ownership_pct
FROM units u
ORDER BY u.number;
