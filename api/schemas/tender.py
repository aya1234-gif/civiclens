"""Pydantic response schemas for tender endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class TenderSummary(BaseModel):
    """A single tender record returned by the API."""

    model_config = {"from_attributes": True}

    reference: str
    contracting_authority: str | None = None
    object: str | None = None
    tender_type: str | None = None
    procedure_type: str | None = None
    publication_date: date | None = None
    deadline_date: date | None = None
    region: str | None = None
    wilaya: str | None = None
    source_url: str | None = None
    scraped_at: datetime | None = None
    # Populated only for tenders that have reached the award stage and whose
    # PV/award notice was successfully scraped — see ingestion/backfill_amounts.py.
    # None means "not yet available", not "zero".
    montant_mad: float | None = None
    attributaire: str | None = None


class TenderListResponse(BaseModel):
    """Paginated list of tender summaries."""

    items: list[TenderSummary]
    total: int
    page: int
    page_size: int
    pages: int = Field(default=0)

    @model_validator(mode="after")
    def compute_pages(self) -> "TenderListResponse":
        """Compute total page count after init."""
        if self.page_size > 0:
            self.pages = (self.total + self.page_size - 1) // self.page_size
        return self
