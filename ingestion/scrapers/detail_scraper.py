"""Detail-page scraper for marchespublics.gov.ma.

Fetches individual tender detail pages to extract fields not available
on the listing page:
  - real_deadline     : dateHeureLimiteRemisePlis (actual bid submission deadline)
  - announcement_type : annonce (Avis d'appel d'offres / PV / résultat définitif)

Note: estimated amounts and attributee names are NOT exposed in the public
detail page — they are behind authenticated supplier accounts or PDF
attachments. This scraper captures what is publicly accessible.

Usage:
    python -m ingestion.scrapers.detail_scraper              # enrich missing rows
    python -m ingestion.scrapers.detail_scraper --limit 500  # batch cap
"""

from __future__ import annotations

import argparse
import asyncio
import re
import time
from datetime import date, datetime

import asyncpg
import httpx
import structlog
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential

from config.settings import settings

load_dotenv()
log = structlog.get_logger(__name__)

_BASE_URL = "https://www.marchespublics.gov.ma"
_RATE_DELAY = 1.2  # seconds between requests — be polite

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# ── SQL ───────────────────────────────────────────────────────────────────────

_CREATE_DETAILS_TABLE = """
CREATE TABLE IF NOT EXISTS public.tender_details (
    reference           TEXT PRIMARY KEY,
    real_deadline       TIMESTAMPTZ,
    announcement_type   TEXT,
    enriched_at         TIMESTAMPTZ DEFAULT NOW()
);
"""

_LOAD_PENDING = """
SELECT t.reference, t.detail_url
FROM raw.tenders t
LEFT JOIN public.tender_details d USING (reference)
WHERE t.detail_url IS NOT NULL
  AND t.detail_url != ''
  AND d.reference IS NULL
ORDER BY t.scraped_at DESC
LIMIT $1
"""

_UPSERT_DETAIL = """
INSERT INTO public.tender_details (reference, real_deadline, announcement_type)
VALUES ($1, $2, $3)
ON CONFLICT (reference) DO UPDATE
  SET real_deadline     = EXCLUDED.real_deadline,
      announcement_type = EXCLUDED.announcement_type,
      enriched_at       = NOW()
"""


# ── Parser ────────────────────────────────────────────────────────────────────

_PREFIX = "ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_"


def _span(soup: BeautifulSoup, field: str) -> str:
    tag = soup.find("span", id=f"{_PREFIX}{field}")
    return tag.get_text(strip=True) if tag else ""


def _parse_deadline(text: str) -> datetime | None:
    """Parse 'DD/MM/YYYY HH:MM' into a timezone-naive datetime."""
    m = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", text)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d/%m/%Y %H:%M")
    except ValueError:
        return None


def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    return {
        "real_deadline": _parse_deadline(_span(soup, "dateHeureLimiteRemisePlis")),
        "announcement_type": _span(soup, "annonce") or None,
    }


# ── HTTP ──────────────────────────────────────────────────────────────────────

async def _fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=15),
            reraise=True,
        ):
            with attempt:
                r = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT, "Referer": _BASE_URL},
                    timeout=30,
                    follow_redirects=True,
                )
                r.raise_for_status()
                return r.content.decode(r.encoding or "utf-8", errors="replace")
    except RetryError:
        return None
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

async def enrich_details(limit: int = 1000) -> None:
    db_url = (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    conn = await asyncpg.connect(db_url)

    try:
        await conn.execute(_CREATE_DETAILS_TABLE)
        rows = await conn.fetch(_LOAD_PENDING, limit)

        if not rows:
            log.info("detail_scraper.nothing_to_enrich")
            return

        log.info("detail_scraper.start", n=len(rows))
        ok = 0
        t0 = time.perf_counter()

        async with httpx.AsyncClient() as client:
            for i, row in enumerate(rows):
                ref = row["reference"]
                url = row["detail_url"]

                html = await _fetch(client, url)
                if not html:
                    log.warning("detail_scraper.fetch_failed", ref=ref)
                    continue

                detail = parse_detail_page(html)
                await conn.execute(
                    _UPSERT_DETAIL,
                    ref,
                    detail["real_deadline"],
                    detail["announcement_type"],
                )
                ok += 1

                if ok % 50 == 0:
                    log.info("detail_scraper.progress",
                             done=ok, total=len(rows),
                             elapsed_s=round(time.perf_counter() - t0, 1))

                # Rate limiting
                await asyncio.sleep(_RATE_DELAY)

        log.info("detail_scraper.complete",
                 enriched=ok, total=len(rows),
                 elapsed_s=round(time.perf_counter() - t0, 1))

    finally:
        await conn.close()


if __name__ == "__main__":
    import structlog
    structlog.configure(processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ])
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    asyncio.run(enrich_details(limit=args.limit))
