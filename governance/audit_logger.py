"""Reusable audit logger for AI model inferences.

Every ML inference and LLM call should be wrapped with AuditLogger.track()
to ensure full reproducibility, cost attribution, and bias auditing.

The audit_log table is created on first use if it does not exist.
"""

from __future__ import annotations

import hashlib
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings

log = structlog.get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_name      TEXT        NOT NULL,
    model_version   TEXT        NOT NULL,
    input_hash      CHAR(64)    NOT NULL,
    output_hash     CHAR(64),
    inference_time_ms DOUBLE PRECISION,
    triggered_by    TEXT        NOT NULL,
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_log_model
    ON audit_log (model_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_triggered_by
    ON audit_log (triggered_by, timestamp DESC);
"""


class AuditLogger:
    """Async-safe audit logger that persists inference records to Postgres.

    Usage::

        logger = AuditLogger()
        await logger.initialise()

        async with logger.track("anomaly_detector", version="1.0",
                                triggered_by="dag/daily_tenders") as ctx:
            result = model.predict(features)
            ctx.set_output(result)
    """

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self._engine = engine or create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._initialised = False

    async def initialise(self) -> None:
        """Create the audit_log table and indexes if they do not exist."""
        stmts = [s.strip() for s in _CREATE_TABLE_SQL.split(";") if s.strip()]
        async with self._engine.begin() as conn:
            for stmt in stmts:
                await conn.execute(text(stmt))
        self._initialised = True
        log.info("audit_logger_initialised")

    @asynccontextmanager
    async def track(
        self,
        model_name: str,
        version: str,
        triggered_by: str,
        input_data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator["_AuditContext"]:
        """Context manager that records a single inference to audit_log.

        Args:
            model_name: Logical model identifier, e.g. "anomaly_detector".
            version: Semver or commit SHA of the model artefact.
            triggered_by: Actor initiating inference, e.g. "dag/daily_tenders" or
                          a user ID such as "user/aya".
            input_data: Raw input; only its SHA-256 is stored.
            metadata: Free-form JSON metadata attached to the log row.

        Yields:
            An :class:`_AuditContext` that callers use to attach the output.
        """
        if not self._initialised:
            await self.initialise()

        input_hash = _sha256(input_data)
        ctx = _AuditContext()
        start = time.monotonic()

        try:
            yield ctx
        finally:
            inference_ms = (time.monotonic() - start) * 1000
            output_hash = _sha256(ctx._output) if ctx._output is not None else None

            async with self._session_factory() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO audit_log
                            (timestamp, model_name, model_version, input_hash,
                             output_hash, inference_time_ms, triggered_by, metadata)
                        VALUES
                            (:ts, :model_name, :model_version, :input_hash,
                             :output_hash, :inference_ms, :triggered_by, CAST(:metadata AS jsonb))
                        """
                    ),
                    {
                        "ts": datetime.utcnow(),
                        "model_name": model_name,
                        "model_version": version,
                        "input_hash": input_hash,
                        "output_hash": output_hash,
                        "inference_ms": inference_ms,
                        "triggered_by": triggered_by,
                        "metadata": _json_or_null(metadata),
                    },
                )
                await session.commit()

            log.info(
                "inference_audited",
                model=model_name,
                version=version,
                triggered_by=triggered_by,
                inference_ms=round(inference_ms, 2),
            )

    async def close(self) -> None:
        """Dispose the engine connection pool."""
        await self._engine.dispose()


class _AuditContext:
    """Carrier object yielded by AuditLogger.track()."""

    def __init__(self) -> None:
        self._output: Any = None

    def set_output(self, output: Any) -> None:
        """Attach the inference result so its hash can be logged."""
        self._output = output


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _sha256(value: Any) -> str:
    """Return a hex SHA-256 digest of *value* serialised to bytes."""
    if value is None:
        raw = b""
    elif isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode()
    else:
        import json
        raw = json.dumps(value, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _json_or_null(d: dict[str, Any] | None) -> str | None:
    """Serialise dict to JSON string or return None."""
    if d is None:
        return None
    import json
    return json.dumps(d, default=str)
