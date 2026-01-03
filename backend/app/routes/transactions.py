"""Transaction routes."""

import base64
import json
from datetime import datetime
from typing import Any

from app.services import database, csv_processor, categorizer


def handle_list_transactions(query: dict) -> dict:
    """List transactions with optional filters.

    Args:
        query: Query parameters (year, account, category_id, needs_review, limit, offset)

    Returns:
        Response with transaction list
    """
    # Build query
    sql = """
        SELECT t.*,
               c.name as category,
               c.type as category_type,
               ac.name as auto_category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories ac ON t.auto_category_id = ac.id
        WHERE 1=1
    """
    params: list = []

    # Apply filters
    if query.get('year'):
        sql += " AND strftime('%Y', t.post_date) = ?"
        params.append(str(query['year']))

    if query.get('account'):
        sql += " AND t.account_name = ?"
        params.append(query['account'])

    if query.get('category_id'):
        sql += " AND t.category_id = ?"
        params.append(int(query['category_id']))

    if query.get('needs_review') == 'true':
        sql += " AND t.needs_review = 1"

    # Count total
    count_sql = sql.replace("SELECT t.*,", "SELECT COUNT(*) as count")
    count_sql = count_sql.split("FROM")[0] + "SELECT COUNT(*) as count FROM" + count_sql.split("FROM", 1)[1]
    # Simplified: just count
    count_row = database.fetch_one(
        f"SELECT COUNT(*) as count FROM transactions t WHERE 1=1" +
        sql.split("WHERE 1=1")[1].split("ORDER BY")[0] if "ORDER BY" in sql else sql.split("WHERE 1=1")[1],
        tuple(params)
    )
    total = count_row['count'] if count_row else 0

    # Add ordering and pagination
    sql += " ORDER BY t.post_date DESC, t.id DESC"

    limit = int(query.get('limit', 100))
    offset = int(query.get('offset', 0))
    sql += f" LIMIT {limit} OFFSET {offset}"

    rows = database.fetch_all(sql, tuple(params))
    transactions = database.rows_to_dicts(rows)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'transactions': transactions,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    }


