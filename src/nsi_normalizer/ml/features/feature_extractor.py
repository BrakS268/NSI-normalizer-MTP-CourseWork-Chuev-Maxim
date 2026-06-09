from __future__ import annotations

from typing import TypedDict

from rapidfuzz import distance as rfdist
from rapidfuzz import fuzz as rffuzz

from nsi_normalizer.core.cleaning.text_cleaner import clean_text, normalize_okved_code
from nsi_normalizer.schemas.common import RawRecord


class FeatureVector(TypedDict):
    jaro_winkler: float
    token_sort_ratio: float
    token_set_ratio: float
    levenshtein_norm: float
    code_exact_match: float
    code_prefix_2_match: float
    description_jaccard: float
    name_length_diff: float


def _get_name(record: RawRecord) -> str:
    raw = record.payload.get("name", "")
    return clean_text(str(raw), lowercase=True) if raw else ""


def _get_code(record: RawRecord) -> str:
    if record.record_type == "fstec":
        raw = record.payload.get("bdu_id", "")
        return str(raw).strip() if raw else ""
    raw = record.payload.get("code", "")
    return normalize_okved_code(str(raw)) if raw else ""


def _get_description(record: RawRecord) -> str:
    raw = record.payload.get("description", "")
    return clean_text(str(raw), lowercase=True) if raw else ""


def _jaccard_on_tokens(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    set_a = set(a.split())
    set_b = set(b.split())
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def extract_features(left: RawRecord, right: RawRecord) -> FeatureVector:
    name_l = _get_name(left)
    name_r = _get_name(right)

    code_l = _get_code(left)
    code_r = _get_code(right)

    desc_l = _get_description(left)
    desc_r = _get_description(right)

    jw = rfdist.JaroWinkler.normalized_similarity(name_l, name_r)
    tsr = rffuzz.token_sort_ratio(name_l, name_r) / 100.0
    tsset = rffuzz.token_set_ratio(name_l, name_r) / 100.0
    lev = rfdist.Levenshtein.normalized_similarity(name_l, name_r)

    code_exact = 1.0 if code_l and code_r and code_l == code_r else 0.0
    code_prefix = 1.0 if code_l and code_r and code_l[:2] == code_r[:2] else 0.0

    desc_jaccard = _jaccard_on_tokens(desc_l, desc_r)

    len_diff = abs(len(name_l) - len(name_r)) / max(len(name_l), len(name_r), 1)

    return FeatureVector(
        jaro_winkler=jw,
        token_sort_ratio=tsr,
        token_set_ratio=tsset,
        levenshtein_norm=lev,
        code_exact_match=code_exact,
        code_prefix_2_match=code_prefix,
        description_jaccard=desc_jaccard,
        name_length_diff=len_diff,
    )


FEATURE_NAMES: list[str] = list(FeatureVector.__annotations__.keys())


def features_to_list(fv: FeatureVector) -> list[float]:
    return [fv[k] for k in FEATURE_NAMES]  # type: ignore[literal-required]
