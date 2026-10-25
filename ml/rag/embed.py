"""Embed all stg_tenders locally using sentence-transformers.

Model: paraphrase-multilingual-MiniLM-L12-v2
- 384-dim vectors, multilingual (French + Arabic)
- Runs fully offline, no API needed

Stores embeddings as float8[] in public.tender_embeddings.
Cosine similarity search done in SQL — no pgvector needed.

Usage:
    python -m ml.rag.embed              # embed only new/missing tenders
    python -m ml.rag.embed --rebuild    # re-embed everything
"""

from __future__ import annotations

import argparse
import asyncio
import os
import time

import asyncpg
import structlog
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
log = structlog.get_logger(__name__)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
BATCH_SIZE = 256

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS public.tender_embeddings (
    reference    TEXT PRIMARY KEY,
    embedding    float8[],
    embedded_at  TIMESTAMPTZ DEFAULT NOW(),
    model        TEXT
);
"""

_LOAD_MISSING = """
SELECT s.reference, s.object, s.contracting_authority,
       s.tender_type, s.region, s.wilaya
FROM public_staging.stg_tenders s
LEFT JOIN public.tender_embeddings e USING (reference)
WHERE s.publication_date IS NOT NULL
  AND e.reference IS NULL
"""

_LOAD_ALL = """
SELECT s.reference, s.object, s.contracting_authority,
       s.tender_type, s.region, s.wilaya
FROM public_staging.stg_tenders s
WHERE s.publication_date IS NOT NULL
"""

_UPSERT = """
INSERT INTO public.tender_embeddings (reference, embedding, model)
VALUES ($1, $2, $3)
ON CONFLICT (reference) DO UPDATE
  SET embedding   = EXCLUDED.embedding,
      embedded_at = NOW(),
      model       = EXCLUDED.model
"""


def _tender_text(row: dict) -> str:
    parts = [
        row.get("object") or "",
        row.get("contracting_authority") or "",
        row.get("tender_type") or "",
        row.get("region") or "",
        row.get("wilaya") or "",
    ]
    return " | ".join(p for p in parts if p)


async def embed_tenders(rebuild: bool = False) -> None:
    db_url = (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    conn = await asyncpg.connect(db_url)
    model = SentenceTransformer(MODEL_NAME)

    try:
        await conn.execute(_CREATE_TABLE)

        rows = await conn.fetch(_LOAD_ALL if rebuild else _LOAD_MISSING)
        if not rows:
            log.info("embed.nothing_to_do")
            return

        log.info("embed.start", n=len(rows), model=MODEL_NAME, rebuild=rebuild)
        t0 = time.perf_counter()
        total = 0

        for i in range(0, len(rows), BATCH_SIZE):
            batch = [dict(r) for r in rows[i : i + BATCH_SIZE]]
            texts = [_tender_text(r) for r in batch]
            vectors = model.encode(texts, show_progress_bar=False)

            async with conn.transaction():
                for row, vec in zip(batch, vectors):
                    await conn.execute(
                        _UPSERT,
                        row["reference"],
                        vec.tolist(),
                        MODEL_NAME,
                    )

            total += len(batch)
            log.info("embed.progress", done=total, total=len(rows),
                     elapsed_s=round(time.perf_counter() - t0, 1))

        log.info("embed.complete", total=total,
                 elapsed_s=round(time.perf_counter() - t0, 1))

    finally:
        await conn.close()


if __name__ == "__main__":
    import structlog
    structlog.configure(processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ])
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    asyncio.run(embed_tenders(rebuild=args.rebuild))
