"""
airflow/dags/trading_pipeline_dag.py
──────────────────────────────────────────────────────────────────────────────
Main Airflow DAG for the AI Data Pipeline Lab.

Pipeline steps (run daily at 06:00 UTC):
  1. ingest_raw_data    – Loads CSV files into trading.raw.* tables
  2. dbt_deps           – Installs dbt packages (dbt_utils)
  3. run_dbt_models     – Executes staging → intermediate → mart transformations
  4. run_dbt_tests      – Validates all dbt data quality tests
  5. generate_ai_summary – Calls the AI layer to produce daily insights

Each step is idempotent and the DAG never catches up on missed runs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# ─── Default arguments ───────────────────────────────────────────────────────
DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}

# ─── dbt command helper ───────────────────────────────────────────────────────
DBT_CMD = "cd /opt/airflow/dbt && dbt {subcmd} --profiles-dir /opt/airflow/dbt --no-partial-parse"

# ─── AI Layer ────────────────────────────────────────────────────────────────
AI_LAYER_URL = "http://ai-layer:8000"


def generate_ai_summary(**context: dict) -> None:
    """
    Calls the AI insights service to generate the daily summary.
    Gracefully degrades if the service is unavailable.
    """
    execution_date = str(context.get("ds", datetime.utcnow().date()))

    try:
        response = requests.post(
            f"{AI_LAYER_URL}/insights/generate",
            json={"execution_date": execution_date},
            timeout=120,
        )
        response.raise_for_status()
        insights = response.json()

        logger.info("─── AI Insights Summary ─────────────────────────────")
        logger.info("Anomaly summary : %s",
                    insights.get("anomaly_summary", "—"))
        logger.info("Risk explanation: %s",
                    insights.get("risk_explanation", "—"))
        logger.info("Operational     : %s", insights.get(
            "operational_insight", "—"))
        logger.info("────────────────────────────────────────────────────")

    except requests.exceptions.ConnectionError:
        logger.warning(
            "AI layer not reachable at %s – skipping insight generation. "
            "Ensure OPENAI_API_KEY is set and the ai-layer container is running.",
            AI_LAYER_URL,
        )
    except requests.exceptions.HTTPError as exc:
        logger.error("AI layer returned an error: %s", exc)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error calling AI layer: %s", exc)
        raise


# ─── DAG definition ──────────────────────────────────────────────────────────
with DAG(
    dag_id="trading_pipeline",
    description="End-to-end fintech data pipeline: ingest → dbt → AI insights",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 6 * * *",   # daily at 06:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["fintech", "dbt", "trading", "ai"],
) as dag:

    # ── Step 1: Ingest raw CSVs into PostgreSQL ───────────────────────────────
    ingest_raw_data = BashOperator(
        task_id="ingest_raw_data",
        bash_command="python /opt/airflow/ingestion/load_raw.py",
        doc_md="""
        Runs the ingestion script that truncates and reloads all raw tables
        in the `trading.raw` schema from CSV source files.
        """,
    )

    # ── Step 2: Install dbt packages ─────────────────────────────────────────
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=DBT_CMD.format(subcmd="deps"),
        doc_md="Installs dbt_utils and any other packages declared in packages.yml.",
    )

    # ── Step 3: Run dbt transformations ──────────────────────────────────────
    run_dbt_models = BashOperator(
        task_id="run_dbt_models",
        bash_command=DBT_CMD.format(subcmd="run"),
        doc_md="""
        Executes all dbt models in dependency order:
          staging (views) → intermediate (views) → marts (tables)
        """,
    )

    # ── Step 4: Run dbt data quality tests ───────────────────────────────────
    run_dbt_tests = BashOperator(
        task_id="run_dbt_tests",
        bash_command=DBT_CMD.format(subcmd="test"),
        doc_md="""
        Runs all dbt generic and singular tests:
          not_null, unique, accepted_values, relationships
        Fails the DAG if any test fails – data quality gate.
        """,
    )

    # ── Step 5: Generate AI insights ─────────────────────────────────────────
    generate_ai_summary_task = PythonOperator(
        task_id="generate_ai_summary",
        python_callable=generate_ai_summary,
        doc_md="""
        Calls the FastAPI AI layer which reads the mart tables and uses
        OpenAI GPT-4o-mini to produce:
          • Anomaly summary
          • Risk explanation
          • Operational insight
        """,
    )

    # ── Task dependencies ─────────────────────────────────────────────────────
    (
        ingest_raw_data
        >> dbt_deps
        >> run_dbt_models
        >> run_dbt_tests
        >> generate_ai_summary_task
    )
