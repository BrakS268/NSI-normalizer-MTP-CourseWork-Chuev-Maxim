from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from nsi_normalizer.schemas.common import RawRecord
from nsi_normalizer.core.cleaning.text_cleaner import clean_text, normalize_okved_code


Step = Callable[[RawRecord], RawRecord]


def _clean_name_step(record: RawRecord) -> RawRecord:
    name = record.payload.get("name", "")
    if isinstance(name, str):
        payload = dict(record.payload)
        payload["name"] = clean_text(name, strip_legal=True, expand_abbrevs=True)
        return record.model_copy(update={"payload": payload})
    return record


def _clean_description_step(record: RawRecord) -> RawRecord:
    desc = record.payload.get("description", "")
    if isinstance(desc, str) and desc:
        payload = dict(record.payload)
        payload["description"] = clean_text(desc)
        return record.model_copy(update={"payload": payload})
    return record


def _normalize_okved_code_step(record: RawRecord) -> RawRecord:
    if record.record_type != "okved":
        return record
    code = record.payload.get("code", "")
    if isinstance(code, str) and code:
        payload = dict(record.payload)
        payload["code"] = normalize_okved_code(code)
        return record.model_copy(update={"payload": payload})
    return record


def _normalize_fstec_severity_step(record: RawRecord) -> RawRecord:
    if record.record_type != "fstec":
        return record
    from nsi_normalizer.schemas.fstec import SEVERITY_MAP, Severity

    severity_raw = record.payload.get("severity_raw", "")
    if isinstance(severity_raw, str) and severity_raw:
        mapped = SEVERITY_MAP.get(severity_raw.strip().lower(), Severity.UNKNOWN)
        payload = dict(record.payload)
        payload["severity"] = mapped.value
        return record.model_copy(update={"payload": payload})
    return record


DEFAULT_STEPS: list[Step] = [
    _clean_name_step,
    _clean_description_step,
    _normalize_okved_code_step,
    _normalize_fstec_severity_step,
]


class CleaningPipeline:
    def __init__(self, steps: list[Step] | None = None) -> None:
        self.steps: list[Step] = steps if steps is not None else DEFAULT_STEPS

    def run_one(self, record: RawRecord) -> RawRecord:
        for step in self.steps:
            record = step(record)
        return record

    def run(self, records: Iterable[RawRecord]) -> list[RawRecord]:
        return [self.run_one(r) for r in records]

    def add_step(self, step: Step) -> CleaningPipeline:
        return CleaningPipeline(steps=[*self.steps, step])
