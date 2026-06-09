from nsi_normalizer.workers.celery_app import celery_app


@celery_app.task(name="nsi_normalizer.deduplicate")
def deduplicate_task(job_id: str, record_type: str) -> dict[str, str]:
    # Will be implemented in Phase 5
    return {"job_id": job_id, "status": "pending"}
