"""Scraper for hcp.ma — Haut-Commissariat au Plan.

Downloads Excel/ZIP statistical datasets (census, economic indicators).
"""

from __future__ import annotations

import asyncio
import io
import zipfile
from pathlib import Path
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from config.settings import settings

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.hcp.ma"
_STATS_PATHS = [
    "/page-statistiques-sociales.html",
    "/page-statistiques-economiques.html",
]


class HcpScraper:
    """Async scraper for hcp.ma statistical publications.

    Finds Excel and ZIP download links and saves them to data/raw/hcp/.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HcpScraper":
        """Open the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=120.0,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    async def scrape_all(self) -> list[Path]:
        """Scrape all stats pages and download new files.

        Returns paths of saved files.
        """
        saved: list[Path] = []
        for path in _STATS_PATHS:
            links = await self._extract_download_links(path)
            for url in links:
                dest = self._dest_path(url)
                if dest.exists():
                    log.debug("skipping_existing", path=str(dest))
                    continue
                saved.append(await self._download(url, dest))
        return saved

    async def _extract_download_links(self, path: str) -> list[str]:
        """Return all Excel/ZIP download URLs found on a stats page."""
        assert self._client is not None
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.scraper_max_retries),
            wait=wait_exponential(min=2, max=30),
            reraise=True,
        ):
            with attempt:
                resp = await self._client.get(path)
                resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        links = [
            a["href"]
            for a in soup.find_all("a", href=True)
            if any(ext in a["href"].lower() for ext in (".xlsx", ".xls", ".zip"))
        ]
        log.info("download_links_found", page=path, count=len(links))
        return [l if l.startswith("http") else f"{_BASE_URL}{l}" for l in links]

    async def _download(self, url: str, dest: Path) -> Path:
        """Download *url* to *dest*, extracting ZIPs in-place."""
        assert self._client is not None
        dest.parent.mkdir(parents=True, exist_ok=True)
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.scraper_max_retries),
            wait=wait_exponential(min=2, max=60),
            reraise=True,
        ):
            with attempt:
                async with self._client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    raw = await resp.aread()

        if url.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                zf.extractall(dest.parent)
            log.info("zip_extracted", url=url, dest=str(dest.parent))
        else:
            dest.write_bytes(raw)
            log.info("file_saved", url=url, dest=str(dest))

        return dest

    def _dest_path(self, url: str) -> Path:
        """Map a remote URL to a local path under data/raw/hcp/."""
        filename = url.split("/")[-1].split("?")[0] or "unknown"
        return Path(settings.data_raw_dir) / "hcp" / filename
