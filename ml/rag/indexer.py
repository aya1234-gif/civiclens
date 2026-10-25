"""Vector indexer for CivicLens documents.

Chunks PDF/text documents and stores embeddings in a pgvector table
for retrieval-augmented generation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings

log = structlog.get_logger(__name__)

_CHUNK_SIZE = 512  # characters per chunk
_CHUNK_OVERLAP = 64

_CREATE_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id          BIGSERIAL PRIMARY KEY,
    document_id TEXT        NOT NULL,
    title       TEXT        NOT NULL,
    excerpt     TEXT        NOT NULL,
    embedding   vector(1536),
    source_url  TEXT,
    indexed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
"""


class Indexer:
    """Chunk documents and write embeddings to the pgvector store."""

    def __init__(self) -> None:
        self._engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        self._sessions = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def initialise(self) -> None:
        """Create the document_chunks table and vector index if absent."""
        async with self._engine.begin() as conn:
            await conn.execute(text(_CREATE_TABLE_SQL))
        log.info("indexer_initialised")

    async def index_text(
        self, document_id: str, title: str, text_content: str, source_url: str = ""
    ) -> int:
        """Chunk *text_content*, embed each chunk, and upsert into the store.

        Returns the number of chunks indexed.
        """
        chunks = _chunk_text(text_content, _CHUNK_SIZE, _CHUNK_OVERLAP)
        log.info("indexing_document", document_id=document_id, chunks=len(chunks))

        count = 0
        for chunk in chunks:
            embedding = await self._embed(chunk)
            async with self._sessions() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO document_chunks
                            (document_id, title, excerpt, embedding, source_url)
                        VALUES (:doc_id, :title, :excerpt, :embedding, :url)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "doc_id": document_id,
                        "title": title,
                        "excerpt": chunk,
                        "embedding": str(embedding),
                        "url": source_url,
                    },
                )
                await session.commit()
            count += 1

        log.info("document_indexed", document_id=document_id, chunks=count)
        return count

    async def _embed(self, text_content: str) -> list[float]:
        """Return an embedding vector for *text_content* via the Anthropic API."""
        # Anthropic doesn't yet expose an embeddings endpoint; swap for your
        # preferred provider (OpenAI text-embedding-3-small, Cohere, etc.)
        # This stub returns a zero vector as placeholder.
        _ = text_content
        return [0.0] * 1536

    async def close(self) -> None:
        """Dispose connection pool."""
        await self._engine.dispose()


def _chunk_text(text_content: str, size: int, overlap: int) -> list[str]:
    """Split *text_content* into overlapping character chunks."""
    chunks: list[str] = []
    start = 0
    while start < len(text_content):
        end = start + size
        chunks.append(text_content[start:end])
        start += size - overlap
    return [c for c in chunks if c.strip()]