def handle_upload(event_body: dict, raw_body: str = '') -> dict:
    """Handle CSV file upload.

    Args:
        event_body: Parsed request body
        raw_body: Raw body for multipart handling

    Returns:
        Response with upload stats
    """
    try:
        # Get CSV content
        # In Lambda, file may come as base64 or direct content
        csv_content = None

        if 'file' in event_body:
            # Direct file content
            csv_content = event_body['file']
        elif 'body' in event_body:
            # Base64 encoded
            try:
                csv_content = base64.b64decode(event_body['body']).decode('utf-8')
            except Exception:
                csv_content = event_body['body']
        elif raw_body:
            # Try to extract from multipart or use directly
            if 'Content-Disposition' in raw_body:
                # Multipart - extract content after headers
                parts = raw_body.split('\r\n\r\n', 1)
                if len(parts) > 1:
                    csv_content = parts[1].rsplit('\r\n--', 1)[0]
            else:
                csv_content = raw_body
        elif isinstance(event_body, str):
            csv_content = event_body

        if not csv_content:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': 'No file content provided'})
            }

        # Parse CSV
        result = csv_processor.parse_csv(csv_content)

        if result.errors:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'bad_request',
                    'message': 'CSV parsing errors',
                    'errors': result.errors
                })
            }

        # Process transactions
        with database.transaction() as conn:
            # Clear existing transactions
            conn.execute("DELETE FROM transactions")

            # Get category mapping for pre-categorized items
            categories = {c['name']: c['id'] for c in database.get_categories()}

            # Stats
            stats = {
                'total_rows': len(result.transactions),
                'categorized': 0,
                'needs_review': 0,
                'uncategorized': 0
            }

            # Prepare transactions for categorization
            txn_dicts = []
            for txn in result.transactions:
                txn_dicts.append({
                    'account_number': txn.account_number,
                    'account_name': txn.account_name,
                    'post_date': txn.post_date,
                    'check_number': txn.check_number,
                    'description': txn.description,
                    'debit': txn.debit,
                    'credit': txn.credit,
                    'status': txn.status,
                    'balance': txn.balance,
                    'existing_category': txn.category
                })

            # Categorize transactions
            for txn in txn_dicts:
                category_id = None
                auto_category_id = None
                confidence = None
                needs_review = False

                # Check for pre-existing category
                if txn['existing_category'] and txn['existing_category'] in categories:
                    category_id = categories[txn['existing_category']]
                    confidence = 100
                    stats['categorized'] += 1
                else:
                    # Auto-categorize
                    cat_result = categorizer.categorize_transaction(
                        txn['description'],
                        txn['account_name']
                    )
                    auto_category_id = cat_result.category_id
                    confidence = cat_result.confidence
                    needs_review = cat_result.needs_review

                    if cat_result.category_id and not cat_result.needs_review:
                        category_id = cat_result.category_id
                        stats['categorized'] += 1
                    elif cat_result.needs_review:
                        stats['needs_review'] += 1
                    else:
                        stats['uncategorized'] += 1

                # Insert transaction
                conn.execute("""
                    INSERT INTO transactions (
                        account_number, account_name, post_date, check_number,
                        description, debit, credit, status, balance,
                        category_id, auto_category_id, confidence, needs_review
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    txn['account_number'],
                    txn['account_name'],
                    txn['post_date'],
                    txn['check_number'],
                    txn['description'],
                    txn['debit'],
                    txn['credit'],
                    txn['status'],
                    txn['balance'],
                    category_id,
                    auto_category_id,
                    confidence,
                    1 if needs_review else 0
                ))

            # Update last upload timestamp
            database.set_config('last_upload_at', datetime.now().isoformat())

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Upload successful',
                'stats': stats,
                'warnings': result.warnings[:10]  # Limit warnings in response
            })
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'internal_error', 'message': str(e)})
        }


def handle_download(query: dict) -> dict:
    """Download transactions as CSV.

    Args:
        query: Query parameters (year optional)

    Returns:
        Response with CSV content
    """
    sql = """
        SELECT t.*,
               c.name as category,
               ac.name as auto_category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories ac ON t.auto_category_id = ac.id
        WHERE 1=1
    """
    params: list = []

    if query.get('year'):
        sql += " AND strftime('%Y', t.post_date) = ?"
        params.append(str(query['year']))

    sql += " ORDER BY t.post_date DESC, t.id DESC"

    rows = database.fetch_all(sql, tuple(params))
    transactions = database.rows_to_dicts(rows)

    csv_content = csv_processor.generate_csv(transactions, include_app_columns=True)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename="dwcoa_transactions.csv"'
        },
        'body': csv_content
    }


def handle_update(transaction_id: int, body: dict) -> dict:
    """Update a transaction's category.

    Args:
        transaction_id: Transaction ID
        body: Request body with category_id and/or needs_review

    Returns:
        Response with updated transaction
    """
    # Verify transaction exists
    txn = database.fetch_one("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    if not txn:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'not_found', 'message': 'Transaction not found'})
        }

    # Build update
    updates = []
    params: list = []

    if 'category_id' in body:
        updates.append("category_id = ?")
        params.append(body['category_id'])

        # Learn pattern if manually categorized
        if body['category_id']:
            categorizer.learn_pattern(txn['description'], body['category_id'])

    if 'needs_review' in body:
        updates.append("needs_review = ?")
        params.append(1 if body['needs_review'] else 0)
    elif 'category_id' in body and body['category_id']:
        # Clear needs_review when category is set
        updates.append("needs_review = 0")

    updates.append("updated_at = datetime('now')")

    if updates:
        params.append(transaction_id)
        with database.transaction():
            database.execute(
                f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

    # Fetch updated transaction
    updated = database.fetch_one("""
        SELECT t.*,
               c.name as category,
               ac.name as auto_category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories ac ON t.auto_category_id = ac.id
        WHERE t.id = ?
    """, (transaction_id,))

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(database.row_to_dict(updated))
    }


def handle_review_queue() -> dict:
    """Get transactions needing review.

    Returns:
        Response with transactions needing review
    """
    rows = database.fetch_all("""
        SELECT t.*,
               c.name as category,
               ac.name as auto_category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories ac ON t.auto_category_id = ac.id
        WHERE t.needs_review = 1
        ORDER BY t.post_date DESC
        LIMIT 100
    """)

    transactions = database.rows_to_dicts(rows)
    count = database.fetch_one("SELECT COUNT(*) as count FROM transactions WHERE needs_review = 1")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'transactions': transactions,
            'count': count['count'] if count else 0
        })
    }
