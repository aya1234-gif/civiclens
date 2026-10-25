"""Bulk ingestion: scrape N pages of all tenders (newest-first) into Postgres.

The marchespublics portal returns all 229K+ tenders sorted roughly by
publication date descending, regardless of any date filter we send.  For
historical backfill we simply scrape as many pages as needed and store
everything — deduplication is handled by the raw_hash UNIQUE constraint.

Usage:
    python -m ingestion.bulk_ingest --pages 50        # ~25 000 tenders, ~40 min
    python -m ingestion.bulk_ingest --pages 200       # ~100 000 tenders, ~3 hrs
    python -m ingestion.bulk_ingest --pages 10        # quick test, ~5 000 tenders
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import asyncpg
import httpx
import structlog
from bs4 import BeautifulSoup, Tag
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential

from config.settings import settings
from ingestion.loader import _CREATE_TABLE_SQL

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.marchespublics.gov.ma"
_SEARCH_URL = f"{_BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch"
_PAGE_SIZE = "500"
_RATE_DELAY = 1.0 / settings.scraper_rate_limit_rps

_UA = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
]

_F_STATE    = "PRADO_PAGESTATE"
_F_TARGET   = "PRADO_POSTBACK_TARGET"
_F_PARAM    = "PRADO_POSTBACK_PARAMETER"
_F_SEARCH   = "ctl0$CONTENU_PAGE$AdvancedSearch$lancerRecherche"
_F_SRCHTYPE = "ctl0$CONTENU_PAGE$AdvancedSearch$type_rechercheEntite"
_F_PAGE_NUM = "ctl0$CONTENU_PAGE$resultSearch$numPageTop"
_F_PAGE_BTN = "ctl0$CONTENU_PAGE$resultSearch$DefaultButtonTop"
_F_PAGE_SZ  = "ctl0$CONTENU_PAGE$resultSearch$listePageSizeTop"

_UPSERT = """
INSERT INTO raw.tenders (
    reference, contracting_authority, object, tender_type, procedure_type,
    publication_date, deadline_date, wilaya, detail_url, scraped_at, raw_hash
) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
ON CONFLICT (raw_hash) DO NOTHING;
"""


async def bulk_ingest(max_pages: int) -> None:
    """Scrape *max_pages* result pages and load everything into raw.tenders."""
    db_url = (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    conn = await asyncpg.connect(db_url)
    await conn.execute(_CREATE_TABLE_SQL)

    last_req = 0.0

    async def pace() -> None:
        nonlocal last_req
        elapsed = time.monotonic() - last_req
        if elapsed < _RATE_DELAY:
            await asyncio.sleep(_RATE_DELAY - elapsed)
        last_req = time.monotonic()

    async def fetch(client: httpx.AsyncClient, method: str, url: str, data: dict | None = None) -> str:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.scraper_max_retries),
            wait=wait_exponential(min=2, max=30), reraise=True,
        ):
            with attempt:
                await pace()
                r = await client.request(method, url, data=data,
                    headers={"User-Agent": random.choice(_UA), "Referer": _BASE_URL})
                r.raise_for_status()
                return r.content.decode(r.encoding or "utf-8", errors="replace")
        return ""

    def get_state(html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("input", {"name": _F_STATE})
        return tag["value"] if isinstance(tag, Tag) else ""  # type: ignore[index]

    def parse_rows(html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict[str, Any]] = []
        ref_spans = soup.find_all(
            "span", id=re.compile(r"tableauResultSearch_ctl\d+_reference$")
        )
        for span in ref_spans:
            m = re.search(r"ctl(\d+)_reference", span["id"])
            if not m:
                continue
            n = m.group(1)
            pfx = f"ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl{n}"

            def txt(s: str) -> str:
                t = soup.find(id=f"{pfx}_{s}")
                return t.get_text(strip=True) if t else ""

            ref = span.get_text(strip=True)
            raw = ref + txt("panelBlocDenomination") + txt("panelBlocCategorie")
            raw_hash = hashlib.sha256(raw.encode()).hexdigest()

            # publication date from cell[1]
            pub_date = None
            act = soup.find(id=f"{pfx}_panelAction")
            deadline = None
            if act:
                tr = act.find_parent("tr")
                if tr:
                    cells = tr.find_all("td")
                    if len(cells) >= 2:
                        m2 = re.search(r"\d{2}/\d{2}/\d{4}", cells[1].get_text(separator="|"))
                        if m2:
                            pub_date = m2.group()
                    if len(cells) >= 5:
                        m3 = re.search(r"\d{2}/\d{2}/\d{4}", cells[4].get_text(separator="|"))
                        if m3:
                            deadline = m3.group()

            detail_url = ""
            if act:
                a = act.find("a", href=lambda h: h and "EntrepriseDetailConsultation" in h)
                if a:
                    detail_url = urljoin(_BASE_URL, a["href"])

            def parse_date(s: str | None) -> str | None:
                if not s:
                    return None
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(s, fmt).date().isoformat()
                    except ValueError:
                        continue
                return None

            authority = txt("panelBlocDenomination")
            authority = re.sub(r"^Acheteur public\s*:", "", authority).strip()
            authority = " ".join(authority.split())

            rows.append({
                "reference":            ref,
                "contracting_authority": authority,
                "object":               " ".join((txt("infosBullesObjet") or txt("panelBlocObjet")).split()),
                "tender_type":          txt("panelBlocCategorie").lower() or "autre",
                "procedure_type":       txt("panelBlocTypesProc").lower(),
                "publication_date":     parse_date(pub_date),
                "deadline_date":        parse_date(deadline),
                "wilaya":               _first_wilaya(txt("panelBlocLieuxExec")),
                "detail_url":           detail_url,
                "scraped_at":           datetime.utcnow().isoformat(),
                "raw_hash":             raw_hash,
            })
        return rows

    total_inserted = 0
    total_rows = 0

    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=45.0, follow_redirects=True) as client:
        # Step 1: GET to seed the PRADO session
        html = await fetch(client, "GET", _SEARCH_URL)
        state = get_state(html)
        log.info("session_acquired", state_len=len(state))

        # Step 2: POST to get all results (no date filter)
        payload = {
            _F_STATE: state, _F_TARGET: _F_SEARCH, _F_PARAM: "",
            _F_SEARCH: "Lancer la recherche", _F_SRCHTYPE: "floue",
        }
        html = await fetch(client, "POST", _SEARCH_URL, data=payload)

        for page in range(1, max_pages + 1):
            rows = parse_rows(html)
            if not rows:
                log.info("no_rows_on_page", page=page)
                break

            from datetime import date as date_type, datetime as dt_type

            def _d(s: str | None):
                return date_type.fromisoformat(s) if s else None

            def _ts(s: str | None):
                return dt_type.fromisoformat(s) if s else None

            # Bulk upsert
            async with conn.transaction():
                for row in rows:
                    result = await conn.execute(
                        _UPSERT,
                        row["reference"], row["contracting_authority"], row["object"],
                        row["tender_type"], row["procedure_type"],
                        _d(row["publication_date"]), _d(row["deadline_date"]),
                        row["wilaya"], row["detail_url"],
                        _ts(row["scraped_at"]), row["raw_hash"],
                    )
                    if result == "INSERT 0 1":
                        total_inserted += 1

            total_rows += len(rows)
            log.info("page_done", page=page, rows=len(rows),
                     inserted=total_inserted, total_rows=total_rows)

            # Check total pages
            soup = BeautifulSoup(html, "lxml")
            npages_tag = soup.find(id="ctl0_CONTENU_PAGE_resultSearch_nombrePageTop")
            total_pages = int(npages_tag.get_text(strip=True)) if npages_tag else max_pages
            if page >= min(max_pages, total_pages):
                log.info("reached_limit", page=page, max_pages=max_pages)
                break

            # Navigate to next page
            state = get_state(html)
            payload = {
                _F_STATE: state, _F_TARGET: _F_PAGE_BTN, _F_PARAM: "",
                _F_PAGE_NUM: str(page + 1), _F_PAGE_SZ: _PAGE_SIZE,
            }
            html = await fetch(client, "POST", _SEARCH_URL, data=payload)

    await conn.close()
    log.info("bulk_ingest_complete", total_rows=total_rows, inserted=total_inserted)


def _first_wilaya(text: str) -> str | None:
    clean = text.replace("...", "|").replace(",", "|")
    parts = [p.strip() for p in clean.split("|") if p.strip() and p.strip().upper() != "MAROC"]
    return parts[0] if parts else None


async def _main() -> None:
    structlog.configure(processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ])
    parser = argparse.ArgumentParser(description="Bulk ingest tenders from marchespublics.gov.ma")
    parser.add_argument("--pages", type=int, default=20,
                        help="Number of result pages to scrape (500 rows/page). Default: 20 (~10 000 tenders)")
    args = parser.parse_args()
    log.info("bulk_ingest_start", pages=args.pages,
             estimated_tenders=args.pages * 500)
    await bulk_ingest(args.pages)


if __name__ == "__main__":
    asyncio.run(_main())
