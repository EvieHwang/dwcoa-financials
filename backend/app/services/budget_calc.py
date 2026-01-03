"""Budget calculation service."""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.services import database


def calculate_ytd_budget(annual_amount: float, timing: str, as_of_date: date) -> float:
    """Calculate YTD budget based on timing pattern.

    Args:
        annual_amount: Annual budget amount
        timing: Timing pattern ('monthly', 'quarterly', 'annual')
        as_of_date: Date to calculate as of

    Returns:
        YTD budget amount
    """
    month = as_of_date.month

    if timing == 'monthly':
        # Monthly: (annual / 12) * months elapsed
        return (annual_amount / 12) * month

    elif timing == 'quarterly':
        # Quarterly: (annual / 4) * quarters completed
        # Q1 = months 1-3, Q2 = months 4-6, etc.
        quarters_complete = (month - 1) // 3
        return (annual_amount / 4) * quarters_complete

    elif timing == 'annual':
        # Annual: full amount available all year (expense could hit any time)
        return annual_amount

    # Default to annual
    return annual_amount


def get_ytd_actuals(year: int) -> Dict[int, float]:
    """Get YTD actual amounts by category for budget comparison.

    NOTE: This ONLY includes Income and Expense categories.
    Transfers (type='Transfer' and type='Internal') are intentionally excluded
    because they are not income or expenses - they just move money between accounts.
    Transfers DO affect account balances (handled by get_account_balances()),
    but should NOT appear in income/expense budget summaries.

    Args:
        year: Year to calculate

    Returns:
        Dict mapping category_id to actual amount (Income and Expense only)
    """
    # Income = credits, Expenses = debits
    # Transfers excluded - they're not income or expenses
    sql = """
        SELECT
            t.category_id,
            c.type,
            SUM(CASE WHEN c.type = 'Income' THEN t.credit ELSE t.debit END) as amount
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE strftime('%Y', t.post_date) = ?
        AND t.category_id IS NOT NULL
        AND c.type IN ('Income', 'Expense')
        GROUP BY t.category_id
    """
    rows = database.fetch_all(sql, (str(year),))

    return {row['category_id']: row['amount'] or 0 for row in rows}


def get_budget_summary(year: int, as_of_date: Optional[date] = None) -> dict:
    """Get complete budget summary for dashboard.

    Args:
        year: Budget year
        as_of_date: Date to calculate YTD (defaults to today)

    Returns:
        Dict with income_summary, expense_summary, and category details
    """
    if as_of_date is None:
        as_of_date = date.today()

    # Get budgets
    budgets = database.get_budgets(year)

    # Get actuals
    actuals = get_ytd_actuals(year)

    # Process income
    income_categories = []
    income_ytd_budget = 0
    income_ytd_actual = 0

    # Process expenses
    expense_categories = []
    expense_ytd_budget = 0
    expense_ytd_actual = 0

    for budget in budgets:
        cat_type = budget['category_type']
        timing = budget.get('effective_timing', 'monthly')
        annual = budget['annual_amount'] or 0
        category_id = budget['category_id']

        ytd_budget = calculate_ytd_budget(annual, timing, as_of_date)
        ytd_actual = actuals.get(category_id, 0)
        remaining = ytd_budget - ytd_actual

        cat_data = {
            'id': category_id,
            'category': budget['category_name'],
            'type': cat_type,
            'timing': timing,
            'annual_amount': annual,
            'ytd_budget': round(ytd_budget, 2),
            'ytd_actual': round(ytd_actual, 2),
            'remaining': round(remaining, 2)
        }

        if cat_type == 'Income':
            income_categories.append(cat_data)
            income_ytd_budget += ytd_budget
            income_ytd_actual += ytd_actual
        elif cat_type == 'Expense':
            expense_categories.append(cat_data)
            expense_ytd_budget += ytd_budget
            expense_ytd_actual += ytd_actual

    return {
        'year': year,
        'as_of_date': as_of_date.isoformat(),
        'income_summary': {
            'ytd_budget': round(income_ytd_budget, 2),
            'ytd_actual': round(income_ytd_actual, 2),
            'categories': income_categories
        },
        'expense_summary': {
            'ytd_budget': round(expense_ytd_budget, 2),
            'ytd_actual': round(expense_ytd_actual, 2),
            'remaining': round(expense_ytd_budget - expense_ytd_actual, 2),
            'categories': expense_categories
        }
    }


def get_account_balances() -> List[dict]:
    """Get current balance for each account.

    NOTE: Account balances include ALL transactions (including transfers).
    We use the balance column from the CSV which the bank calculates,
    not a calculated sum of debits/credits. This ensures transfers
    between accounts are properly reflected in each account's balance.

    Returns:
        List of account dicts with name and balance
    """
    # Get most recent balance for each account by date (and id as tiebreaker)
    # No category filtering - all transactions affect account balances
    sql = """
        SELECT t.account_name as name, t.balance
        FROM transactions t
        INNER JOIN (
            SELECT account_name, MAX(post_date) as max_date
            FROM transactions
            GROUP BY account_name
        ) latest ON t.account_name = latest.account_name
                 AND t.post_date = latest.max_date
        WHERE t.id = (
            SELECT MAX(id) FROM transactions t2
            WHERE t2.account_name = t.account_name
            AND t2.post_date = latest.max_date
        )
        ORDER BY t.account_name
    """
    rows = database.fetch_all(sql)

    balances = []
    for row in rows:
        balances.append({
            'name': row['name'],
            'balance': row['balance'] or 0
        })

    return balances


def get_total_cash() -> float:
    """Get total cash across all accounts.

    Returns:
        Sum of all account balances
    """
    balances = get_account_balances()
    return sum(b['balance'] for b in balances)
