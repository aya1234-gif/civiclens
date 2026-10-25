"""Extract awarded contract amounts from tender PV/award-notice PDFs.

marchespublics.gov.ma masks the "Estimation" budget field for unauthenticated
visitors (confirmed: the field renders literally as "@@@@" server-side, even
on a fresh session). The actual contract value is, however, available for
tenders that have reached the award stage, inside the downloadable PV
(procès-verbal) or "Résultats définitifs" PDF attached to each tender —
specifically the "Montant de l'acte d'engagement" / "Montant de l'offre
retenue" field for the winning bidder.

These PDFs are mostly scanned images (no embedded text layer), so this module
OCRs them. The download link itself is only present after a PRADO AJAX
callback fires, which a plain HTTP scraper can't trigger — hence Playwright.

Coverage is partial by design (v1): only documents matching one of the two
known field-label patterns below will yield an amount. Tenders without a PV
yet (still open for bids) will return None — that's expected, not a bug.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import pytesseract
import structlog
from PIL import Image
from playwright.async_api import async_playwright

log = structlog.get_logger(__name__)

_DOWNLOAD_SELECTOR = 'a[href*="EntrepriseDownloadAvisJAL"]'

# Two known field-label patterns seen across PV templates. Each is tried in
# order; the first that matches wins. Amounts use French formatting
# ("99 696,00") — space as thousands separator, comma as decimal point.
# Shared building block for a French-formatted amount, e.g. "420 000,00" or
# "420.000,00" (both space and period are used as thousands separators across
# different templates). The negative lookbehind prevents matching a fragment
# of a longer number — without it, "420.000,00" would wrongly match just
# "000,00" => 0.0, which happened in testing.
_AMOUNT_NUM = r"(?<![\d.])\d{1,3}(?:[ \xa0.]\d{3})*,\d{2}"

_AMOUNT_PATTERNS = [
    # "Concurrent retenu" table: "TOP ELECTRICITE 99 696,00" right after
    # "Attributaire ... Montant de l'acte d'engagement" header.
    re.compile(
        r"Attributaire.{0,40}Montant.{0,60}?\n+([A-ZÀ-Ü][A-Za-zÀ-ÿ0-9 &\-\.'’]{2,80}?)\s+"
        rf"({_AMOUNT_NUM})",
        re.DOTALL,
    ),
    # "Résultats définitifs" template: amount followed by "dh TTC", possibly
    # with other table-cell text in between (OCR sometimes interleaves
    # adjacent columns, e.g. a date cell, before the currency cell).
    re.compile(
        rf"({_AMOUNT_NUM})[^\n]{{0,80}}?dh\s*TTC",
        re.IGNORECASE | re.DOTALL,
    ),
    # "Résultats définitifs" template (table, header/value on separate rows):
    # "Montant de l'offre retenue ... En DH TTC" followed, after the winner's
    # name, by a French-formatted number. Looser than the patterns above
    # because OCR on these tables is noisy (e.g. "11" misread as "1;") — this
    # is a best-effort fallback, hence its own "source" tag for auditability.
    re.compile(
        r"l['’]offre retenue.{0,300}?([\d][\d \xa0;,\.]{2,20}\d,\d{2})",
        re.IGNORECASE | re.DOTALL,
    ),
]



@dataclass
class AmountResult:
    reference: str
    attributaire: str | None
    montant_mad: float
    source: str  # which pattern/template matched


def _parse_amount_text(text: str, reference: str) -> AmountResult | None:
    m = _AMOUNT_PATTERNS[0].search(text)
    if m:
        name, amount_str = m.group(1).strip(), m.group(2)
        return AmountResult(
            reference=reference,
            attributaire=name,
            montant_mad=_to_float(amount_str),
            source="attributaire_table",
        )

    m = _AMOUNT_PATTERNS[1].search(text)
    if m:
        return AmountResult(
            reference=reference,
            attributaire=None,
            montant_mad=_to_float(m.group(1)),
            source="offre_retenue",
        )

    m = _AMOUNT_PATTERNS[2].search(text)
    if m:
        try:
            amount = _to_float(m.group(1))
        except ValueError:
            return None
        return AmountResult(
            reference=reference,
            attributaire=None,
            montant_mad=amount,
            source="offre_retenue_table_ocr",
        )

    return None


def _to_float(amount_str: str) -> float:
    # Strip thousands separators (regular + non-breaking space, and stray
    # OCR noise like semicolons/periods) before converting the decimal comma.
    whole, _, decimals = amount_str.rpartition(",")
    cleaned_whole = re.sub(r"[\s\xa0;.]", "", whole)
    return float(f"{cleaned_whole}.{decimals}")


_FRENCH_MARKERS = ("de", "le", "la", "des", "du", "et", "royaume", "maroc", "montant", "offre")


def _ocr_with_orientation_fix(img: Image.Image) -> str:
    """OCR an image at all 4 rotations and keep whichever yields readable French.

    pytesseract.image_to_osd() was tried first but proved unreliable on these
    scans — on a confirmed upside-down sample it reported "Rotate: 90" with
    confidence 6.15 (and guessed the script as Cyrillic), which is wrong; the
    correct rotation was 180. Scoring all 4 orientations by common French word
    frequency reliably picked the right one in testing, at the cost of 4x the
    OCR calls per scanned page.
    """
    best_text, best_score = "", -1
    for angle in (0, 90, 180, 270):
        rotated = img.rotate(angle, expand=True) if angle else img
        text = pytesseract.image_to_string(rotated, lang="fra")
        score = sum(text.lower().count(w) for w in _FRENCH_MARKERS)
        if score > best_score:
            best_text, best_score = text, score
    return best_text


async def extract_amount(reference: str, source_url: str) -> AmountResult | None:
    """Fetch a tender's PV/award PDF and extract the awarded amount, if any.

    Returns None if no download link exists (tender not yet awarded), no PDF
    pattern matches (unknown template), or the page/PDF fails to load.
    """
    import pdfplumber

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto(source_url, wait_until="networkidle", timeout=30_000)
            links = await page.eval_on_selector_all(
                _DOWNLOAD_SELECTOR, "els => els.map(e => e.href)"
            )
            real_links = [href for href in links if href and not href.endswith("idAvis=")]
            if not real_links:
                log.info("no_pv_download_link", reference=reference)
                return None

            async with page.expect_download(timeout=15_000) as dl_info:
                await page.click(_DOWNLOAD_SELECTOR)
            download = await dl_info.value
            pdf_path = await download.path()
            if pdf_path is None:
                return None

            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for pdf_page in pdf.pages:
                    if pdf_page.chars:
                        full_text += pdf_page.extract_text() or ""
                    else:
                        img = pdf_page.to_image(resolution=150).original
                        full_text += _ocr_with_orientation_fix(img)
                    full_text += "\n"

            result = _parse_amount_text(full_text, reference)
            if result is None:
                log.info("no_amount_pattern_matched", reference=reference)
            return result
        except Exception as exc:
            log.warning("amount_extraction_failed", reference=reference, error=str(exc))
            return None
        finally:
            await browser.close()
