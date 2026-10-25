"""Anomaly detection result endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas.anomaly import AnomalyListResponse, AnomalyRecord

log = structlog.get_logger(__name__)
router = APIRouter()

_VIEW = "public_staging.stg_tenders"

# Surfaces the actual signals the model trains on (ml/anomaly/features.py),
# so the UI can explain *why* a tender scored high instead of just repeating
# its title. Note: a duration-based signal (deadline_date - publication_date)
# was removed from both this query and the feature set — that field turned
# out to be the portal's listing display-end date, not the real bid deadline
# (confirmed against a live tender page), so it carried no real signal.
_ANOMALY_SQL = """
WITH authority_counts AS (
    SELECT contracting_authority, COUNT(*) AS authority_tender_count
    FROM {view}
    GROUP BY contracting_authority
),
global_stats AS (
    SELECT AVG(authority_tender_count) AS global_avg_authority_count
    FROM authority_counts
)
SELECT
    s.reference         AS tender_reference,
    a.anomaly_score,
    a.is_anomaly,
    a.scored_at         AS detected_at,
    s.tender_type       AS anomaly_type,
    s.object            AS object,
    s.region,
    s.wilaya,
    s.contracting_authority,
    s.publication_date,
    ac.authority_tender_count,
    gs.global_avg_authority_count
FROM public.anomaly_scores a
JOIN {view} s USING (reference)
JOIN authority_counts ac USING (contracting_authority)
CROSS JOIN global_stats gs
WHERE a.anomaly_score >= :min_score
  AND a.is_anomaly = true
  {{extra}}
ORDER BY a.anomaly_score DESC
LIMIT :limit OFFSET :offset
""".format(view=_VIEW)

_COUNT_SQL = """
SELECT count(*)
FROM public.anomaly_scores a
JOIN {view} s USING (reference)
WHERE a.anomaly_score >= :min_score
  AND a.is_anomaly = true
  {{extra}}
""".format(view=_VIEW)


def _explain(r: dict) -> str:
    """Render a human-readable reason from the real signal the model uses.

    Currently the only behaviorally meaningful feature is authority publishing
    volume (estimated_amount, single_bidder, and deadline-duration are either
    unpopulated placeholders or — for deadline — confirmed to be the wrong
    field entirely; see module docstring in ml/anomaly/features.py). Tender
    type and wilaya also feed the model but are categorical, not "unusual" in
    the deviation sense, so they aren't used to justify a flag here.
    """
    authority_count = r["authority_tender_count"]
    global_avg_count = r["global_avg_authority_count"] or 1.0
    volume_ratio = authority_count / global_avg_count if global_avg_count else 1.0

    if volume_ratio >= 2.0:
        return (
            f"Volume de publication inhabituel : cette autorité a publié {authority_count:.0f} marchés, "
            f"contre une moyenne de {global_avg_count:.0f} marchés par autorité."
        )
    return "Signalé par le modèle de détection d'anomalies (score élevé sans facteur dominant identifié)."


@router.get("/", response_model=AnomalyListResponse)
async def list_anomalies(
    region: Annotated[str | None, Query()] = None,
    min_score: Annotated[float, Query(ge=0.0, le=1.0)] = 0.5,
    date_from: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> AnomalyListResponse:
    """Return procurement anomalies ordered by anomaly score (highest first).

    Requires the anomaly model to have been trained via `python -m ml.anomaly.train`.
    """
    extra_conditions = []
    params: dict = {
        "min_score": min_score,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }

    if region:
        extra_conditions.append("AND upper(s.region) LIKE upper(:region)")
        params["region"] = f"%{region}%"
    if date_from:
        extra_conditions.append("AND s.publication_date >= :date_from")
        params["date_from"] = date_from

    extra = "\n".join(extra_conditions)

    try:
        count_result = await db.execute(
            text(_COUNT_SQL.format(extra=extra)), params
        )
        total = count_result.scalar_one()

        rows_result = await db.execute(
            text(_ANOMALY_SQL.format(extra=extra)), params
        )
        rows = rows_result.mappings().all()
    except Exception as exc:
        # Model not yet trained — return empty with a hint
        if "anomaly_scores" in str(exc):
            log.info("anomaly_scores_table_missing", hint="Run: python -m ml.anomaly.train")
            return AnomalyListResponse(items=[], total=0, page=page, page_size=page_size)
        raise

    items = [
        AnomalyRecord(
            tender_reference=r["tender_reference"],
            anomaly_score=round(r["anomaly_score"], 4),
            anomaly_type=r["anomaly_type"] or "unknown",
            explanation=_explain(r),
            detected_at=r["detected_at"],
            region=r["region"],
        )
        for r in rows
    ]

    log.info("list_anomalies", total=total, page=page, min_score=min_score)
    return AnomalyListResponse(items=items, total=total, page=page, page_size=page_size)
