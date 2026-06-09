from __future__ import annotations

import csv
import io
from pathlib import Path

from nsi_normalizer.ml.classification.dedup_classifier import DedupClassifier
from nsi_normalizer.ml.features.feature_extractor import (
    extract_features,
    features_to_list,
)
from nsi_normalizer.schemas.common import RawRecord


def load_labeled_pairs(csv_source: str | Path | bytes) -> tuple[list[list[float]], list[int]]:
    """Load labeled pairs CSV: left_* / right_* columns + 'label' (0 or 1).

    Expected columns:
      left_code, left_name, left_description,
      right_code, right_name, right_description,
      label
    """
    if isinstance(csv_source, bytes):
        text = csv_source.decode("utf-8")
    else:
        text = Path(csv_source).read_text(encoding="utf-8")

    X: list[list[float]] = []  # noqa: N806
    y: list[int] = []

    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        left = RawRecord(
            source="train",
            record_type="okved",
            raw_id=row.get("left_code"),
            payload={
                "code": row.get("left_code", ""),
                "name": row.get("left_name", ""),
                "description": row.get("left_description", ""),
            },
        )
        right = RawRecord(
            source="train",
            record_type="okved",
            raw_id=row.get("right_code"),
            payload={
                "code": row.get("right_code", ""),
                "name": row.get("right_name", ""),
                "description": row.get("right_description", ""),
            },
        )
        fv = extract_features(left, right)
        X.append(features_to_list(fv))
        y.append(int(row.get("label", 0)))

    return X, y


def train(
    csv_source: str | Path | bytes,
    model_path: Path = Path("models/dedup_classifier.joblib"),
) -> dict[str, float]:
    """Train classifier on labeled pairs CSV and save the model."""
    X, y = load_labeled_pairs(csv_source)  # noqa: N806
    if not X:
        raise ValueError("No training samples found in the CSV")

    classifier = DedupClassifier(model_path=model_path)
    metrics = classifier.fit(X, y)
    return metrics
