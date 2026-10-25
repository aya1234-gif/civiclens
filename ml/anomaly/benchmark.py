"""Anomaly model benchmark.

Compares four PyOD algorithms on the same feature matrix, runs contamination
sensitivity analysis, and performs feature ablation — all without ground-truth
labels (unsupervised setting).

Usage:
    python -m ml.anomaly.benchmark

Outputs:
    ml/anomaly/artifacts/benchmark_results.json   — machine-readable summary
    ml/anomaly/artifacts/benchmark_report.txt     — human-readable report
"""

from __future__ import annotations

import asyncio
import json
import time
from itertools import combinations
from pathlib import Path

import asyncpg
import numpy as np
import pandas as pd
import structlog

from config.settings import settings
from ml.anomaly.features import FEATURE_COLUMNS, build_features

log = structlog.get_logger(__name__)

ARTIFACT_DIR = Path("ml/anomaly/artifacts")

_LOAD_SQL = """
SELECT
    reference,
    contracting_authority,
    object,
    tender_type,
    procedure_type,
    publication_date,
    deadline_date,
    region,
    wilaya
FROM public_staging.stg_tenders
WHERE publication_date IS NOT NULL
ORDER BY publication_date DESC
"""


# ── Algorithm registry ────────────────────────────────────────────────────────

def _make_models(contamination: float) -> dict:
    from pyod.models.iforest import IForest
    from pyod.models.lof import LOF
    from pyod.models.copod import COPOD
    from pyod.models.hbos import HBOS

    return {
        "IForest": IForest(contamination=contamination, n_estimators=200, random_state=42),
        "LOF":     LOF(contamination=contamination, n_neighbors=20),
        "COPOD":   COPOD(contamination=contamination),
        "HBOS":    HBOS(contamination=contamination),
    }


# ── Agreement metric ──────────────────────────────────────────────────────────

def _pairwise_agreement(labels: dict[str, np.ndarray]) -> dict[str, float]:
    """Jaccard similarity between every pair of models' flagged sets."""
    result = {}
    names = list(labels.keys())
    for a, b in combinations(names, 2):
        la, lb = labels[a].astype(bool), labels[b].astype(bool)
        intersection = (la & lb).sum()
        union = (la | lb).sum()
        jaccard = float(intersection / union) if union > 0 else 1.0
        result[f"{a}_vs_{b}"] = round(jaccard, 4)
    return result


def _flag_rate(label: np.ndarray) -> float:
    return round(float(label.mean()), 4)


# ── Part 1: Algorithm comparison ─────────────────────────────────────────────

def run_algorithm_comparison(
    features: pd.DataFrame,
    contamination: float = 0.08,
) -> dict:
    log.info("benchmark.algorithm_comparison", contamination=contamination)
    models = _make_models(contamination)
    labels: dict[str, np.ndarray] = {}
    scores: dict[str, np.ndarray] = {}
    timings: dict[str, float] = {}

    X = features.values

    for name, model in models.items():
        t0 = time.perf_counter()
        model.fit(X)
        elapsed = round(time.perf_counter() - t0, 2)

        labels[name] = model.labels_
        scores[name] = model.decision_scores_
        timings[name] = elapsed
        log.info("model_done", model=name, flag_rate=_flag_rate(labels[name]), elapsed_s=elapsed)

    agreement = _pairwise_agreement(labels)
    avg_agreement = round(float(np.mean(list(agreement.values()))), 4)

    return {
        "contamination": contamination,
        "flag_rates": {k: _flag_rate(v) for k, v in labels.items()},
        "pairwise_agreement": agreement,
        "avg_pairwise_agreement": avg_agreement,
        "fit_time_s": timings,
        "labels": {k: v.tolist() for k, v in labels.items()},
    }


# ── Part 2: Contamination sensitivity ────────────────────────────────────────

