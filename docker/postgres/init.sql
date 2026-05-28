-- ─────────────────────────────────────────────────────────────────────────────
-- PostgreSQL initialisation – runs once on first container start
-- Creates the two databases needed by the project:
--   • trading  → the actual data warehouse (raw → staging → marts)
--   • airflow  → Airflow metadata store
-- ─────────────────────────────────────────────────────────────────────────────

-- Trading data warehouse
CREATE USER trading WITH PASSWORD 'trading';
CREATE DATABASE trading OWNER trading;
GRANT ALL PRIVILEGES ON DATABASE trading TO trading;

-- Airflow metadata
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
