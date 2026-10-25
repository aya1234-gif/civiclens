"""Scraper for data.gov.ma — Morocco's national open data portal (CKAN).

Downloads datasets by tag/group and saves them to data/raw/govma/.
Priority datasets: budget, census, health facilities, education.

Usage:
    python -m ingestion.scrapers.govma_scraper --tags budget,census
    python -m ingestion.scrapers.govma_scraper --all
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path
from typing import Any

import httpx
import structlog
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from config.settings import settings

log = structlog.get_logger(__name__)

_CKAN_BASE = "https://data.gov.ma/data/api/3/action"
_RATE_DELAY = 1.0 / settings.scraper_rate_limit_rps

# Moroccan open data priority tags
_PRIORITY_TAGS = [
    "budget",
    "finances-publiques",
    "recensement",
    "population",
    "sante",
    "education",
    "infrastructures",
    "marches-publics",
]


class GovMaScraper:
    """Async CKAN client for data.gov.ma.

    Searches for datasets by tag, downloads CSV/Excel resources,
    and writes them to data/raw/govma/<tag>/<filename>.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_request_at: float = 0.0

    async def __aenter__(self) -> "GovMaScraper":
        """Open the HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            follow_redirects=True,
            headers={"User-Agent": "CivicLens/0.1 (data.gov.ma open data consumer)"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    async def search_datasets(
        self,
        tags: list[str] | None = None,
        rows: int = 100,
    ) -> list[dict[str, Any]]:
        """Return dataset metadata from the CKAN catalogue.

        Args:
            tags: Filter by tag names. None returns all datasets.
            rows: Max datasets to return per tag.

        Returns:
            List of CKAN dataset dicts.
        """
        results: list[dict[str, Any]] = []
        search_tags = tags or [""]

        for tag in search_tags:
            params: dict[str, Any] = {"rows": rows, "start": 0}
            if tag:
                params["fq"] = f'tags:"{tag}"'

            data = await self._ckan_call("package_search", params)
            datasets = data.get("result", {}).get("results", [])
            log.info("datasets_found", tag=tag or "all", count=len(datasets))
            results.extend(datasets)

        # Deduplicate by dataset id
        seen: set[str] = set()
        unique = [d for d in results if not (d["id"] in seen or seen.add(d["id"]))]  # type: ignore[func-returns-value]
        return unique

    async def download_dataset(
        self, dataset: dict[str, Any], tag: str = "misc"
    ) -> list[Path]:
        """Download all CSV/Excel resources from a CKAN dataset.

        Args:
            dataset: CKAN dataset dict from :meth:`search_datasets`.
            tag: Subdirectory name under data/raw/govma/.

        Returns:
            List of paths to downloaded files.
        """
        saved: list[Path] = []
        resources = dataset.get("resources", [])

        for resource in resources:
            fmt = (resource.get("format") or "").upper()
            if fmt not in ("CSV", "XLS", "XLSX", "JSON"):
                continue

            url = resource.get("url", "")
            if not url:
                continue

            filename = resource.get("name") or url.split("/")[-1]
            filename = filename.replace("/", "_").replace(" ", "_")
            if not any(filename.lower().endswith(ext) for ext in (".csv", ".xls", ".xlsx", ".json")):
                filename += f".{fmt.lower()}"

            dest = Path(settings.data_raw_dir) / "govma" / tag / filename
            if dest.exists():
                log.debug("resource_exists", path=str(dest))
                continue

            try:
                path = await self._download_file(url, dest)
                saved.append(path)
            except Exception as exc:
                log.warning("resource_download_failed", url=url, error=str(exc))

        return saved

    async def scrape_priority_datasets(self) -> dict[str, list[Path]]:
        """Download all priority datasets (budget, census, health, education).

        Returns:
            Dict mapping tag name → list of downloaded file paths.
        """
        all_paths: dict[str, list[Path]] = {}

        datasets = await self.search_datasets(tags=_PRIORITY_TAGS, rows=50)
        log.info("priority_datasets_total", count=len(datasets))

        for dataset in datasets:
            # Find the most relevant tag for this dataset
            dataset_tags = [t.get("name", "") for t in dataset.get("tags", [])]
            tag = next(
                (t for t in _PRIORITY_TAGS if t in dataset_tags),
                "misc",
            )
            paths = await self.download_dataset(dataset, tag=tag)
            all_paths.setdefault(tag, []).extend(paths)

        total = sum(len(v) for v in all_paths.values())
        log.info("govma_scrape_complete", total_files=total)
        return all_paths

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _ckan_call(
        self, action: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a CKAN API action and return the response JSON."""
        assert self._client is not None
        url = f"{_CKAN_BASE}/{action}"
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.scraper_max_retries),
            wait=wait_exponential(min=2, max=30),
            reraise=True,
        ):
            with attempt:
                await self._pace()
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if not data.get("success"):
                    raise ValueError(f"CKAN error: {data.get('error')}")
                log.debug("ckan_call_ok", action=action, params=params)
                return data  # type: ignore[return-value]
        return {}

    async def _download_file(self, url: str, dest: Path) -> Path:
        """Stream-download a file to *dest*."""
        assert self._client is not None
        dest.parent.mkdir(parents=True, exist_ok=True)
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.scraper_max_retries),
            wait=wait_exponential(min=2, max=30),
            reraise=True,
        ):
            with attempt:
                await self._pace()
                async with self._client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    with dest.open("wb") as fh:
                        async for chunk in resp.aiter_bytes(65536):
                            fh.write(chunk)
        log.info("file_downloaded", url=url, dest=str(dest))
        return dest

    async def _pace(self) -> None:
        """Respect the configured rate limit."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _RATE_DELAY:
            await asyncio.sleep(_RATE_DELAY - elapsed)
        self._last_request_at = time.monotonic()


async def _main() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    parser = argparse.ArgumentParser(description="Scrape data.gov.ma open datasets")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tags", help="Comma-separated tags, e.g. budget,census")
    group.add_argument("--all", action="store_true", help="Download all priority datasets")
    args = parser.parse_args()

    async with GovMaScraper() as scraper:
        if args.all:
            await scraper.scrape_priority_datasets()
        else:
            tags = [t.strip() for t in args.tags.split(",")]
            datasets = await scraper.search_datasets(tags=tags)
            for ds in datasets:
                await scraper.download_dataset(ds, tag=tags[0])


if __name__ == "__main__":
    asyncio.run(_main())
