"""Service gap forecasting model using Facebook Prophet.

Trains per-region time series models to predict where public service
delivery is likely to fall short over the coming months.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import structlog
from prophet import Prophet

log = structlog.get_logger(__name__)

ARTIFACT_DIR = Path("ml/forecasting/artifacts")


class GapForecaster:
    """Train and serve Prophet-based service gap forecasts per region.

    Each region gets its own model saved as a joblib artefact.
    """

    def train(self, df: pd.DataFrame, region: str, horizon_months: int = 6) -> pd.DataFrame:
        """Train a Prophet model for *region* and return the forecast DataFrame.

        Args:
            df: DataFrame with columns ds (date), y (gap_score 0–1).
            region: Region name used to namespace the saved artefact.
            horizon_months: Number of months to forecast ahead.

        Returns:
            Prophet forecast DataFrame with yhat, yhat_lower, yhat_upper.
        """
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.80,
        )
        model.fit(df[["ds", "y"]])

        future = model.make_future_dataframe(periods=horizon_months, freq="MS")
        forecast = model.predict(future)

        self._save(model, region)
        log.info("gap_model_trained", region=region, horizon=horizon_months)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    def predict(self, region: str, horizon_months: int = 6) -> pd.DataFrame:
        """Load a saved model for *region* and return a fresh forecast."""
        model = self._load(region)
        future = model.make_future_dataframe(periods=horizon_months, freq="MS")
        return model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    def _save(self, model: Prophet, region: str) -> None:
        """Persist model to disk."""
        import joblib

        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        path = ARTIFACT_DIR / f"{region.lower().replace(' ', '_')}.pkl"
        joblib.dump(model, path)
        log.debug("gap_model_saved", path=str(path))

    def _load(self, region: str) -> Prophet:
        """Load model from disk."""
        import joblib

        path = ARTIFACT_DIR / f"{region.lower().replace(' ', '_')}.pkl"
        if not path.exists():
            raise FileNotFoundError(f"No trained model for region: {region}")
        return joblib.load(path)
