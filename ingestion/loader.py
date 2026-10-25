"""Load raw JSONL tender files into the Postgres raw.tenders table.

Usage:
    python -m ingestion.loader --date today
    python -m ingestion.loader --date 2026-06-03
    python -m ingestion.loader --all          # load every file in data/raw/tenders/
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

import asyncpg
import structlog
from datetime import datetime

from config.settings import settings

log = structlog.get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw.tenders (
    reference               TEXT,
    contracting_authority   TEXT,
    object                  TEXT,
    tender_type             TEXT,
    procedure_type          TEXT,
    publication_date        DATE,
    deadline_date           DATE,
    wilaya                  TEXT,
    detail_url              TEXT,
    scraped_at              TIMESTAMPTZ,
    raw_hash                TEXT,
    UNIQUE (raw_hash)
);
"""

_UPSERT_SQL = """
INSERT INTO raw.tenders (
    reference, contracting_authority, object, tender_type, procedure_type,
    publication_date, deadline_date, wilaya, detail_url, scraped_at, raw_hash
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
)
ON CONFLICT (raw_hash) DO NOTHING;
"""


async def load_file(path: Path, conn: asyncpg.Connection) -> int:
    """Load a single JSONL file into raw.tenders.

    Returns the number of rows inserted (excluding duplicates).
    """
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def _date(v: str | None) -> date | None:
        return date.fromisoformat(v) if v else None

    def _dt(v: str | None):
        return datetime.fromisoformat(v) if v else None
    if not rows:
        log.warning("empty_file", path=str(path))
        return 0

    inserted = 0
    async with conn.transaction():
        for row in rows:
            result = await conn.execute(
                _UPSERT_SQL,
                row.get("reference"),
                row.get("contracting_authority"),
                row.get("object"),
                row.get("tender_type"),
                row.get("procedure_type"),
                _date(row.get("publication_date")),
                _date(row.get("deadline_date")),
                row.get("wilaya"),
                row.get("detail_url"),
                _dt(row.get("scraped_at")),
                row.get("raw_hash"),
            )
            if result == "INSERT 0 1":
                inserted += 1

    log.info("file_loaded", path=str(path), rows=len(rows), inserted=inserted)
    return inserted


async def _main() -> None:
    """CLI entrypoint."""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )

    parser = argparse.ArgumentParser(description="Load tender JSONL into Postgres")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="Load file for YYYY-MM-DD (or 'today')")
    group.add_argument("--all", action="store_true", help="Load all JSONL files")
    args = parser.parse_args()

    # asyncpg needs a plain psycopg-style URL (no +asyncpg dialect prefix)
    db_url = (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(_CREATE_TABLE_SQL)

        raw_dir = Path(settings.data_raw_dir) / "tenders"

        if args.all:
            files = sorted(raw_dir.glob("*.jsonl"))
        else:
            target = date.today() if args.date == "today" else date.fromisoformat(args.date)
            files = [raw_dir / f"{target.isoformat()}.jsonl"]

        total = 0
        for f in files:
            if not f.exists():
                log.warning("file_not_found", path=str(f))
                continue
            total += await load_file(f, conn)

        log.info("load_complete", total_inserted=total, files=len(files))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(_main())
