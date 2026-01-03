"""Budget management routes."""

import json
from typing import Any

from app.services import database


def handle_list(year: int) -> dict:
    """List all budgets for a year.

    Args:
        year: Budget year

    Returns:
        Response with budget list including transaction counts
    """
    budgets = database.get_budgets(year)

    # Add transaction count for each category
    for budget in budgets:
        count_row = database.fetch_one(
            "SELECT COUNT(*) as count FROM transactions WHERE category_id = ?",
            (budget['category_id'],)
        )
        budget['transaction_count'] = count_row['count'] if count_row else 0

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'year': year,
            'budgets': budgets
        })
    }


def handle_upsert(body: dict) -> dict:
    """Create or update a budget entry.

    Args:
        body: Budget data (year, category_id, annual_amount, timing)

    Returns:
        Response with budget entry
    """
    required = ['year', 'category_id', 'annual_amount']
    for field in required:
        if body.get(field) is None:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': f'{field} is required'})
            }

    year = int(body['year'])
    category_id = int(body['category_id'])
    annual_amount = float(body['annual_amount'])
    timing = body.get('timing')  # Optional override

    # Verify category exists
    category = database.get_category_by_id(category_id)
    if not category:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'Category not found'})
        }

    # Upsert budget
    with database.transaction():
        database.execute("""
            INSERT INTO budgets (year, category_id, annual_amount, timing)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(year, category_id) DO UPDATE SET
                annual_amount = excluded.annual_amount,
                timing = excluded.timing
        """, (year, category_id, annual_amount, timing))

    # Fetch the budget entry
    row = database.fetch_one("""
        SELECT b.*, c.name as category_name, c.type as category_type,
               COALESCE(b.timing, c.timing) as effective_timing
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.year = ? AND b.category_id = ?
    """, (year, category_id))

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(database.row_to_dict(row))
    }


def handle_copy(body: dict) -> dict:
    """Copy budgets from one year to another.

    Args:
        body: Copy parameters (from_year, to_year)

    Returns:
        Response with count of copied budgets
    """
    from_year = body.get('from_year')
    to_year = body.get('to_year')

    if not from_year or not to_year:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'from_year and to_year are required'})
        }

    from_year = int(from_year)
    to_year = int(to_year)

    if from_year == to_year:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'from_year and to_year must be different'})
        }

    # Check source budgets exist
    source_budgets = database.get_budgets(from_year)
    if not source_budgets:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': f'No budgets found for {from_year}'})
        }

    # Copy budgets
    with database.transaction():
        database.execute("""
            INSERT OR REPLACE INTO budgets (year, category_id, annual_amount, timing)
            SELECT ?, category_id, annual_amount, timing
            FROM budgets
            WHERE year = ?
        """, (to_year, from_year))

    # Count copied
    count_row = database.fetch_one(
        "SELECT COUNT(*) as count FROM budgets WHERE year = ?",
        (to_year,)
    )
    count = count_row['count'] if count_row else 0

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': f'Copied {count} budgets from {from_year} to {to_year}',
            'count': count
        })
    }
