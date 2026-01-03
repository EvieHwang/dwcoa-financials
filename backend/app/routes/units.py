"""Unit management routes."""

import json

from app.services import database


def handle_get_units() -> dict:
    """Get all units.

    Returns:
        Response with units list
    """
    units = database.get_units()
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'units': database.rows_to_dicts(units)})
    }


def handle_update_unit(unit_number: str, body: dict) -> dict:
    """Update a unit's past due balance.

    Args:
        unit_number: Unit number (e.g., '101')
        body: Request body with past_due_balance

    Returns:
        Response with updated unit
    """
    if 'past_due_balance' not in body:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'past_due_balance is required'})
        }

    try:
        past_due_balance = float(body['past_due_balance'])
    except (ValueError, TypeError):
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'past_due_balance must be a number'})
        }

    if past_due_balance < 0:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'past_due_balance cannot be negative'})
        }

    unit = database.update_unit(unit_number, past_due_balance)
    if not unit:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'not_found', 'message': f'Unit {unit_number} not found'})
        }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(unit)
    }
