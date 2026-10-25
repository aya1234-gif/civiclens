"""CivicLens FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import check_connection, engine
from api.routers import anomalies, forecasts, governance, query, tenders
from config.settings import settings

log = structlog.get_logger(__name__)


def _configure_logging() -> None:
    """Configure structlog for JSON in prod, pretty in dev."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    structlog.configure(processors=processors)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown."""
    _configure_logging()
    db_ok = await check_connection()
    log.info(
        "civiclens_api_starting",
        environment=settings.environment,
        database=("ok" if db_ok else "UNREACHABLE"),
    )
    yield
    await engine.dispose()
    log.info("civiclens_api_shutdown")


app = FastAPI(
    title="CivicLens API",
    description="AI-powered civic data intelligence for Morocco 🇲🇦",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(tenders.router,    prefix="/api/v1/tenders",    tags=["tenders"])
app.include_router(anomalies.router,  prefix="/api/v1/anomalies",  tags=["anomalies"])
app.include_router(forecasts.router,  prefix="/api/v1/forecasts",  tags=["forecasts"])
app.include_router(query.router,      prefix="/api/v1/query",      tags=["query"])
app.include_router(governance.router, prefix="/api/v1/governance", tags=["governance"])


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness + readiness probe."""
    db_ok = await check_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "environment": settings.environment,
    }
