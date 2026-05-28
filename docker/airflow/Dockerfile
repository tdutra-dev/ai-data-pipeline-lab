# ─────────────────────────────────────────────────────────────────────────────
# Custom Airflow image: apache/airflow 2.9.3 + dbt-postgres
#
# Uses the official Airflow constraints file to avoid dependency conflicts
# between Airflow's pinned packages and dbt's requirements.
# ─────────────────────────────────────────────────────────────────────────────

ARG AIRFLOW_VERSION=2.9.3
ARG PYTHON_VERSION=3.11

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

ARG AIRFLOW_VERSION=2.9.3
ARG PYTHON_VERSION=3.11

# Install dbt-postgres respecting Airflow's own dependency constraints
COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    -r /tmp/requirements.txt
