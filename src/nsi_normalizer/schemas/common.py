from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RecordType = Literal["okved", "fstec", "generic"]


class RawRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str = Field(..., description="Data source identifier")
    record_type: RecordType = Field(..., description="Type of reference record")
    raw_id: str | None = Field(None, description="Original ID in the source system")
    payload: dict[str, Any] = Field(default_factory=dict, description="Raw record fields")


class NormalizedRecord(BaseModel):
    canonical_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    record_type: RecordType
    canonical_name: str
    canonical_code: str | None = None
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    cluster_id: uuid.UUID | None = None
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeduplicationResult(BaseModel):
    cluster_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    record_ids: list[uuid.UUID]
    canonical_record: NormalizedRecord
    confidence: float = Field(..., ge=0.0, le=1.0)
    record_count: int

    @classmethod
    def from_cluster(
        cls,
        record_ids: list[uuid.UUID],
        canonical: NormalizedRecord,
        confidence: float,
    ) -> DeduplicationResult:
        return cls(
            record_ids=record_ids,
            canonical_record=canonical,
            confidence=confidence,
            record_count=len(record_ids),
        )


class NormalizationJob(BaseModel):
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    record_type: RecordType
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    total_records: int = 0
    processed_records: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    error: str | None = None

    @property
    def progress(self) -> float:
        if self.total_records == 0:
            return 0.0
        return self.processed_records / self.total_records
