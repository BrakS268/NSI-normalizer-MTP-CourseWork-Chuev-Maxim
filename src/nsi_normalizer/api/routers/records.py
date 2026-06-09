from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from nsi_normalizer.api.dependencies import verify_api_key
from nsi_normalizer.api.schemas import (
    DeduplicateRequest,
    DeduplicateResponse,
    IngestRequest,
    IngestResponse,
    NormalizeRequest,
    NormalizeResponse,
)
from nsi_normalizer.core.normalization.canonical_selector import normalize_record
from nsi_normalizer.schemas.common import RawRecord
from nsi_normalizer.store import job_store, record_store

router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a batch of raw records",
)
async def ingest(
    request: IngestRequest,
    _: str = Depends(verify_api_key),
) -> IngestResponse:
    job_id = uuid.uuid4()
    raw_records = [
        RawRecord(
            source=request.source,
            record_type=request.record_type,
            raw_id=str(item.get("id") or item.get("code") or i),
            payload=item,
        )
        for i, item in enumerate(request.records)
    ]
    record_store.save_batch(job_id, raw_records)
    job_store.create(job_id, request.record_type, total=len(raw_records))
    return IngestResponse(accepted=len(raw_records), job_id=job_id)


@router.post(
    "/normalize",
    response_model=NormalizeResponse,
    summary="Normalize a single record synchronously",
)
async def normalize_one(
    request: NormalizeRequest,
    _: str = Depends(verify_api_key),
) -> NormalizeResponse:
    record = RawRecord(
        source=request.source,
        record_type=request.record_type,
        payload=request.payload,
    )
    result = normalize_record(record)
    return NormalizeResponse(result=result)


@router.post(
    "/deduplicate",
    response_model=DeduplicateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start deduplication job over ingested records",
)
async def deduplicate(
    request: DeduplicateRequest,
    _: str = Depends(verify_api_key),
) -> DeduplicateResponse:
    from nsi_normalizer.ml.pipeline import DeduplicationPipeline

    records = record_store.get_all(record_type=request.record_type)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ingested records found for type '{request.record_type}'",
        )
    job_id = uuid.uuid4()
    job_store.create(job_id, request.record_type, total=len(records))
    job_store.update(job_id, status="running")

    try:
        pipeline = DeduplicationPipeline(threshold=request.threshold)
        report = pipeline.run(records)
        job_store.complete(job_id, report)
    except Exception as exc:
        job_store.fail(job_id, str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DeduplicateResponse(job_id=job_id)
