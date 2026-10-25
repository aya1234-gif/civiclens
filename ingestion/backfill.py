"""Backfill scraper: fetch tenders for a range of past dates.

Usage:
    python -m ingestion.backfill --days 30
    python -m ingestion.backfill --start 2026-01-01 --end 2026-06-01
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

import structlog

from ingestion.loader import _CREATE_TABLE_SQL, load_file
from ingestion.scrapers.marchespublics_scraper import (
    MarchesPublicsScraper,
    save_tenders,
)

import asyncpg
from config.settings import settings

log = structlog.get_logger(__name__)


async def backfill(start: date, end: date, max_pages_per_day: int = 5) -> None:
    """Scrape and load tenders for every date in [start, end].

    Args:
        start: First date to scrape (inclusive).
        end: Last date to scrape (inclusive).
        max_pages_per_day: Page cap per day — keeps runs under ~10 min/day.
    """
    db_url = (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    conn = await asyncpg.connect(db_url)
    await conn.execute(_CREATE_TABLE_SQL)

    current = start
    total_days = (end - start).days + 1
    day_num = 0

    async with MarchesPublicsScraper() as scraper:
        while current <= end:
            day_num += 1
            log.info("backfill_day", date=str(current), progress=f"{day_num}/{total_days}")

            tenders = await scraper.scrape(current, max_pages=max_pages_per_day)

            if tenders:
                path = await save_tenders(tenders, current)
                inserted = await load_file(path, conn)
                log.info("day_loaded", date=str(current), scraped=len(tenders), inserted=inserted)
            else:
                log.info("day_empty", date=str(current))

            current += timedelta(days=1)

    await conn.close()
    log.info("backfill_complete", days=total_days)


async def _main() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    parser = argparse.ArgumentParser(description="Backfill tender scraper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--days", type=int, help="Number of past days to backfill")
    group.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=str(date.today()), help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages per day (default: 5)")
    args = parser.parse_args()

    if args.days:
        start = date.today() - timedelta(days=args.days)
        end = date.today()
    else:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)

    log.info("backfill_start", start=str(start), end=str(end), max_pages=args.max_pages)
    await backfill(start, end, max_pages_per_day=args.max_pages)


if __name__ == "__main__":
    asyncio.run(_main())
