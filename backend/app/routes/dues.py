"""Dues tracking routes."""

import json
from datetime import date
from typing import Optional

from app.services import database


def get_dues_status(year: Optional[int] = None, as_of_date: Optional[date] = None) -> dict:
    """Calculate dues status for all units as of a specific date.

    Args:
        year: Budget year (defaults to current year)
        as_of_date: Only include payments on or before this date

    Returns:
        Dict with year, total_budget, and units list
    """
    if not year:
        current_year = database.get_config('current_year')
        year = int(current_year) if current_year else date.today().year

    if as_of_date is None:
        as_of_date = date.today()

    # Get total expense budget (this is the annual amount, not date-filtered)
    budget_row = database.fetch_one("""
        SELECT SUM(b.annual_amount) as total
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.year = ? AND c.type = 'Expense'
    """, (year,))
    total_budget = budget_row['total'] or 0 if budget_row else 0

    # Get units
    units = database.get_units()

    # Get dues payments by unit through as_of_date
    dues_sql = """
        SELECT c.name as category, SUM(t.credit) as paid
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name LIKE 'Dues %'
        AND strftime('%Y', t.post_date) = ?
        AND t.post_date <= ?
        GROUP BY c.name
    """
    dues_rows = database.fetch_all(dues_sql, (str(year), as_of_date.isoformat()))
    dues_by_unit = {}
    for row in dues_rows:
        # Extract unit number from "Dues XXX"
        unit_num = row['category'].replace('Dues ', '')
        dues_by_unit[unit_num] = row['paid'] or 0

    # Calculate status for each unit
    unit_status = []
    for unit in units:
        expected = total_budget * unit['ownership_pct']
        paid = dues_by_unit.get(unit['number'], 0)
        outstanding = expected - paid

        unit_status.append({
            'unit': unit['number'],
            'ownership_pct': unit['ownership_pct'],
            'expected_annual': round(expected, 2),
            'paid_ytd': round(paid, 2),
            'outstanding': round(outstanding, 2)
        })

    return {
        'year': year,
        'total_budget': round(total_budget, 2),
        'units': unit_status
    }


def handle_get_dues(year: Optional[int] = None) -> dict:
    """Handle GET /api/dues request.

    Args:
        year: Budget year

    Returns:
        Response with dues status
    """
    data = get_dues_status(year)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data)
    }
