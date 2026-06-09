from celery import Celery
from nsi_normalizer.config import settings

celery_app = Celery(
    "nsi_normalizer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["nsi_normalizer.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
)
