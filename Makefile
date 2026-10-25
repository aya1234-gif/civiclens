.PHONY: setup ingest transform api audit test lint fmt typecheck clean docker-up docker-down backfill train frontend

PYTHON := .venv/bin/python
UV := uv
DBT := ../.venv/bin/dbt
PYTEST := .venv/bin/pytest

# ── Bootstrap ────────────────────────────────────────────────────────────────

setup:
	@echo "→ Ensuring uv is installed"
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@export PATH="$$HOME/.cargo/bin:$$HOME/.local/bin:$$PATH"; \
	echo "→ Installing Python 3.12 via uv"; \
	uv python install 3.12; \
	echo "→ Creating virtual environment (Python 3.12)"; \
	uv venv .venv --python 3.12; \
	echo "→ Installing Python dependencies"; \
	uv pip install --python .venv/bin/python -e ".[dev]"
	@echo "→ Installing Playwright browsers"
	$(PYTHON) -m playwright install chromium
	@echo "→ Copying .env template (edit before use)"
	@test -f .env || cp .env.example .env
	@echo "→ Starting Postgres + Redis"
	docker compose up -d postgres redis
	@echo "→ Waiting for Postgres to be ready…"
	@until docker compose exec postgres pg_isready -U civiclens > /dev/null 2>&1; do sleep 1; done
	@echo "→ Initialising database schemas"
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-civiclens} -d $${POSTGRES_DB:-civiclens} \
	  -c "CREATE SCHEMA IF NOT EXISTS raw; CREATE SCHEMA IF NOT EXISTS staging; CREATE SCHEMA IF NOT EXISTS marts;"
	@echo "✓ Setup complete. Edit .env with your API keys, then run: make docker-up"

# ── Ingestion ────────────────────────────────────────────────────────────────

ingest:
	@echo "→ Running marchespublics scraper for today (capped at 10 pages)"
	$(PYTHON) -m ingestion.scrapers.marchespublics_scraper --date today --max-pages 10

ingest-date:
	@test -n "$(DATE)" || (echo "Usage: make ingest-date DATE=2024-05-01" && exit 1)
	$(PYTHON) -m ingestion.scrapers.marchespublics_scraper --date $(DATE)

backfill:
	@echo "→ Bulk-ingesting 20 pages × 500 rows = ~10 000 tenders (newest-first)"
	set -a && . ./.env && set +a && \
	$(PYTHON) -m ingestion.bulk_ingest --pages 20

train:
	@echo "→ Training anomaly detection model"
	set -a && . ./.env && set +a && \
	$(PYTHON) -m ml.anomaly.train

pipeline:
	@echo "→ Running full pipeline: ingest → transform → train"
	$(MAKE) ingest
	$(MAKE) transform
	$(MAKE) train

frontend:
	@echo "→ Starting React frontend (port 5177)"
	cd frontend && npm run dev -- --port 5177

# ── Warehouse ─────────────────────────────────────────────────────────────────

transform:
	@echo "→ Loading today's JSONL into Postgres"
	$(PYTHON) -m ingestion.loader --date today
	@echo "→ dbt seed (wilayas)"
	cd warehouse && $(DBT) seed --profiles-dir ..
	@echo "→ dbt run"
	cd warehouse && $(DBT) run --profiles-dir ..
	@echo "→ dbt test"
	cd warehouse && $(DBT) test --profiles-dir ..

transform-run:
	cd warehouse && $(DBT) run --profiles-dir ..

transform-test:
	cd warehouse && $(DBT) test --profiles-dir ..

seeds:
	cd warehouse && $(DBT) seed --profiles-dir ..

# ── API ───────────────────────────────────────────────────────────────────────

frontend:
	@echo "→ Starting React frontend (port 5173)"
	cd frontend && npm run dev

api:
	@echo "→ Starting FastAPI dev server (hot-reload)"
	set -a && . ./.env && set +a && \
	.venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8001

# ── Governance ────────────────────────────────────────────────────────────────

audit:
	@echo "→ Running bias audit"
	$(PYTHON) -m governance.bias_audit

lineage:
	@echo "→ Generating lineage report"
	$(PYTHON) -m governance.lineage_reporter

# ── Quality ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) --cov=. --cov-report=term-missing --cov-report=html -v

test-fast:
	$(PYTEST) -x -q --no-header

lint:
	ruff check .

fmt:
	ruff format .

typecheck:
	mypy . --ignore-missing-imports

check: lint typecheck test

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-reset:
	docker compose down -v
	docker compose up -d

# ── Misc ──────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete 2>/dev/null; true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	cd warehouse && rm -rf target dbt_packages
