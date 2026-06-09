from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status, Depends

from nsi_normalizer.api.dependencies import verify_api_key
from nsi_normalizer.api.schemas import JobStatusResponse, JobResultResponse
from nsi_normalizer.store import job_store

router = APIRouter()


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get status of a background job",
)
async def get_job_status(
    job_id: uuid.UUID,
    _: str = Depends(verify_api_key),
) -> JobStatusResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    total = job["total_records"]
    processed = job["processed_records"]
    progress = processed / total if total else 0.0
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        total_records=total,
        processed_records=processed,
        progress=progress,
        created_at=job["created_at"],
        finished_at=job.get("finished_at"),
        error=job.get("error"),
    )


@router.get(
    "/{job_id}/result",
    response_model=JobResultResponse,
    summary="Get results of a completed deduplication job",
)
async def get_job_result(
    job_id: uuid.UUID,
    _: str = Depends(verify_api_key),
) -> JobResultResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not completed yet, current status: {job['status']}",
        )
    report = job.get("report", {})
    return JobResultResponse(
        job_id=job_id,
        clusters_found=report.get("clusters_found", 0),
        duplicate_pairs=report.get("duplicate_pairs", 0),
        total_records=report.get("total_records", 0),
        reduction_ratio=report.get("reduction_ratio", 0.0),
        results=[r.model_dump() for r in report.get("results", [])],
    )
