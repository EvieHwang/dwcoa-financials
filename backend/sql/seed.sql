-- DWCOA Financial Tracker Seed Data
-- Initial data for categories, accounts, units, and 2025 budgets

-- Account mappings
INSERT OR IGNORE INTO accounts (masked_number, name) VALUES
('****7145', 'Savings'),
('****9242', 'Checking'),
('****9226', 'Reserve Fund');

-- Categories: Income (Dues)
INSERT OR IGNORE INTO categories (name, type, default_account, timing) VALUES
('Dues 101', 'Income', 'Savings', 'monthly'),
('Dues 102', 'Income', 'Savings', 'monthly'),
('Dues 103', 'Income', 'Savings', 'monthly'),
('Dues 201', 'Income', 'Savings', 'monthly'),
('Dues 202', 'Income', 'Savings', 'monthly'),
('Dues 203', 'Income', 'Savings', 'monthly'),
('Dues 301', 'Income', 'Savings', 'monthly'),
('Dues 302', 'Income', 'Savings', 'monthly'),
('Dues 303', 'Income', 'Savings', 'monthly'),
('Interest income', 'Income', 'Any', 'monthly');

-- Categories: Expenses
INSERT OR IGNORE INTO categories (name, type, default_account, timing) VALUES
('Bulger Safe & Lock', 'Expense', 'Checking', 'annual'),
('Cintas Fire Protection', 'Expense', 'Checking', 'annual'),
('Common Area Cleaning', 'Expense', 'Checking', 'monthly'),
('Fire Alarm', 'Expense', 'Checking', 'monthly'),
('Grounds/Landscaping', 'Expense', 'Checking', 'monthly'),
('Homeowners Club Dues', 'Expense', 'Checking', 'annual'),
('Insurance Premiums', 'Expense', 'Checking', 'monthly'),
('Seattle City Light', 'Expense', 'Checking', 'monthly'),
('Other', 'Expense', 'Checking', 'annual'),
('Reserve Contribution', 'Transfer', 'Savings', 'monthly'),
('Reserve Expenses', 'Expense', 'Reserve Fund', 'annual'),
('Transfers', 'Internal', 'Any', 'annual');

-- Unit ownership percentages
INSERT OR IGNORE INTO units (number, ownership_pct) VALUES
('101', 0.117),
('102', 0.104),
('103', 0.112),
('201', 0.117),
('202', 0.104),
('203', 0.112),
('301', 0.117),
('302', 0.104),
('303', 0.112);

-- 2025 Budget: Income
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5954.75 FROM categories WHERE name = 'Dues 101';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5293.11 FROM categories WHERE name = 'Dues 102';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5700.27 FROM categories WHERE name = 'Dues 103';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5954.75 FROM categories WHERE name = 'Dues 201';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5293.11 FROM categories WHERE name = 'Dues 202';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5700.27 FROM categories WHERE name = 'Dues 203';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5954.75 FROM categories WHERE name = 'Dues 301';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5293.11 FROM categories WHERE name = 'Dues 302';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5700.27 FROM categories WHERE name = 'Dues 303';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 26.00 FROM categories WHERE name = 'Interest income';

-- 2025 Budget: Expenses
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 18000.00 FROM categories WHERE name = 'Reserve Contribution';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 400.00 FROM categories WHERE name = 'Bulger Safe & Lock';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 1500.00 FROM categories WHERE name = 'Cintas Fire Protection';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 2700.00 FROM categories WHERE name = 'Common Area Cleaning';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 3300.00 FROM categories WHERE name = 'Fire Alarm';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 12000.00 FROM categories WHERE name = 'Grounds/Landscaping';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 7500.00 FROM categories WHERE name = 'Other';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 4500.00 FROM categories WHERE name = 'Insurance Premiums';
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 6000.00 FROM categories WHERE name = 'Seattle City Light';

-- 2026 Budget (copy of 2025 for current year)
INSERT OR IGNORE INTO budgets (year, category_id, annual_amount)
SELECT 2026, category_id, annual_amount FROM budgets WHERE year = 2025;

-- App configuration
INSERT OR IGNORE INTO app_config (key, value) VALUES
('last_upload_at', ''),
('current_year', '2026');
