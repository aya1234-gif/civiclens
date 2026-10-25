"""Tender listing and detail endpoints — backed by stg_tenders."""

from __future__ import annotations

from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas.tender import TenderListResponse, TenderSummary

log = structlog.get_logger(__name__)
router = APIRouter()

# stg_tenders is a view in the public schema created by dbt
_TABLE = text("public.stg_tenders")
_VIEW = "public_staging.stg_tenders"


def _base_query() -> str:
    return f"""
        SELECT
            s.reference,
            s.contracting_authority,
            s.object,
            s.tender_type,
            s.procedure_type,
            s.publication_date,
            s.deadline_date,
            s.region,
            s.wilaya,
            s.source_url,
            s.scraped_at,
            ta.montant_mad,
            ta.attributaire
        FROM {_VIEW} s
        LEFT JOIN public.tender_amounts ta USING (reference)
    """


@router.get("/", response_model=TenderListResponse)
async def list_tenders(
    region: Annotated[str | None, Query(description="Filter by region name")] = None,
    wilaya: Annotated[str | None, Query(description="Filter by wilaya name")] = None,
    tender_type: Annotated[
        str | None, Query(description="travaux | fournitures | services | autre")
    ] = None,
    date_from: Annotated[date | None, Query(description="Publication date from (YYYY-MM-DD)")] = None,
    date_to: Annotated[date | None, Query(description="Publication date to (YYYY-MM-DD)")] = None,
    q: Annotated[str | None, Query(description="Full-text search on object")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> TenderListResponse:
    """Return paginated tender listings with optional filters."""

    # Build WHERE clauses dynamically
    conditions = ["1=1"]
    params: dict = {}

    if region:
        conditions.append("upper(region) LIKE upper(:region)")
        params["region"] = f"%{region}%"
    if wilaya:
        conditions.append("upper(wilaya) LIKE upper(:wilaya)")
        params["wilaya"] = f"%{wilaya}%"
    if tender_type:
        conditions.append("tender_type = :tender_type")
        params["tender_type"] = tender_type.lower()
    if date_from:
        conditions.append("publication_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("publication_date <= :date_to")
        params["date_to"] = date_to
    if q:
        conditions.append("object ILIKE :q")
        params["q"] = f"%{q}%"

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size

    count_sql = text(f"SELECT count(*) FROM {_VIEW} WHERE {where}")
    data_sql = text(
        f"{_base_query()} WHERE {where}"
        f" ORDER BY publication_date DESC, reference"
        f" LIMIT :limit OFFSET :offset"
    )
    params["limit"] = page_size
    params["offset"] = offset

    total_result = await db.execute(count_sql, params)
    total = total_result.scalar_one()

    rows_result = await db.execute(data_sql, params)
    rows = rows_result.mappings().all()

    items = [TenderSummary(**dict(row)) for row in rows]

    log.info(
        "list_tenders",
        total=total,
        page=page,
        filters={"region": region, "tender_type": tender_type, "q": q},
    )
    return TenderListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{reference}", response_model=TenderSummary)
async def get_tender(
    reference: str,
    db: AsyncSession = Depends(get_db),
) -> TenderSummary:
    """Return details for a single tender by reference number."""
    sql = text(f"{_base_query()} WHERE reference = :reference LIMIT 1")
    result = await db.execute(sql, {"reference": reference})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tender '{reference}' not found")
    log.info("get_tender", reference=reference)
    return TenderSummary(**dict(row))
