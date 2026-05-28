"""
ingestion/load_raw.py
---------------------
Reads the raw CSV files from /data/raw/ and loads them into the
`trading` PostgreSQL database under the `raw` schema.

This is the first step of the pipeline — idempotent (TRUNCATE + reload).
"""

import csv
import os
import sys
from pathlib import Path

import psycopg2

# ─── Config ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "TRADING_DB_CONN",
    "postgresql://trading:trading@localhost:5432/trading",
)
DATA_DIR = Path(os.environ.get("DATA_DIR", "/opt/airflow/data/raw"))

# ─── DDL ─────────────────────────────────────────────────────────────────────
DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.raw_users (
    user_id             VARCHAR(20),
    name                VARCHAR(100),
    email               VARCHAR(150),
    country             VARCHAR(10),
    account_type        VARCHAR(20),
    risk_profile        VARCHAR(20),
    created_at          TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.raw_instruments (
    instrument_id       VARCHAR(20),
    symbol              VARCHAR(20),
    name                VARCHAR(100),
    instrument_type     VARCHAR(20),
    currency            VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS raw.raw_trades (
    trade_id            VARCHAR(20),
    user_id             VARCHAR(20),
    instrument_id       VARCHAR(20),
    trade_type          VARCHAR(10),
    quantity            NUMERIC(18, 8),
    price               NUMERIC(18, 8),
    trade_timestamp     TIMESTAMP,
    status              VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS raw.raw_transactions (
    transaction_id      VARCHAR(20),
    user_id             VARCHAR(20),
    trade_id            VARCHAR(20),
    amount              NUMERIC(18, 2),
    fee                 NUMERIC(18, 2),
    transaction_type    VARCHAR(30),
    transaction_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.raw_risk_events (
    event_id            VARCHAR(20),
    user_id             VARCHAR(20),
    trade_id            VARCHAR(20),
    event_type          VARCHAR(50),
    severity            VARCHAR(20),
    event_timestamp     TIMESTAMP,
    description         TEXT
);
"""

TRUNCATE_SQL = """
TRUNCATE TABLE
    raw.raw_users,
    raw.raw_instruments,
    raw.raw_trades,
    raw.raw_transactions,
    raw.raw_risk_events;
"""

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(DATABASE_URL)


def create_schema(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()
    print("[ingestion] Schema and tables ensured.")


def truncate_tables(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(TRUNCATE_SQL)
    conn.commit()
    print("[ingestion] Raw tables truncated.")


def load_csv(
    conn: psycopg2.extensions.connection,
    table: str,
    filepath: Path,
) -> None:
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    if not rows:
        print(f"[ingestion] {filepath.name} – no rows, skipping.")
        return

    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    cols_sql = ", ".join(columns)
    insert_sql = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})"

    with conn.cursor() as cur:
        for row in rows:
            values = [
                row[col] if row[col] not in ("", None) else None
                for col in columns
            ]
            cur.execute(insert_sql, values)

    conn.commit()
    print(f"[ingestion] {table} ← {len(rows)} rows from {filepath.name}")


# ─── Main ────────────────────────────────────────────────────────────────────

TABLE_MAP = {
    "raw.raw_users":        DATA_DIR / "users.csv",
    "raw.raw_instruments":  DATA_DIR / "instruments.csv",
    "raw.raw_trades":       DATA_DIR / "trades.csv",
    "raw.raw_transactions": DATA_DIR / "transactions.csv",
    "raw.raw_risk_events":  DATA_DIR / "risk_events.csv",
}


def main() -> None:
    print(f"[ingestion] Connecting to {DATABASE_URL.split('@')[-1]}")
    conn = get_connection()

    try:
        create_schema(conn)
        truncate_tables(conn)

        for table, filepath in TABLE_MAP.items():
            if not filepath.exists():
                print(f"[ingestion] WARNING: {filepath} not found – skipping.")
                continue
            load_csv(conn, table, filepath)

        print("[ingestion] ✓ Ingestion complete.")
    except Exception as exc:
        conn.rollback()
        print(f"[ingestion] ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
