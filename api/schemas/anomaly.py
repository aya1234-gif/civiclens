"""Pydantic response schemas for anomaly endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnomalyRecord(BaseModel):
    """A single flagged procurement anomaly."""

    tender_reference: str
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    anomaly_type: str  # e.g. "price_inflation", "single_bidder", "split_contract"
    explanation: str
    detected_at: datetime
    region: str | None = None


class AnomalyListResponse(BaseModel):
    """Paginated list of anomaly records."""

    items: list[AnomalyRecord]
    total: int
    page: int
    page_size: int
