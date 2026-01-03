"""Database service for SQLite operations."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Optional

from app.utils import s3

# Database file locations
DB_KEY = 'dwcoa.db'
_db_connection: Optional[sqlite3.Connection] = None
_db_path: Optional[str] = None


def get_sql_path(filename: str) -> str:
    """Get path to SQL file in package."""
    # When running in Lambda, files are in /var/task
    base_path = Path(__file__).parent.parent.parent / 'sql'
    return str(base_path / filename)


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database with schema and seed data.

    Args:
        conn: SQLite connection
    """
    # Run schema
    with open(get_sql_path('schema.sql'), 'r') as f:
        conn.executescript(f.read())

    # Run seed data
    with open(get_sql_path('seed.sql'), 'r') as f:
        conn.executescript(f.read())

    # Run categorization rules
    with open(get_sql_path('rules.sql'), 'r') as f:
        conn.executescript(f.read())

    conn.commit()


def get_connection() -> sqlite3.Connection:
    """Get database connection, downloading from S3 if needed.

    Returns:
        SQLite connection with row factory set
    """
    global _db_connection, _db_path

    if _db_connection is not None:
        return _db_connection

    # Download database from S3 or create new
    _db_path = s3.get_temp_path('dwcoa.db')

    if s3.file_exists(DB_KEY):
        s3.download_file(DB_KEY, _db_path)
        _db_connection = sqlite3.connect(_db_path)
        _db_connection.row_factory = sqlite3.Row
    else:
        # Create new database
        _db_connection = sqlite3.connect(_db_path)
        _db_connection.row_factory = sqlite3.Row
        init_db(_db_connection)
        # Upload initial database
        save_db()

    return _db_connection


def save_db() -> None:
    """Save database to S3."""
    global _db_connection, _db_path

    if _db_connection is not None and _db_path is not None:
        _db_connection.commit()
        s3.upload_file(_db_path, DB_KEY)


def close_db() -> None:
    """Close database connection."""
    global _db_connection, _db_path

    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
        _db_path = None


@contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions.

    Yields:
        SQLite connection

    Commits on success, rolls back on exception, saves to S3.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
        save_db()
    except Exception:
        conn.rollback()
        raise


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Execute SQL and return cursor.

    Args:
        sql: SQL statement
        params: Query parameters

    Returns:
        Cursor with results
    """
    conn = get_connection()
    return conn.execute(sql, params)


def execute_many(sql: str, params_list: List[tuple]) -> None:
    """Execute SQL with multiple parameter sets.

    Args:
        sql: SQL statement
        params_list: List of parameter tuples
    """
    conn = get_connection()
    conn.executemany(sql, params_list)


def fetch_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """Fetch a single row.

    Args:
        sql: SQL query
        params: Query parameters

    Returns:
        Row or None
    """
    cursor = execute(sql, params)
    return cursor.fetchone()


def fetch_all(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    """Fetch all rows.

    Args:
        sql: SQL query
        params: Query parameters

    Returns:
        List of rows
    """
    cursor = execute(sql, params)
    return cursor.fetchall()


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict]:
    """Convert a Row to a dict.

    Args:
        row: SQLite Row object

    Returns:
        Dict or None
    """
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: List[sqlite3.Row]) -> List[dict]:
    """Convert Rows to list of dicts.

    Args:
        rows: List of SQLite Row objects

    Returns:
        List of dicts
    """
    return [dict(row) for row in rows]


# Convenience functions for common queries

def get_categories(active_only: bool = True, category_type: Optional[str] = None) -> List[dict]:
    """Get all categories.

    Args:
        active_only: Only return active categories
        category_type: Filter by type (Income, Expense, Transfer, Internal)

    Returns:
        List of category dicts
    """
    sql = "SELECT * FROM categories WHERE 1=1"
    params: List[Any] = []

    if active_only:
        sql += " AND active = 1"

    if category_type:
        sql += " AND type = ?"
        params.append(category_type)

    sql += " ORDER BY type, name"
    return rows_to_dicts(fetch_all(sql, tuple(params)))


def get_category_by_id(category_id: int) -> Optional[dict]:
    """Get a category by ID."""
    return row_to_dict(fetch_one("SELECT * FROM categories WHERE id = ?", (category_id,)))


def get_category_by_name(name: str) -> Optional[dict]:
    """Get a category by name."""
    return row_to_dict(fetch_one("SELECT * FROM categories WHERE name = ?", (name,)))


def get_accounts() -> List[dict]:
    """Get all account mappings."""
    return rows_to_dicts(fetch_all("SELECT * FROM accounts ORDER BY name"))


def get_account_name(masked_number: str) -> Optional[str]:
    """Get friendly account name from masked number."""
    row = fetch_one("SELECT name FROM accounts WHERE masked_number = ?", (masked_number,))
    return row['name'] if row else None


def get_units() -> List[dict]:
    """Get all units with ownership percentages."""
    return rows_to_dicts(fetch_all("SELECT * FROM units ORDER BY number"))


def get_budgets(year: int) -> List[dict]:
    """Get all active categories with their budgets for a year.

    Returns ALL active categories, not just ones with existing budgets.
    Categories without a budget entry will show annual_amount=0.
    """
    sql = """
        SELECT
            c.id as category_id,
            c.name as category_name,
            c.type as category_type,
            COALESCE(b.annual_amount, 0) as annual_amount,
            COALESCE(b.timing, c.timing) as effective_timing,
            b.id as budget_id,
            ? as year
        FROM categories c
        LEFT JOIN budgets b ON b.category_id = c.id AND b.year = ?
        WHERE c.active = 1
        ORDER BY c.type, c.name
    """
    return rows_to_dicts(fetch_all(sql, (year, year)))


def get_config(key: str) -> Optional[str]:
    """Get a config value."""
    row = fetch_one("SELECT value FROM app_config WHERE key = ?", (key,))
    return row['value'] if row else None


def set_config(key: str, value: str) -> None:
    """Set a config value."""
    execute(
        "INSERT OR REPLACE INTO app_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value)
    )


def get_categorize_rules() -> List[dict]:
    """Get all active categorization rules, ordered by priority."""
    sql = """
        SELECT r.*, c.name as category_name
        FROM categorize_rules r
        JOIN categories c ON r.category_id = c.id
        WHERE r.active = 1
        ORDER BY r.priority DESC, r.id
    """
    return rows_to_dicts(fetch_all(sql))
