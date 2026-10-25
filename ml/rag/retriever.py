"""Context retriever: semantic vector search over tender embeddings.

Fetches all embeddings from Postgres, computes cosine similarity in Python
with numpy (fast for <50k rows), returns top-k most relevant tenders.
Falls back to most-recent tenders if the embeddings table is empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_FETCH_EMBEDDINGS = text("""
SELECT e.reference, e.embedding,
       s.contracting_authority, s.object, s.tender_type,
       s.procedure_type, s.publication_date::text, s.region,
       s.wilaya, s.source_url
FROM public.tender_embeddings e
JOIN public_staging.stg_tenders s USING (reference)
""")

_RECENT_SQL = text("""
SELECT reference, contracting_authority, object, tender_type,
       procedure_type, publication_date::text, region, wilaya, source_url
FROM public_staging.stg_tenders
ORDER BY publication_date DESC
LIMIT :limit
""")

_HAS_EMBEDDINGS = text("SELECT COUNT(*) FROM public.tender_embeddings")


@dataclass
class TenderChunk:
    document_id: str
    title: str
    excerpt: str
    relevance_score: float = 1.0


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def _embed_question(question: str) -> np.ndarray:
    vec = _get_model().encode([question], show_progress_bar=False)
    return vec[0]


def _cosine_top_k(
    qvec: np.ndarray,
    refs: list[str],
    matrix: np.ndarray,
    top_k: int,
) -> list[tuple[str, float]]:
    """Return (reference, score) pairs sorted by cosine similarity."""
    norms = np.linalg.norm(matrix, axis=1)
    qnorm = np.linalg.norm(qvec)
    with np.errstate(divide="ignore", invalid="ignore"):
        sims = (matrix @ qvec) / (norms * qnorm + 1e-9)
    idx = np.argsort(sims)[::-1][:top_k]
    return [(refs[i], float(sims[i])) for i in idx]


def _make_chunk(row: dict, score: float) -> TenderChunk:
    excerpt = (
        f"Référence: {row['reference']}\n"
        f"Acheteur: {row['contracting_authority']}\n"
        f"Objet: {row['object']}\n"
        f"Type: {row['tender_type']} — {row['procedure_type']}\n"
        f"Région: {row['region']}\n"
        f"Publié le: {row['publication_date']}\n"
        f"Lien: {row['source_url']}"
    )
    return TenderChunk(
        document_id=row["reference"],
        title=(row["object"] or row["reference"])[:80],
        excerpt=excerpt,
        relevance_score=round(score, 4),
    )


async def retrieve(
    question: str,
    db: AsyncSession,
    top_k: int = 8,
) -> list[TenderChunk]:
    """Return the top-k semantically similar tenders for *question*."""

    count = (await db.execute(_HAS_EMBEDDINGS)).scalar()
    if not count:
        rows = (await db.execute(_RECENT_SQL, {"limit": top_k})).mappings().all()
        return [_make_chunk(dict(r), 1.0) for r in rows]

    rows = (await db.execute(_FETCH_EMBEDDINGS)).mappings().all()
    rows = [dict(r) for r in rows]

    refs = [r["reference"] for r in rows]
    matrix = np.array([r["embedding"] for r in rows], dtype=np.float32)
    row_by_ref = {r["reference"]: r for r in rows}

    qvec = _embed_question(question).astype(np.float32)
    top = _cosine_top_k(qvec, refs, matrix, top_k)

    return [_make_chunk(row_by_ref[ref], score) for ref, score in top]
