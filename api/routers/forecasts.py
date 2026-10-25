"""Service gap forecast endpoints."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Query

from api.schemas.forecast import ForecastResponse

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/gaps", response_model=ForecastResponse)
async def get_service_gaps(
    region: Annotated[str | None, Query(description="Filter by region")] = None,
    horizon_months: Annotated[int, Query(ge=1, le=24)] = 6,
) -> ForecastResponse:
    """Return predicted service delivery gaps for the given region and horizon."""
    log.info("get_service_gaps", region=region, horizon=horizon_months)
    # TODO: invoke ml.forecasting.gap_model
    return ForecastResponse(region=region or "all", predictions=[])
