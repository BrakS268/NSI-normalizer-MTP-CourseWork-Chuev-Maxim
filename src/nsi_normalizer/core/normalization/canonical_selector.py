from __future__ import annotations

from nsi_normalizer.core.normalization.field_normalizer import (
    normalize_cve_ids,
    normalize_cvss,
    normalize_date,
    normalize_description,
    normalize_name,
    normalize_okved_code,
    normalize_severity,
)
from nsi_normalizer.schemas.common import NormalizedRecord, RawRecord

# Higher weight = more trusted source
_SOURCE_WEIGHTS: dict[str, float] = {
    "okved2_fns": 1.0,
    "fstec_bdu_xml": 1.0,
    "fstec_bdu_csv": 0.9,
    "okved2_csv": 0.85,
    "generic_json": 0.5,
    "generic_csv": 0.5,
}


def _source_weight(source: str) -> float:
    return _SOURCE_WEIGHTS.get(source, 0.6)


def _completeness_score(record: RawRecord) -> float:
    """Score based on how many important fields are filled."""
    p = record.payload
    fields = ["name", "description", "code", "section", "severity", "cve_ids_raw"]
    filled = sum(1 for f in fields if p.get(f))
    return filled / len(fields)


def _record_score(record: RawRecord) -> float:
    name_len = len(str(record.payload.get("name", "")))
    desc_len = len(str(record.payload.get("description") or ""))
    return (
        _source_weight(record.source) * 0.4
        + _completeness_score(record) * 0.35
        + min(name_len / 200, 1.0) * 0.15
        + min(desc_len / 500, 1.0) * 0.10
    )


def elect_canonical(records: list[RawRecord]) -> RawRecord:
    """Pick the highest-scoring record from a cluster as the canonical source."""
    return max(records, key=_record_score)


def normalize_okved_record(record: RawRecord) -> NormalizedRecord:
    p = record.payload
    raw_name = str(p.get("name", ""))
    raw_code = str(p.get("code", ""))
    raw_desc = str(p.get("description") or "")

    normalized_payload = {
        "code": normalize_okved_code(raw_code) if raw_code else None,
        "name": normalize_name(raw_name),
        "description": normalize_description(raw_desc) if raw_desc else None,
        "section": p.get("section"),
        "parent_code": (
            normalize_okved_code(str(p["parent_code"])) if p.get("parent_code") else None
        ),
        "version": p.get("version", "OKVED-2"),
    }

    return NormalizedRecord(
        record_type="okved",
        canonical_name=normalize_name(raw_name),
        canonical_code=normalize_okved_code(raw_code) if raw_code else None,
        normalized_payload=normalized_payload,
        confidence=_completeness_score(record),
        source=record.source,
    )


def normalize_fstec_record(record: RawRecord) -> NormalizedRecord:
    p = record.payload

    raw_name = str(p.get("name", ""))
    raw_severity = str(p.get("severity_raw") or p.get("severity") or "")
    raw_cve = str(p.get("cve_ids_raw") or "")
    raw_cvss = str(p.get("cvss_score_raw") or "")
    raw_published = str(p.get("published_at_raw") or "")
    raw_updated = str(p.get("updated_at_raw") or "")
    raw_desc = str(p.get("description") or "")

    severity = normalize_severity(raw_severity)
    published = normalize_date(raw_published)
    updated = normalize_date(raw_updated)
    cve_ids = normalize_cve_ids(raw_cve)
    cvss = normalize_cvss(raw_cvss)

    normalized_payload = {
        "bdu_id": p.get("bdu_id"),
        "name": normalize_name(raw_name),
        "description": normalize_description(raw_desc) if raw_desc else None,
        "severity": severity.value,
        "cve_ids": cve_ids,
        "cvss_score": cvss,
        "published_at": published.isoformat() if published else None,
        "updated_at": updated.isoformat() if updated else None,
    }

    return NormalizedRecord(
        record_type="fstec",
        canonical_name=normalize_name(raw_name),
        canonical_code=str(p.get("bdu_id", "")),
        normalized_payload=normalized_payload,
        confidence=_completeness_score(record),
        source=record.source,
    )


def normalize_record(record: RawRecord) -> NormalizedRecord:
    """Dispatch to the correct normalizer based on record_type."""
    if record.record_type == "okved":
        return normalize_okved_record(record)
    if record.record_type == "fstec":
        return normalize_fstec_record(record)
    # generic fallback
    return NormalizedRecord(
        record_type=record.record_type,
        canonical_name=normalize_name(str(record.payload.get("name", ""))),
        canonical_code=str(record.payload.get("code", "")) or None,
        normalized_payload=record.payload,
        confidence=0.5,
        source=record.source,
    )


def normalize_cluster(records: list[RawRecord]) -> NormalizedRecord:
    """Elect best record from cluster, normalize it, set confidence from cluster size."""
    canonical_raw = elect_canonical(records)
    result = normalize_record(canonical_raw)
    # Larger clusters give slightly higher confidence (more evidence)
    cluster_boost = min(len(records) / 10, 0.15)
    boosted = min(result.confidence + cluster_boost, 1.0)
    return result.model_copy(update={"confidence": boosted})
