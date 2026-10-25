"""Pydantic request/response schemas for the NL query endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """A natural-language question submitted by the user."""

    question: str = Field(..., min_length=5, max_length=1000)
    language: str = Field(default="fr", description="Response language: fr | ar | en")


class SourceCitation(BaseModel):
    """A document chunk cited by the RAG narrator."""

    document_id: str
    title: str
    excerpt: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    """AI-generated answer with source citations."""

    answer: str
    sources: list[SourceCitation]
    confidence: float = Field(..., ge=0.0, le=1.0)
    language: str = "fr"
