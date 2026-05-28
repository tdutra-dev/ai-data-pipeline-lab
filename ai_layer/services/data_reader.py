"""
services/data_reader.py
──────────────────────────────────────────────────────────────────────────────
Reads production mart tables from the trading PostgreSQL database.
Returns structured Python dicts ready for OpenAI prompt construction.

Handles gracefully:
  • Missing schema / tables (dbt hasn't run yet)
  • Connection failures
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://trading:trading@postgres:5432/trading",
)


def _get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(DATABASE_URL)


def _query(conn: psycopg2.extensions.connection, sql: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        return [dict(row) for row in cur.fetchall()]


def read_mart_data() -> dict[str, Any]:
    """
    Reads from the two production mart tables and returns a summary dict.
    Returns empty lists if the tables do not yet exist (before first dbt run).
    """
    try:
        conn = _get_connection()
        conn.autocommit = True

        customer_activity = _query(
            conn,
            """
            SELECT
                user_id, name, country, account_type, risk_profile,
                total_trades, total_notional, avg_trade_size,
                net_pnl_estimate, total_fees_paid,
                customer_segment,
                total_risk_events, high_risk_events,
                trading_days_span
            FROM marts.mart_customer_activity
            ORDER BY total_notional DESC
            LIMIT 10
            """,
        )

        risk_signals = _query(
            conn,
            """
            SELECT
                user_id, name, country, risk_profile,
                total_risk_events, high_severity_events,
                compliance_flags, rapid_trading_flags,
                concentration_risk_flags,
                risk_tier, risk_score,
                last_risk_event_at,
                user_total_notional
            FROM marts.mart_risk_signals
            ORDER BY risk_score DESC
            """,
        )

        volume_summary = _query(
            conn,
            """
            SELECT
                symbol, instrument_type,
                sum(total_trades)   AS total_trades,
                sum(total_notional) AS total_notional,
                avg(avg_price)      AS avg_price
            FROM intermediate.int_trading_volume
            GROUP BY symbol, instrument_type
            ORDER BY total_notional DESC
            LIMIT 5
            """,
        )

        conn.close()

        return {
            "customer_activity": customer_activity,
            "risk_signals": risk_signals,
            "volume_summary": volume_summary,
        }

    except psycopg2.errors.UndefinedTable:
        logger.warning("Mart tables not found – dbt may not have run yet.")
        return {"customer_activity": [], "risk_signals": [], "volume_summary": []}
    except psycopg2.OperationalError as exc:
        logger.error("Database connection failed: %s", exc)
        return {"error": str(exc), "customer_activity": [], "risk_signals": [], "volume_summary": []}
