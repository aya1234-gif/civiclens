"""Feature engineering for procurement anomaly detection.

Produces a feature matrix from the stg_tenders mart suitable for
PyOD / Isolation Forest training and inference.

Note: marchespublics.gov.ma listing pages do not expose estimated amounts —
those are only available inside individual tender detail pages.  Until we add
a detail-page scraper, amount-based features fall back to 0/1.0 defaults and
the model operates on geographic + authority-frequency signals.

`days_to_deadline` was removed (was: deadline_date - publication_date). The
scraper's "deadline_date" field turns out to be the portal's "date de fin
d'affichage" (listing display-end date), not the actual bid submission
deadline ("date et heure limite de remise des plis") — confirmed by fetching
a live tender detail page. 99.1% of tenders have an identical ~730-day value
for this field, so it carries no real signal and was driving false positives.
Re-add a duration feature once the scraper captures the real deadline field.
"""

from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger(__name__)

# Features used by the anomaly model — defined here to keep train/inference in sync
FEATURE_COLUMNS = [
    "estimated_amount_mad_log",
    "authority_tender_count",
    "is_single_bidder_flag",
    "tender_type_encoded",
    "wilaya_encoded",
    "days_to_real_deadline",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Transform a raw tenders DataFrame into the anomaly model feature matrix.

    Handles missing columns gracefully — the portal listing page doesn't expose
    estimated amounts, so amount-based features default to neutral values.

    Args:
        df: DataFrame with columns matching stg_tenders schema.

    Returns:
        DataFrame with :data:`FEATURE_COLUMNS` columns, same index as *df*.
    """
    import numpy as np

    out = pd.DataFrame(index=df.index)

    # ── Amount (optional — only available after detail-page scrape) ────────
    if "estimated_amount_mad" in df.columns:
        out["estimated_amount_mad_log"] = np.log1p(
            pd.to_numeric(df["estimated_amount_mad"], errors="coerce").fillna(0)
        )
    else:
        out["estimated_amount_mad_log"] = 0.0

    # ── Authority activity count (proxy for single-source concentration) ───
    if "contracting_authority" in df.columns:
        out["authority_tender_count"] = (
            df.groupby("contracting_authority")["reference"]
            .transform("count")
            .fillna(1)
            .astype(float)
        )
    else:
        out["authority_tender_count"] = 1.0

    # ── Single-bidder placeholder ─────────────────────────────────────────
    out["is_single_bidder_flag"] = 0.0

    # ── Tender type as ordinal ─────────────────────────────────────────────
    type_map = {"travaux": 2, "fournitures": 1, "services": 0, "autre": -1}
    if "tender_type" in df.columns:
        out["tender_type_encoded"] = (
            df["tender_type"].map(type_map).fillna(0).astype(float)
        )
    else:
        out["tender_type_encoded"] = 0.0

    # ── Wilaya label-encoded ───────────────────────────────────────────────
    if "wilaya" in df.columns:
        wilaya_codes = df["wilaya"].astype("category").cat.codes.astype(float)
        out["wilaya_encoded"] = wilaya_codes.fillna(-1)
    else:
        out["wilaya_encoded"] = -1.0

    # ── Real bid deadline duration (from tender_details enrichment) ───────
    # real_deadline is the actual submission deadline scraped from detail pages,
    # unlike the listing's deadline_date which is the display-end date (~730 days).
    if "real_deadline" in df.columns and "publication_date" in df.columns:
        pub = pd.to_datetime(df["publication_date"], errors="coerce")
        deadline = pd.to_datetime(df["real_deadline"], errors="coerce", utc=True).dt.tz_localize(None)
        days = (deadline - pub).dt.days
        # Only use rows where the duration is plausible (1–365 days)
        days = days.where((days >= 1) & (days <= 365))
        out["days_to_real_deadline"] = days.fillna(-1).astype(float)
    else:
        out["days_to_real_deadline"] = -1.0

    # Fill any remaining NaNs
    out = out.fillna(0.0)

    log.info("features_built", rows=len(out), columns=FEATURE_COLUMNS)
    return out[FEATURE_COLUMNS]
