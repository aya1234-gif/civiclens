"""Governance endpoints — audit log and bias audit."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db

router = APIRouter()


@router.get("/audit-log")
async def audit_log(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the most recent AI model inference records."""
    sql = text("""
        SELECT
            timestamp::text        AS ts,
            model_name,
            model_version,
            triggered_by,
            ROUND(inference_time_ms::numeric, 0)::int AS inference_ms,
            input_hash,
            output_hash
        FROM audit_log
        ORDER BY timestamp DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"limit": limit})
    return [dict(r) for r in result.mappings()]


@router.get("/bias-audit")
async def bias_audit(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Return anomaly flag-rate per region (per 1000 tenders)."""
    sql = text("""
        SELECT
            s.wilaya                               AS region,
            COUNT(*)                               AS total,
            SUM(CASE WHEN a.is_anomaly THEN 1 ELSE 0 END) AS flagged,
            ROUND(
                1000.0 * SUM(CASE WHEN a.is_anomaly THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 1
            )                                      AS rate_per_1000
        FROM public_staging.stg_tenders s
        LEFT JOIN public.anomaly_scores a USING (reference)
        WHERE s.wilaya IS NOT NULL
        GROUP BY s.wilaya
        HAVING COUNT(*) >= 5
        ORDER BY rate_per_1000 DESC NULLS LAST
        LIMIT 20
    """)
    result = await db.execute(sql)
    return [dict(r) for r in result.mappings()]
