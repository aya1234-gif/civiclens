"""Train the procurement anomaly detection model.

Loads tenders from the warehouse, builds features, trains an IForest,
persists scores back to Postgres, and logs everything to MLflow.

Usage:
    python -m ml.anomaly.train
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import asyncpg
import mlflow
import numpy as np
import pandas as pd
import structlog
from pyod.models.iforest import IForest

from config.settings import settings
from governance.audit_logger import AuditLogger
from ml.anomaly.features import FEATURE_COLUMNS, build_features

log = structlog.get_logger(__name__)

MODEL_NAME = "anomaly_detector"
MODEL_VERSION = "1.0"
ARTIFACT_DIR = Path("ml/anomaly/artifacts")

_LOAD_SQL = """
SELECT
    s.reference,
    s.contracting_authority,
    s.object,
    s.tender_type,
    s.procedure_type,
    s.publication_date,
    s.region,
    s.wilaya,
    d.real_deadline,
    d.announcement_type
FROM public_staging.stg_tenders s
LEFT JOIN public.tender_details d USING (reference)
WHERE s.publication_date IS NOT NULL
ORDER BY s.publication_date DESC
"""

_CREATE_SCORES_TABLE = """
CREATE TABLE IF NOT EXISTS public.anomaly_scores (
    reference           TEXT PRIMARY KEY,
    anomaly_score       DOUBLE PRECISION,
    is_anomaly          BOOLEAN,
    scored_at           TIMESTAMPTZ DEFAULT NOW(),
    model_version       TEXT
)
"""

_UPSERT_SCORE_SQL = """
INSERT INTO public.anomaly_scores (reference, anomaly_score, is_anomaly, model_version)
VALUES ($1, $2, $3, $4)
ON CONFLICT (reference) DO UPDATE
  SET anomaly_score = EXCLUDED.anomaly_score,
      is_anomaly    = EXCLUDED.is_anomaly,
      scored_at     = NOW(),
      model_version = EXCLUDED.model_version;
"""


async def train_and_score(contamination: float = 0.1) -> None:
    """Train IForest on all warehouse tenders, persist anomaly scores.

    Args:
        contamination: Expected fraction of anomalous tenders (0–0.5).
    """
    db_url = (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    conn = await asyncpg.connect(db_url)

    try:
        rows = await conn.fetch(_LOAD_SQL)
        if not rows:
            log.warning("no_data_for_training")
            return

        df = pd.DataFrame([dict(r) for r in rows])
        log.info("training_data_loaded", rows=len(df))

        # Add synthetic amount column if missing (raw data has no amount yet)
        if "estimated_amount_mad" not in df.columns or df["estimated_amount_mad"].isna().all():
            df["estimated_amount_mad"] = np.nan

        features = build_features(df)

        audit = AuditLogger()
        await audit.initialise()

        with mlflow.start_run(run_name=f"{MODEL_NAME}_v{MODEL_VERSION}"):
            mlflow.log_params({
                "contamination": contamination,
                "n_estimators": 200,
                "n_samples": len(df),
                "features": FEATURE_COLUMNS,
            })

            async with audit.track(
                MODEL_NAME,
                version=MODEL_VERSION,
                triggered_by="train/manual",
                input_data={"rows": len(features), "cols": FEATURE_COLUMNS},
            ):
                model = IForest(
                    contamination=contamination,
                    n_estimators=200,
                    random_state=42,
                )
                model.fit(features.values)

            # Normalise scores to [0, 1] (higher = more anomalous)
            raw_scores = model.decision_scores_
            norm_scores = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-9)
            labels = model.labels_  # 0 = normal, 1 = anomaly

            flagged_pct = float(labels.mean())
            mlflow.log_metrics({
                "flagged_pct": flagged_pct,
                "mean_score": float(norm_scores.mean()),
                "n_anomalies": int(labels.sum()),
            })

            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
            import joblib
            model_path = ARTIFACT_DIR / "iforest.pkl"
            joblib.dump(model, model_path)
            mlflow.log_artifact(str(model_path))

        # Persist scores to Postgres
        await conn.execute(_CREATE_SCORES_TABLE)
        async with conn.transaction():
            for i, ref in enumerate(df["reference"]):
                await conn.execute(
                    _UPSERT_SCORE_SQL,
                    str(ref),
                    float(norm_scores[i]),
                    bool(labels[i]),
                    MODEL_VERSION,
                )

        log.info(
            "training_complete",
            n_samples=len(df),
            flagged_pct=round(flagged_pct, 3),
            model_path=str(model_path),
        )
        await audit.close()

    finally:
        await conn.close()


if __name__ == "__main__":
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(train_and_score())
