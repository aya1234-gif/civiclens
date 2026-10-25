"""Airflow DAG: monthly HCP and finances.gov.ma statistics ingestion."""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago


@dag(
    dag_id="monthly_stats",
    description="Download HCP and budget statistics on the 2nd of each month",
    schedule_interval="0 8 2 * *",
    start_date=days_ago(1),
    catchup=False,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=15),
        "owner": "civiclens",
    },
    tags=["ingestion", "hcp", "budget"],
)
def monthly_stats_dag() -> None:
    """Download monthly statistical publications from HCP and finances.gov.ma."""

    @task()
    def download_hcp_datasets() -> list[str]:
        """Download all Excel/ZIP datasets from hcp.ma."""
        import asyncio

        from ingestion.scrapers.hcp_scraper import HcpScraper

        async def _run() -> list[str]:
            async with HcpScraper() as scraper:
                paths = await scraper.scrape_all()
            return [str(p) for p in paths]

        return asyncio.run(_run())

    @task()
    def log_download_summary(paths: list[str]) -> None:
        """Emit a structured log summarising this month's downloads."""
        import structlog

        log = structlog.get_logger(__name__)
        log.info("monthly_stats_downloaded", count=len(paths), files=paths)

    paths = download_hcp_datasets()
    log_download_summary(paths)


monthly_stats_dag()
