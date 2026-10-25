"""Production-quality async scraper for marchespublics.gov.ma.

The portal runs on the PRADO PHP framework (PHP equivalent of ASP.NET WebForms).
Every interaction requires a PRADO_PAGESTATE ViewState token obtained via an
initial GET, then passed back on every POST.

Flow:
  1. GET /index.php?page=entreprise.EntrepriseAdvancedSearch  → extract PRADO_PAGESTATE
  2. POST with search criteria (date range) + PRADO_PAGESTATE  → results page 1
  3. For each subsequent page, POST with page-navigation postback

Output: data/raw/tenders/YYYY-MM-DD.jsonl  (one JSON object per line)

Usage:
    python -m ingestion.scrapers.marchespublics_scraper --date today
    python -m ingestion.scrapers.marchespublics_scraper --date 2024-05-01
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings

log = structlog.get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_BASE_URL = "https://www.marchespublics.gov.ma"
_SEARCH_URL = f"{_BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch"
_RATE_LIMIT_DELAY = 1.0 / settings.scraper_rate_limit_rps
_MAX_RETRIES = settings.scraper_max_retries

# 500 results per page = far fewer requests for large date ranges
_PAGE_SIZE = "500"

_USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
]

# PRADO field name constants (avoids scattered string literals)
_F_STATE = "PRADO_PAGESTATE"
_F_TARGET = "PRADO_POSTBACK_TARGET"
_F_PARAM = "PRADO_POSTBACK_PARAMETER"
_F_DATE_START = "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeStart"
_F_DATE_END = "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeEnd"
_F_SEARCH_BTN = "ctl0$CONTENU_PAGE$AdvancedSearch$lancerRecherche"
_F_SEARCH_TYPE = "ctl0$CONTENU_PAGE$AdvancedSearch$type_rechercheEntite"
_F_PAGE_SIZE_TOP = "ctl0$CONTENU_PAGE$resultSearch$listePageSizeTop"
_F_PAGE_NUM_TOP = "ctl0$CONTENU_PAGE$resultSearch$numPageTop"
_F_PAGE_BTN_TOP = "ctl0$CONTENU_PAGE$resultSearch$DefaultButtonTop"


# ── Pydantic data contract ───────────────────────────────────────────────────


class Tender(BaseModel):
    """A single public tender listing from marchespublics.gov.ma."""

    reference: str = Field(..., description="Unique tender reference (Référence)")
    contracting_authority: str = Field(..., description="Acheteur public")
    object: str = Field(..., description="Objet du marché")
    tender_type: str = Field(..., description="travaux | fournitures | services | autre")
    procedure_type: str = Field(default="", description="AOO, AMI, CAO, etc.")
    publication_date: date | None = None
    deadline_date: date | None = None
    wilaya: str | None = None
    detail_url: str = Field(default="")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    raw_hash: str = Field(default="")

    @field_validator("tender_type", mode="before")
    @classmethod
    def normalise_type(cls, v: str) -> str:
        """Map French category labels to canonical values."""
        mapping = {"travaux": "travaux", "fournitures": "fournitures", "services": "services"}
        lower = v.lower().strip()
        for key, canonical in mapping.items():
            if key in lower:
                return canonical
        return "autre"


# ── PRADO session helpers ────────────────────────────────────────────────────


def _get_prado_state(soup: BeautifulSoup) -> str:
    """Extract the PRADO_PAGESTATE hidden input value from a parsed page."""
    tag = soup.find("input", {"name": _F_STATE})
    if not isinstance(tag, Tag):
        raise ValueError("PRADO_PAGESTATE not found in page")
    return tag.get("value", "")  # type: ignore[return-value]


def _base_form_fields(state: str) -> dict[str, str]:
    """Return the minimum PRADO form fields required on every POST."""
    return {
        _F_STATE: state,
        _F_TARGET: "",
        _F_PARAM: "",
    }


# ── Core scraper ─────────────────────────────────────────────────────────────


class MarchesPublicsScraper:
    """Async scraper for the Moroccan public tenders portal.

    Handles the PRADO ViewState session, rate limiting, retries,
    rotating user-agents, and automatic pagination.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_request_at: float = 0.0

    async def __aenter__(self) -> "MarchesPublicsScraper":
        """Open the shared HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(45.0),
            follow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "fr-MA,fr;q=0.9",
            },
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape(
        self,
        target_date: date,
        max_pages: int | None = None,
    ) -> list[Tender]:
        """Scrape tenders published on *target_date*.

        The portal ignores server-side date filters (PRADO ViewState overrides
        our POST values), so we filter client-side and stop early once a page
        contains no tenders matching *target_date*.

        Args:
            target_date: Only return tenders whose publication_date equals this.
            max_pages: Hard cap on pages fetched (safety valve for large runs).
                       ``None`` means no limit.

        Returns:
            A list of validated :class:`Tender` objects for *target_date*.
        """
        log.info("scrape_start", date=str(target_date), max_pages=max_pages)

        # Step 1: GET the search form to acquire PRADO session state
        html = await self._get(_SEARCH_URL)
        if html is None:
            log.error("initial_get_failed")
            return []
        soup = BeautifulSoup(html, "lxml")
        state = _get_prado_state(soup)

        # Step 2: POST — the date fields exist but are overridden by ViewState;
        # we still send them as a best-effort hint to the server.
        date_str = target_date.strftime("%d/%m/%Y")
        payload = {
            **_base_form_fields(state),
            _F_TARGET: _F_SEARCH_BTN,
            _F_DATE_START: date_str,
            _F_DATE_END: date_str,
            _F_SEARCH_BTN: "Lancer la recherche",
            _F_SEARCH_TYPE: "floue",
        }
        html = await self._post(_SEARCH_URL, payload)
        if html is None:
            log.error("search_post_failed", date=date_str)
            return []

        tenders: list[Tender] = []
        page = 1

        while True:
            soup = BeautifulSoup(html, "lxml")
            rows = self._parse_results(soup)

            if not rows:
                log.info("pagination_exhausted", last_page=page)
                break

            # Client-side date filter
            matched: list[Tender] = []
            has_future = False
            for row in rows:
                try:
                    t = Tender(**row)
                    if t.publication_date == target_date:
                        matched.append(t)
                    elif t.publication_date and t.publication_date > target_date:
                        has_future = True  # results not strictly ordered; keep going
                except Exception as exc:
                    log.warning("tender_parse_error", error=str(exc))

            tenders.extend(matched)
            log.info(
                "page_scraped",
                page=page,
                rows=len(rows),
                matched=len(matched),
                total=len(tenders),
            )

            # Early stop: if this page had no matches and no future-dated rows,
            # results are now older than target_date — no point continuing.
            if not matched and not has_future:
                log.info("early_stop", reason="page_older_than_target", page=page)
                break

            state = _get_prado_state(soup)
            total_pages = self._total_pages(soup)
            if page >= total_pages:
                log.info("pagination_exhausted", last_page=page)
                break
            if max_pages is not None and page >= max_pages:
                log.info("max_pages_reached", max_pages=max_pages)
                break

            page += 1
            payload = {
                **_base_form_fields(state),
                _F_TARGET: _F_PAGE_BTN_TOP,
                _F_PAGE_NUM_TOP: str(page),
                _F_PAGE_SIZE_TOP: _PAGE_SIZE,
            }
            html = await self._post(_SEARCH_URL, payload)
            if html is None:
                log.warning("page_fetch_failed", page=page)
                break

        log.info("scrape_complete", date=str(target_date), total=len(tenders))
        return tenders

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_results(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract tender rows from the PRADO results table.

        Uses stable PRADO element IDs rather than fragile CSS class selectors.
        Rows follow the pattern:
          ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctlN_<field>
        where N counts from 1 (ctl0 is the header row).
        """
        rows: list[dict[str, Any]] = []

        # Find row indices: look for all _reference span IDs
        ref_spans = soup.find_all(
            "span", id=re.compile(r"ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl\d+_reference$")
        )

        for span in ref_spans:
            row_id = re.search(r"ctl(\d+)_reference$", span["id"])
            if not row_id:
                continue
            n = row_id.group(1)
            prefix = f"ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl{n}"

            def _text(suffix: str) -> str:
                tag = soup.find(id=f"{prefix}_{suffix}")
                return tag.get_text(strip=True) if tag else ""

            def _detail_link() -> str:
                actions = soup.find(id=f"{prefix}_panelAction")
                if not actions:
                    return ""
                a = actions.find("a", href=lambda h: h and "EntrepriseDetailConsultation" in h)
                if a:
                    return urljoin(_BASE_URL, a["href"])
                return ""

            reference = span.get_text(strip=True)
            raw = reference + _text("panelBlocCategorie") + _text("panelBlocDenomination")
            raw_hash = hashlib.sha256(raw.encode()).hexdigest()

            # Publication date is in an anonymous <div> inside cell[1] of the row.
            # The panelBlocTypesProc div only holds the procedure label, not the date.
            proc_block = _text("panelBlocTypesProc")
            pub_date: date | None = None
            actions_div_early = soup.find(id=f"{prefix}_panelAction")
            if actions_div_early:
                tr_early = actions_div_early.find_parent("tr")
                if tr_early:
                    cells_early = tr_early.find_all("td")
                    if len(cells_early) >= 2:
                        pub_date = _extract_first_date(
                            cells_early[1].get_text(separator="|", strip=True)
                        )

            # Deadline: first token in the deadline cell (row cell[4])
            # Use the detail link cell to locate the row, then walk up to <tr>
            actions_div = soup.find(id=f"{prefix}_panelAction")
            deadline_date: date | None = None
            if actions_div:
                tr = actions_div.find_parent("tr")
                if tr:
                    cells = tr.find_all("td")
                    if len(cells) >= 5:
                        deadline_text = cells[4].get_text(separator="|", strip=True)
                        deadline_date = _extract_first_date(deadline_text)

            rows.append(
                {
                    "reference": reference,
                    "contracting_authority": _clean(_text("panelBlocDenomination")),
                    "object": _clean(_text("infosBullesObjet") or _text("panelBlocObjet")),
                    "tender_type": _text("panelBlocCategorie"),
                    "procedure_type": _clean(proc_block.split("|")[0] if "|" in proc_block else proc_block),
                    "publication_date": pub_date,
                    "deadline_date": deadline_date,
                    "wilaya": _first_wilaya(_text("panelBlocLieuxExec")),
                    "detail_url": _detail_link(),
                    "raw_hash": raw_hash,
                }
            )

        return rows

    @staticmethod
    def _total_pages(soup: BeautifulSoup) -> int:
        """Extract the total page count from the pagination widget."""
        tag = soup.find(id="ctl0_CONTENU_PAGE_resultSearch_nombrePageTop")
        if tag:
            try:
                return int(tag.get_text(strip=True))
            except ValueError:
                pass
        return 1

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _get(self, url: str) -> str | None:
        """GET *url* with retry and rate-limiting."""
        return await self._request("GET", url)

    async def _post(self, url: str, data: dict[str, str]) -> str | None:
        """POST to *url* with retry and rate-limiting."""
        return await self._request("POST", url, data=data)

    async def _request(
        self, method: str, url: str, data: dict[str, str] | None = None
    ) -> str | None:
        """Execute an HTTP request with tenacity retry and respectful pacing."""
        assert self._client is not None
        ua = random.choice(_USER_AGENTS)
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(_MAX_RETRIES),
                wait=wait_exponential(multiplier=1, min=2, max=30),
                reraise=True,
            ):
                with attempt:
                    await self._pace()
                    resp = await self._client.request(
                        method,
                        url,
                        data=data,
                        headers={"User-Agent": ua, "Referer": _BASE_URL},
                    )
                    resp.raise_for_status()
                    log.debug("http_ok", method=method, url=url, status=resp.status_code)
                    # Decode using the charset the server declared, falling
                    # back to UTF-8. Replace any unmappable bytes so a single
                    # bad byte never aborts the whole page.
                    encoding = resp.encoding or "utf-8"
                    return resp.content.decode(encoding, errors="replace")
        except RetryError as exc:
            log.error("request_failed", method=method, url=url, error=str(exc))
            return None

    async def _pace(self) -> None:
        """Sleep if needed to honour the configured requests-per-second limit."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _RATE_LIMIT_DELAY:
            await asyncio.sleep(_RATE_LIMIT_DELAY - elapsed)
        self._last_request_at = time.monotonic()


# ── Utilities ─────────────────────────────────────────────────────────────────


def _extract_last_date(text: str) -> date | None:
    """Return the last DD/MM/YYYY date found in *text*."""
    matches = re.findall(r"\d{2}/\d{2}/\d{4}", text)
    return _parse_date(matches[-1]) if matches else None


def _extract_first_date(text: str) -> date | None:
    """Return the first DD/MM/YYYY date found in *text*."""
    m = re.search(r"\d{2}/\d{2}/\d{4}", text)
    return _parse_date(m.group()) if m else None


def _parse_date(raw: str) -> date | None:
    """Parse DD/MM/YYYY or YYYY-MM-DD strings."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _first_wilaya(text: str) -> str | None:
    """Extract the first wilaya token from a location string like 'GUELMIM...GUELMIM'."""
    clean = text.replace("...", "|").replace(",", "|")
    parts = [p.strip() for p in clean.split("|") if p.strip() and p.strip() != "MAROC"]
    return parts[0] if parts else None


