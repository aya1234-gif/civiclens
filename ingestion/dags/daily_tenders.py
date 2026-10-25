"""Airflow DAG: daily tender ingestion → load → dbt → anomaly scoring."""

from __future__ import annotations

import subprocess
from datetime import date, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago


@dag(
    dag_id="daily_tenders",
    description="Scrape marchespublics → load Postgres → dbt → anomaly model",
    schedule_interval="0 6 * * 1-6",  # 06:00 Mon–Sat (portal is quiet on Sunday)
    start_date=days_ago(1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "owner": "civiclens",
    },
    tags=["ingestion", "tenders", "daily"],
)
def daily_tenders_dag() -> None:
    """Full daily pipeline: scrape → load → transform → score."""

    @task()
    def scrape_today() -> str:
        """Run the marchespublics scraper for today and return the JSONL path."""
        import asyncio
        from ingestion.scrapers.marchespublics_scraper import (
            MarchesPublicsScraper, save_tenders,
        )

        today = date.today()

        async def _run() -> str:
            async with MarchesPublicsScraper() as scraper:
                tenders = await scraper.scrape(today, max_pages=10)
            if tenders:
                path = await save_tenders(tenders, today)
                return str(path)
            return ""

        return asyncio.run(_run())

    @task()
    def load_to_postgres(jsonl_path: str) -> int:
        """UPSERT the JSONL file into raw.tenders. Returns rows inserted."""
        import asyncio
        import asyncpg
        from pathlib import Path
        from ingestion.loader import _CREATE_TABLE_SQL, load_file
        from config.settings import settings

        if not jsonl_path:
            return 0

        db_url = (
            settings.database_url
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgresql+psycopg2://", "postgresql://")
        )

        async def _run() -> int:
            conn = await asyncpg.connect(db_url)
            await conn.execute(_CREATE_TABLE_SQL)
            n = await load_file(Path(jsonl_path), conn)
            await conn.close()
            return n

        return asyncio.run(_run())

    @task()
    def dbt_run_and_test(rows_loaded: int) -> bool:
        """Run dbt staging models and tests. Fail the DAG on test failure.

        Depends on `rows_loaded` (load_to_postgres's return value) purely to
        create the correct upstream edge in the task graph — dbt always
        operates on the full raw.tenders table, not just the rows from this
        run, so the count itself isn't used beyond that.
        """
        result = subprocess.run(
            ["dbt", "run", "--select", "stg_tenders", "--profiles-dir", ".."],
            cwd="/opt/airflow/civiclens/warehouse",
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dbt run failed:\n{result.stdout}\n{result.stderr}")

        result = subprocess.run(
            ["dbt", "test", "--select", "stg_tenders", "--profiles-dir", ".."],
            cwd="/opt/airflow/civiclens/warehouse",
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dbt test failed:\n{result.stdout}\n{result.stderr}")

        return True

    @task()
    def score_anomalies(dbt_ok: bool) -> None:
        """Re-train and score the anomaly model on updated data."""
        import asyncio
        from ml.anomaly.train import train_and_score

        if not dbt_ok:
            return
        asyncio.run(train_and_score(contamination=0.08))

    @task()
    def enrich_detail_pages(dbt_ok: bool) -> None:
        """Fetch detail pages for new tenders to get real bid deadlines."""
        import asyncio
        from ingestion.scrapers.detail_scraper import enrich_details

        if not dbt_ok:
            return
        asyncio.run(enrich_details(limit=200))  # cap per daily run

    @task()
    def embed_new_tenders(dbt_ok: bool) -> None:
        """Embed any new tenders that don't yet have a vector representation."""
        import asyncio
        from ml.rag.embed import embed_tenders

        if not dbt_ok:
            return
        asyncio.run(embed_tenders(rebuild=False))

    # DAG wiring
    path = scrape_today()
    rows = load_to_postgres(path)
    dbt_ok = dbt_run_and_test(rows)
    score_anomalies(dbt_ok)
    enrich_detail_pages(dbt_ok)
    embed_new_tenders(dbt_ok)


daily_tenders_dag()
