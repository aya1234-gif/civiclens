"""Evaluate the anomaly model with SHAP explanations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import shap
import structlog

from ml.anomaly.features import build_features

log = structlog.get_logger(__name__)

ARTIFACT_DIR = Path("ml/anomaly/artifacts")


def load_model() -> object:
    """Load the trained IForest model from the artifact directory."""
    import joblib

    path = ARTIFACT_DIR / "iforest.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    return joblib.load(path)


def explain(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of SHAP values for each tender row.

    Columns correspond to :data:`~ml.anomaly.features.FEATURE_COLUMNS`.
    """
    model = load_model()
    features = build_features(df)

    explainer = shap.TreeExplainer(model.detector_)
    shap_values = explainer.shap_values(features)

    result = pd.DataFrame(shap_values, columns=features.columns, index=df.index)
    log.info("shap_explained", rows=len(result))
    return result
