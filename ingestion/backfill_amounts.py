"""Backfill awarded contract amounts by scraping each tender's PV/award PDF.

v1 scope: only tenders that have reached the award stage (i.e. have a PV
attachment) will yield an amount. Run repeatedly over time as more tenders
reach that stage — already-extracted references are skipped.

Usage:
    python -m ingestion.backfill_amounts --limit 50
    python -m ingestion.backfill_amounts --all
"""

from __future__ import annotations

import argparse
import asyncio

import asyncpg
import structlog

from config.settings import settings
from ingestion.scrapers.pv_amount_scraper import extract_amount

log = structlog.get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.tender_amounts (
    reference       TEXT PRIMARY KEY,
    attributaire    TEXT,
    montant_mad     NUMERIC,
    source          TEXT,
    extracted_at    TIMESTAMPTZ DEFAULT now()
);
"""

_PENDING_SQL = """
SELECT s.reference, s.source_url
FROM public_staging.stg_tenders s
LEFT JOIN public.tender_amounts a USING (reference)
WHERE a.reference IS NULL
  AND s.source_url IS NOT NULL
ORDER BY s.publication_date DESC
LIMIT $1;
"""

_UPSERT_SQL = """
INSERT INTO public.tender_amounts (reference, attributaire, montant_mad, source)
VALUES ($1, $2, $3, $4)
ON CONFLICT (reference) DO UPDATE SET
    attributaire = EXCLUDED.attributaire,
    montant_mad  = EXCLUDED.montant_mad,
    source       = EXCLUDED.source,
    extracted_at = now();
"""


async def _run(limit: int) -> None:
    db_url = (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(_CREATE_TABLE_SQL)
        rows = await conn.fetch(_PENDING_SQL, limit)
        log.info("backfill_amounts_starting", pending=len(rows))

        found = 0
        for row in rows:
            result = await extract_amount(row["reference"], row["source_url"])
            if result is not None:
                await conn.execute(
                    _UPSERT_SQL,
                    result.reference,
                    result.attributaire,
                    result.montant_mad,
                    result.source,
                )
                found += 1
                log.info(
                    "amount_extracted",
                    reference=result.reference,
                    montant_mad=result.montant_mad,
                    source=result.source,
                )

        log.info("backfill_amounts_complete", processed=len(rows), found=found)
    finally:
        await conn.close()


def _main() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--limit", type=int, help="Process at most N pending tenders")
    group.add_argument("--all", action="store_true", help="Process all pending tenders")
    args = parser.parse_args()

    asyncio.run(_run(args.limit if args.limit else 10_000_000))


if __name__ == "__main__":
    _main()
