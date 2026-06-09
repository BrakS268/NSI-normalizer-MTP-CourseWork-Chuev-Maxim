"""In-memory stores for records and jobs.

Used in tests and for running without a real database.
In production these would be replaced by async DB repositories.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from nsi_normalizer.schemas.common import RawRecord, RecordType


class RecordStore:
    def __init__(self) -> None:
        self._store: dict[str, list[RawRecord]] = {}

    def save_batch(self, job_id: uuid.UUID, records: list[RawRecord]) -> None:
        key = str(job_id)
        self._store[key] = records

    def get_all(self, record_type: RecordType | None = None) -> list[RawRecord]:
        all_records: list[RawRecord] = []
        for batch in self._store.values():
            all_records.extend(batch)
        if record_type:
            return [r for r in all_records if r.record_type == record_type]
        return all_records

    def clear(self) -> None:
        self._store.clear()


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def create(self, job_id: uuid.UUID, record_type: str, total: int = 0) -> None:
        self._jobs[str(job_id)] = {
            "job_id": job_id,
            "record_type": record_type,
            "status": "pending",
            "total_records": total,
            "processed_records": 0,
            "created_at": datetime.now(UTC),
            "finished_at": None,
            "error": None,
        }

    def get(self, job_id: uuid.UUID) -> dict[str, Any] | None:
        return self._jobs.get(str(job_id))

    def update(self, job_id: uuid.UUID, **kwargs: Any) -> None:
        key = str(job_id)
        if key in self._jobs:
            self._jobs[key].update(kwargs)

    def complete(self, job_id: uuid.UUID, report: Any) -> None:
        self.update(
            job_id,
            status="completed",
            finished_at=datetime.now(UTC),
            processed_records=self._jobs[str(job_id)]["total_records"],
            report=report,
        )

    def fail(self, job_id: uuid.UUID, error: str) -> None:
        self.update(job_id, status="failed", error=error, finished_at=datetime.now(UTC))

    def clear(self) -> None:
        self._jobs.clear()


record_store = RecordStore()
job_store = JobStore()
