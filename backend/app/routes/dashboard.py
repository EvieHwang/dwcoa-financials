"""Dashboard routes."""

import json
from datetime import date
from typing import Optional

from app.services import database, budget_calc
from app.routes import dues


def handle_get_dashboard(year: Optional[int] = None) -> dict:
    """Get dashboard data.

    Args:
        year: Budget year (defaults to current year)

    Returns:
        Response with complete dashboard data
    """
    # Default to current year
    if not year:
        current_year = database.get_config('current_year')
        year = int(current_year) if current_year else date.today().year

    # Get last upload timestamp
    last_updated = database.get_config('last_upload_at')

    # Get account balances
    accounts = budget_calc.get_account_balances()
    total_cash = sum(a['balance'] for a in accounts)

    # Get budget summary
    budget_summary = budget_calc.get_budget_summary(year)

    # Get dues status
    dues_data = dues.get_dues_status(year)

    # Get review count
    review_row = database.fetch_one(
        "SELECT COUNT(*) as count FROM transactions WHERE needs_review = 1"
    )
    review_count = review_row['count'] if review_row else 0

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'last_updated': last_updated or None,
            'year': year,
            'accounts': accounts,
            'total_cash': round(total_cash, 2),
            'income_summary': budget_summary['income_summary'],
            'expense_summary': budget_summary['expense_summary'],
            'dues_status': dues_data['units'],
            'review_count': review_count
        })
    }
