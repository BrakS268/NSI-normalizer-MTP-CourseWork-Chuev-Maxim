from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from nsi_normalizer.schemas.common import NormalizedRecord, RecordType


class IngestRequest(BaseModel):
    records: list[dict[str, Any]] = Field(..., min_length=1, max_length=10_000)
    source: str = Field(..., min_length=1, max_length=100)
    record_type: RecordType


class IngestResponse(BaseModel):
    accepted: int
    job_id: uuid.UUID


class NormalizeRequest(BaseModel):
    source: str
    record_type: RecordType
    payload: dict[str, Any]


class NormalizeResponse(BaseModel):
    result: NormalizedRecord


class DeduplicateRequest(BaseModel):
    record_type: RecordType
    threshold: float = Field(default=0.65, ge=0.0, le=1.0)


class DeduplicateResponse(BaseModel):
    job_id: uuid.UUID
    status: Literal["accepted"] = "accepted"


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: Literal["pending", "running", "completed", "failed"]
    total_records: int
    processed_records: int
    progress: float
    created_at: datetime
    finished_at: datetime | None = None
    error: str | None = None


class JobResultResponse(BaseModel):
    job_id: uuid.UUID
    clusters_found: int
    duplicate_pairs: int
    total_records: int
    reduction_ratio: float
    results: list[dict[str, Any]]


class TrainResponse(BaseModel):
    status: str
    n_samples: int
    f1_mean: float
    f1_std: float
    model_path: str


class ProcessRequest(BaseModel):
    records: list[dict[str, Any]] = Field(..., min_length=1, max_length=10_000)
    source: str = Field(..., min_length=1, max_length=100)
    record_type: RecordType
    threshold: float = Field(default=0.65, ge=0.0, le=1.0)


class ProcessResponse(BaseModel):
    total_input: int
    total_output: int
    duplicates_removed: int
    reduction_ratio: float
    records: list[NormalizedRecord]
