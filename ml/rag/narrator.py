"""RAG narrator: answer governance questions grounded in CivicLens data.

Retrieves relevant tender chunks from the warehouse, then asks Claude to
generate a cited, grounded answer. Supports French, Arabic, and English.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from anthropic import AsyncAnthropic

from config.settings import settings
from ml.rag.retriever import TenderChunk

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """Tu es CivicLens, un assistant expert en marchés publics marocains.
Tu réponds en te basant UNIQUEMENT sur les documents fournis ci-dessous.
Pour chaque affirmation, cite la référence du marché entre crochets, ex: [REF-123].
Si la réponse ne figure pas dans les documents, dis-le clairement sans inventer.
Sois concis, factuel et précis. Réponds dans la langue de la question."""


@dataclass
class NarratorResponse:
    """Structured response from the RAG narrator."""

    answer: str
    sources: list[TenderChunk]
    model: str
    input_tokens: int
    output_tokens: int


class Narrator:
    """Generate grounded natural-language governance insights.

    Uses a two-step RAG pipeline:
      1. Retrieve relevant tender chunks from the warehouse (via retriever.py)
      2. Pass chunks as context to Claude and stream back a cited answer
    """

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def answer(
        self,
        question: str,
        sources: list[TenderChunk],
        language: str = "fr",
    ) -> NarratorResponse:
        """Generate a cited answer to *question* using *sources* as context.

        Args:
            question: Natural-language question.
            sources: Retrieved tender chunks from the warehouse.
            language: Target language hint included in the user message.

        Returns:
            A :class:`NarratorResponse` with the answer and cited sources.
        """
        if not sources:
            return NarratorResponse(
                answer="Aucun marché trouvé dans la base de données pour cette question.",
                sources=[],
                model="none",
                input_tokens=0,
                output_tokens=0,
            )

        context_block = "\n\n---\n\n".join(
            f"[{s.document_id}]\n{s.excerpt}" for s in sources
        )
        user_message = (
            f"Voici les marchés publics disponibles:\n\n{context_block}\n\n"
            f"Question (réponds en {language}): {question}"
        )

        log.info(
            "narrator_request",
            question_len=len(question),
            sources=len(sources),
            language=language,
        )

        message = await self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        answer_text = message.content[0].text

        log.info(
            "narrator_response",
            answer_len=len(answer_text),
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

        return NarratorResponse(
            answer=answer_text,
            sources=sources,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