def run_contamination_sensitivity(features: pd.DataFrame) -> dict:
    contaminations = [0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
    log.info("benchmark.contamination_sensitivity", values=contaminations)

    from pyod.models.iforest import IForest

    X = features.values
    results = {}

    base_labels = None
    for c in contaminations:
        model = IForest(contamination=c, n_estimators=200, random_state=42)
        model.fit(X)
        lbl = model.labels_

        if base_labels is None:
            base_labels = lbl
            overlap = 1.0
        else:
            inter = (base_labels.astype(bool) & lbl.astype(bool)).sum()
            union = (base_labels.astype(bool) | lbl.astype(bool)).sum()
            overlap = round(float(inter / union) if union > 0 else 1.0, 4)

        results[str(c)] = {
            "n_flagged": int(lbl.sum()),
            "flag_rate": _flag_rate(lbl),
            "overlap_with_0.03": overlap,
        }
        log.info("contamination_done", c=c, n_flagged=int(lbl.sum()), overlap=overlap)

    return results


# ── Part 3: Feature ablation ──────────────────────────────────────────────────

def run_feature_ablation(
    features: pd.DataFrame,
    contamination: float = 0.08,
) -> dict:
    log.info("benchmark.feature_ablation", n_features=len(FEATURE_COLUMNS))

    from pyod.models.iforest import IForest

    # Baseline with all features
    X_full = features.values
    base_model = IForest(contamination=contamination, n_estimators=200, random_state=42)
    base_model.fit(X_full)
    base_labels = base_model.labels_.astype(bool)

    results = {}
    for col in FEATURE_COLUMNS:
        remaining = [c for c in FEATURE_COLUMNS if c != col]
        X_ablated = features[remaining].values

        model = IForest(contamination=contamination, n_estimators=200, random_state=42)
        model.fit(X_ablated)
        ablated_labels = model.labels_.astype(bool)

        inter = (base_labels & ablated_labels).sum()
        union = (base_labels | ablated_labels).sum()
        stability = round(float(inter / union) if union > 0 else 1.0, 4)

        results[col] = {
            "stability_without": stability,
            "n_flagged_without": int(ablated_labels.sum()),
            "importance": round(1.0 - stability, 4),
        }
        log.info("ablation_done", dropped=col, stability=stability)

    # Sort by importance descending
    results = dict(sorted(results.items(), key=lambda x: x[1]["importance"], reverse=True))
    return results


# ── Report writer ─────────────────────────────────────────────────────────────

def write_report(algo: dict, sensitivity: dict, ablation: dict, path: Path) -> None:
    lines = []
    lines.append("=" * 60)
    lines.append("CIVICLENS ANOMALY MODEL BENCHMARK REPORT")
    lines.append("=" * 60)

    lines.append("\n── 1. ALGORITHM COMPARISON (contamination=0.08) ──────────")
    lines.append(f"{'Model':<15} {'Flag Rate':>10} {'Fit Time (s)':>13}")
    lines.append("-" * 40)
    for name, rate in algo["flag_rates"].items():
        lines.append(f"{name:<15} {rate:>10.2%} {algo['fit_time_s'][name]:>12.2f}s")

    lines.append(f"\nPairwise agreement (Jaccard):")
    for pair, score in algo["pairwise_agreement"].items():
        bar = "█" * int(score * 20)
        lines.append(f"  {pair:<25} {score:.4f}  {bar}")
    lines.append(f"\n  Average agreement: {algo['avg_pairwise_agreement']:.4f}")
    if algo["avg_pairwise_agreement"] >= 0.6:
        lines.append("  ✓ Models broadly agree — IForest results are stable.")
    else:
        lines.append("  ✗ Low agreement — flagged set is sensitive to algorithm choice.")

    lines.append("\n── 2. CONTAMINATION SENSITIVITY (IForest) ────────────────")
    lines.append(f"{'Contamination':>14} {'N Flagged':>10} {'Overlap w/ 3%':>14}")
    lines.append("-" * 42)
    for c, v in sensitivity.items():
        lines.append(f"{float(c):>14.0%} {v['n_flagged']:>10} {v['overlap_with_0.03']:>14.4f}")

    lines.append("\n── 3. FEATURE ABLATION (IForest, contamination=0.08) ─────")
    lines.append(f"{'Feature':<35} {'Importance':>10} {'Stability':>10}")
    lines.append("-" * 58)
    for col, v in ablation.items():
        bar = "█" * int(v["importance"] * 20)
        lines.append(f"{col:<35} {v['importance']:>10.4f} {v['stability_without']:>10.4f}  {bar}")

    lines.append("\n── 4. RECOMMENDATION ─────────────────────────────────────")
    top_feature = next(iter(ablation))
    lines.append(f"  Most important feature: {top_feature}")
    lines.append(f"  Algorithm avg agreement: {algo['avg_pairwise_agreement']:.4f}")

    if algo["avg_pairwise_agreement"] >= 0.5:
        lines.append("  → Keep IForest as primary model.")
    else:
        lines.append("  → Consider ensemble or switch to COPOD (faster, deterministic).")

    lines.append("=" * 60)

    path.write_text("\n".join(lines))
    print("\n".join(lines))


# ── Main ──────────────────────────────────────────────────────────────────────

async def run_benchmark() -> None:
    db_url = (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    conn = await asyncpg.connect(db_url)

    try:
        rows = await conn.fetch(_LOAD_SQL)
        if not rows:
            log.error("no_data")
            return

        df = pd.DataFrame([dict(r) for r in rows])
        df["estimated_amount_mad"] = np.nan
        features = build_features(df)

        log.info("data_loaded", n_tenders=len(df), n_features=len(FEATURE_COLUMNS))

        algo_results = run_algorithm_comparison(features, contamination=0.08)
        sensitivity_results = run_contamination_sensitivity(features)
        ablation_results = run_feature_ablation(features, contamination=0.08)

        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

        summary = {
            "n_tenders": len(df),
            "features": FEATURE_COLUMNS,
            "algorithm_comparison": {k: v for k, v in algo_results.items() if k != "labels"},
            "contamination_sensitivity": sensitivity_results,
            "feature_ablation": ablation_results,
        }
        (ARTIFACT_DIR / "benchmark_results.json").write_text(
            json.dumps(summary, indent=2)
        )

        write_report(
            algo_results,
            sensitivity_results,
            ablation_results,
            ARTIFACT_DIR / "benchmark_report.txt",
        )

        log.info("benchmark_complete", artifacts=str(ARTIFACT_DIR))

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
    asyncio.run(run_benchmark())
