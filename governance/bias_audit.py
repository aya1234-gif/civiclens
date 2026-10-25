"""Bias audit for CivicLens ML models.

Checks whether anomaly scores or service gap predictions exhibit
systematic disparities across regions, tender types, or authority size.

Uses Fairlearn's MetricFrame for disaggregated evaluation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import structlog
from fairlearn.metrics import MetricFrame, selection_rate
from sklearn.metrics import precision_score, recall_score

from governance.audit_logger import AuditLogger

log = structlog.get_logger(__name__)


class BiasAudit:
    """Evaluate ML model predictions for demographic/geographic parity.

    Reports disparities per sensitive feature (region, tender_type).
    """

    def __init__(self, model_name: str, model_version: str) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._audit = AuditLogger()

    async def run(
        self,
        df: pd.DataFrame,
        y_true_col: str,
        y_pred_col: str,
        sensitive_features: list[str],
    ) -> dict[str, Any]:
        """Compute bias metrics disaggregated by *sensitive_features*.

        Args:
            df: DataFrame containing ground truth, predictions, and features.
            y_true_col: Column name for ground-truth labels (0/1).
            y_pred_col: Column name for model predictions (0/1).
            sensitive_features: Column names to disaggregate by.

        Returns:
            Dict of metric name → MetricFrame result per sensitive feature.
        """
        await self._audit.initialise()
        results: dict[str, Any] = {}

        for feature in sensitive_features:
            if feature not in df.columns:
                log.warning("sensitive_feature_missing", feature=feature)
                continue

            mf = MetricFrame(
                metrics={
                    "precision": precision_score,
                    "recall": recall_score,
                    "selection_rate": selection_rate,
                },
                y_true=df[y_true_col],
                y_pred=df[y_pred_col],
                sensitive_features=df[feature],
            )

            disparity = mf.difference()
            results[feature] = {
                "by_group": mf.by_group.to_dict(),
                "overall": mf.overall.to_dict(),
                "disparity": disparity.to_dict(),
            }

            log.info(
                "bias_audit_result",
                model=self._model_name,
                feature=feature,
                max_disparity=float(disparity.max()),
            )

            # Flag if any metric exceeds 0.1 disparity threshold
            if float(disparity.max()) > 0.1:
                log.warning(
                    "bias_threshold_exceeded",
                    model=self._model_name,
                    feature=feature,
                    disparity=float(disparity.max()),
                )

        await self._audit.close()
        return results


async def _main() -> None:
    """CLI entrypoint for running the bias audit from the Makefile."""
    log.info("bias_audit_started")
    # In production: load predictions from the warehouse
    # For now, emit a warning that data must be provided
    log.warning("bias_audit_no_data", hint="Pipe prediction DataFrame via audit.run()")


if __name__ == "__main__":
    import structlog

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(_main())