def _clean(text: str) -> str:
    """Remove PRADO label prefixes like 'Acheteur public :' and excess whitespace."""
    text = re.sub(r"^(Acheteur public|Objet)\s*:", "", text).strip()
    return " ".join(text.split())


# ── Persistence ───────────────────────────────────────────────────────────────


async def save_tenders(tenders: list[Tender], target_date: date) -> Path:
    """Write *tenders* to a JSONL file under data/raw/tenders/.

    Returns the path to the written file.
    """
    output_dir = Path(settings.data_raw_dir) / "tenders"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{target_date.isoformat()}.jsonl"

    # Deduplicate by reference — same tender can appear under multiple
    # announcement types (Avis d'Information, Attribution, etc.)
    seen: set[str] = set()
    unique = [t for t in tenders if not (t.reference in seen or seen.add(t.reference))]  # type: ignore[func-returns-value]
    log.info("deduplication", before=len(tenders), after=len(unique))

    with output_path.open("w", encoding="utf-8") as fh:
        for tender in unique:
            fh.write(tender.model_dump_json() + "\n")

    log.info("tenders_saved", path=str(output_path), count=len(tenders))
    return output_path


# ── CLI entrypoint ────────────────────────────────────────────────────────────


async def _main() -> None:
    """CLI entrypoint for manual and DAG-triggered runs."""
    parser = argparse.ArgumentParser(description="Scrape marchespublics.gov.ma")
    parser.add_argument(
        "--date",
        default="today",
        help="Target date in YYYY-MM-DD format, or 'today'",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to fetch (default: unlimited). Use 5-10 for quick daily runs.",
    )
    args = parser.parse_args()
    target_date = (
        date.today() if args.date == "today" else date.fromisoformat(args.date)
    )

    async with MarchesPublicsScraper() as scraper:
        tenders = await scraper.scrape(target_date, max_pages=args.max_pages)

    if tenders:
        path = await save_tenders(tenders, target_date)
        log.info("done", path=str(path), count=len(tenders))
    else:
        log.warning("no_tenders_found", date=str(target_date))


if __name__ == "__main__":
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(_main())
