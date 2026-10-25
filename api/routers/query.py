"""Natural-language query endpoint powered by the RAG narrator."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas.query import QueryRequest, QueryResponse, SourceCitation
from ml.rag.narrator import Narrator
from ml.rag.retriever import retrieve

log = structlog.get_logger(__name__)
router = APIRouter()

_narrator = Narrator()


@router.post("/", response_model=QueryResponse)
async def natural_language_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Accept a natural-language question and return an AI-generated answer
    grounded in the CivicLens tender database.

    The response includes the source tenders cited and a token usage summary.
    """
    log.info("nl_query", question=request.question[:80], language=request.language)

    # Step 1: retrieve relevant tenders from the warehouse
    chunks = await retrieve(request.question, db, top_k=8)

    # Step 2: generate a grounded answer with Claude
    result = await _narrator.answer(
        question=request.question,
        sources=chunks,
        language=request.language,
    )

    citations = [
        SourceCitation(
            document_id=s.document_id,
            title=s.title,
            excerpt=s.excerpt,
            relevance_score=s.relevance_score,
        )
        for s in result.sources
    ]

    return QueryResponse(
        answer=result.answer,
        sources=citations,
        confidence=min(1.0, len(chunks) / 5),  # simple proxy: more sources = higher confidence
        language=request.language,
    )
