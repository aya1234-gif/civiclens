"""Pydantic response schemas for forecast endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class GapPrediction(BaseModel):
    """A single service gap prediction for a region/month."""

    period: date
    service_category: str
    predicted_gap_score: float = Field(..., ge=0.0, le=1.0)
    confidence_interval_low: float
    confidence_interval_high: float
    contributing_features: dict[str, float] = Field(default_factory=dict)


class ForecastResponse(BaseModel):
    """Forecast results for a given region and horizon."""

    region: str
    predictions: list[GapPrediction]
