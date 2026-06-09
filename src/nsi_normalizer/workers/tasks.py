from __future__ import annotations

import uuid

from nsi_normalizer.workers.celery_app import celery_app


@celery_app.task(name="nsi_normalizer.run_deduplication", bind=True)
def run_deduplication(
    self: object,
    job_id: str,
    record_type: str,
    threshold: float = 0.65,
    records_payload: list[dict] | None = None,
) -> dict[str, object]:
    from nsi_normalizer.ml.pipeline import DeduplicationPipeline
    from nsi_normalizer.schemas.common import RawRecord
    from nsi_normalizer.store import job_store, record_store

    jid = uuid.UUID(job_id)
    job_store.update(jid, status="running")

    try:
        if records_payload:
            # Records passed directly — works across containers (no shared memory needed)
            records = [RawRecord(**r) for r in records_payload]
        else:
            records = record_store.get_all(record_type=record_type)  # type: ignore[arg-type]

        pipeline = DeduplicationPipeline(threshold=threshold)
        report = pipeline.run(records)

        job_store.complete(jid, report)
        return {"job_id": job_id, "status": "completed", "clusters": report.clusters_found}

    except Exception as exc:
        job_store.fail(jid, str(exc))
        raise
