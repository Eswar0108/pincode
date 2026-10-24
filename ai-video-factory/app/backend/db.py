"""Database module — SQLite connection and schema initialization."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "factory.sqlite"
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with WAL mode and row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables from schema.sql if they don't exist."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
    schema_sql = SCHEMA_PATH.read_text()
    with get_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()


def dict_from_row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return {key: row[key] for key in row.keys()}