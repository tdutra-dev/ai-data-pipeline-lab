.PHONY: help up down build logs clean trigger-dag dbt-run dbt-test psql ai-health

# ─── Help ────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "AI Data Pipeline Lab — available commands"
	@echo "─────────────────────────────────────────"
	@echo "  make up            Start all services (detached)"
	@echo "  make build         Rebuild Docker images"
	@echo "  make down          Stop all services"
	@echo "  make clean         Stop and remove volumes (data reset)"
	@echo "  make logs          Tail all logs"
	@echo "  make trigger-dag   Manually trigger the Airflow pipeline DAG"
	@echo "  make dbt-run       Run dbt models directly"
	@echo "  make dbt-test      Run dbt tests directly"
	@echo "  make dbt-docs      Generate dbt docs (open http://localhost:8888)"
	@echo "  make psql          Open psql on the trading database"
	@echo "  make ai-health     Check the AI insights service"
	@echo "  make ai-insights   Generate a new AI insights report"
	@echo ""

# ─── Docker lifecycle ────────────────────────────────────────────────────────
up:
	@cp -n .env.example .env 2>/dev/null || true
	docker compose up -d

build:
	docker compose build --no-cache

down:
	docker compose down

clean:
	docker compose down -v
	@echo "⚠  All volumes removed – database data is gone."

logs:
	docker compose logs -f

airflow-logs:
	docker compose logs -f airflow-webserver airflow-scheduler

# ─── Pipeline operations ─────────────────────────────────────────────────────
trigger-dag:
	docker compose exec airflow-webserver airflow dags trigger trading_pipeline

ingest:
	docker compose exec airflow-webserver python /opt/airflow/ingestion/load_raw.py

dbt-deps:
	docker compose exec airflow-webserver bash -c \
	  "cd /opt/airflow/dbt && dbt deps --profiles-dir /opt/airflow/dbt"

dbt-run:
	docker compose exec airflow-webserver bash -c \
	  "cd /opt/airflow/dbt && dbt run --profiles-dir /opt/airflow/dbt"

dbt-test:
	docker compose exec airflow-webserver bash -c \
	  "cd /opt/airflow/dbt && dbt test --profiles-dir /opt/airflow/dbt"

dbt-docs:
	docker compose exec airflow-webserver bash -c \
	  "cd /opt/airflow/dbt && dbt docs generate --profiles-dir /opt/airflow/dbt && dbt docs serve --port 8888 --host 0.0.0.0" &
	@echo "Open http://localhost:8888"

# ─── Database ────────────────────────────────────────────────────────────────
psql:
	docker compose exec postgres psql -U trading -d trading

psql-marts:
	docker compose exec postgres psql -U trading -d trading \
	  -c "SELECT * FROM marts.mart_customer_activity ORDER BY total_notional DESC;"

psql-risk:
	docker compose exec postgres psql -U trading -d trading \
	  -c "SELECT * FROM marts.mart_risk_signals ORDER BY total_risk_events DESC;"

# ─── AI Layer ────────────────────────────────────────────────────────────────
ai-health:
	curl -s http://localhost:8001/health | python3 -m json.tool

ai-insights:
	curl -s -X POST http://localhost:8001/insights/generate \
	  -H "Content-Type: application/json" \
	  -d '{"execution_date": "$(shell date -I)"}' | python3 -m json.tool
