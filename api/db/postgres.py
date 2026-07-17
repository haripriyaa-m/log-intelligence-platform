import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "loguser"),
        password=os.getenv("POSTGRES_PASSWORD", "logpass"),
        dbname=os.getenv("POSTGRES_DB", "logdb"),
    )
    conn.autocommit = True
    return conn


def fetch_all(query: str, params=None) -> list[dict]:
    """Runs a SELECT and returns all rows as a list of dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, params=None) -> dict | None:
    """Runs a SELECT and returns one row as a dict, or None."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or ())
            row = cur.fetchone()
            return dict(row) if row else None