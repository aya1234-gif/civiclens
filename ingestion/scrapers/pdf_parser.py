"""PDF parsing utilities for Moroccan government documents.

Uses pdfplumber for text extraction and camelot for table extraction.
Handles the common pattern: budget laws and financial bulletins as scanned PDFs.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pdfplumber
import structlog

log = structlog.get_logger(__name__)


class PdfParser:
    """Extract text and tables from government PDF documents.

    Falls back gracefully when a page contains only scanned images.
    """

    async def extract_text(self, path: Path) -> str:
        """Return the full text content of a PDF, page by page."""
        return await asyncio.to_thread(self._extract_text_sync, path)

    async def extract_tables(self, path: Path) -> list[list[list[str | None]]]:
        """Return all tables found in the PDF as lists of rows."""
        return await asyncio.to_thread(self._extract_tables_sync, path)

    def _extract_text_sync(self, path: Path) -> str:
        """Synchronous text extraction — run via asyncio.to_thread."""
        pages: list[str] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    log.debug("empty_page", path=str(path), page=i)
                pages.append(text)
        full_text = "\n\n".join(pages)
        log.info("pdf_text_extracted", path=str(path), chars=len(full_text))
        return full_text

    def _extract_tables_sync(self, path: Path) -> list[list[list[str | None]]]:
        """Synchronous table extraction using pdfplumber's lattice detector."""
        all_tables: list[list[list[str | None]]] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    log.debug("tables_found", page=i, count=len(tables))
                    all_tables.extend(tables)
        log.info("pdf_tables_extracted", path=str(path), tables=len(all_tables))
        return all_tables
