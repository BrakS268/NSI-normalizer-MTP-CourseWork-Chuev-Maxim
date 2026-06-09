from __future__ import annotations

import joblib
import numpy as np
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from nsi_normalizer.ml.features.feature_extractor import (
    FeatureVector,
    FEATURE_NAMES,
    features_to_list,
)

DEFAULT_MODEL_PATH = Path("models/dedup_classifier.joblib")

# Rule-based shortcut thresholds — avoids ML inference for obvious cases
_HARD_MATCH_JW = 0.97
_HARD_NOMATCH_JW = 0.30


def _hard_rule(fv: FeatureVector) -> float | None:
    """Return confidence directly if the pair is unambiguous, else None."""
    if fv["jaro_winkler"] >= _HARD_MATCH_JW and fv["code_exact_match"] == 1.0:
        return 0.99
    if fv["jaro_winkler"] <= _HARD_NOMATCH_JW and fv["code_prefix_2_match"] == 0.0:
        return 0.01
    return None


def build_sklearn_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
        )),
    ])


class DedupClassifier:
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = model_path
        self._pipeline: Pipeline | None = None

    def _get_pipeline(self) -> Pipeline:
        if self._pipeline is None:
            if self.model_path.exists():
                self._pipeline = joblib.load(self.model_path)
            else:
                self._pipeline = build_sklearn_pipeline()
        return self._pipeline

    def predict_proba(self, fv: FeatureVector) -> float:
        """Return probability [0..1] that the pair is a duplicate."""
        hard = _hard_rule(fv)
        if hard is not None:
            return hard

        pipeline = self._get_pipeline()
        if not _is_fitted(pipeline):
            # Model not trained yet — fall back to heuristic mean of string metrics
            return (
                fv["jaro_winkler"] * 0.4
                + fv["token_sort_ratio"] * 0.3
                + fv["token_set_ratio"] * 0.2
                + fv["code_exact_match"] * 0.1
            )

        X = np.array([features_to_list(fv)])
        proba: float = pipeline.predict_proba(X)[0][1]
        return float(proba)

    def is_duplicate(self, fv: FeatureVector, threshold: float = 0.65) -> tuple[bool, float]:
        confidence = self.predict_proba(fv)
        return confidence >= threshold, confidence

    def fit(
        self,
        X: list[list[float]],
        y: list[int],
    ) -> dict[str, float]:
        from sklearn.model_selection import cross_val_score

        pipeline = build_sklearn_pipeline()
        pipeline.fit(X, y)
        self._pipeline = pipeline

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, self.model_path)

        scores = cross_val_score(pipeline, X, y, cv=5, scoring="f1")
        return {
            "f1_mean": float(scores.mean()),
            "f1_std": float(scores.std()),
            "n_samples": len(y),
        }


def _is_fitted(pipeline: Pipeline) -> bool:
    try:
        from sklearn.utils.validation import check_is_fitted
        check_is_fitted(pipeline["clf"])
        return True
    except Exception:
        return False
