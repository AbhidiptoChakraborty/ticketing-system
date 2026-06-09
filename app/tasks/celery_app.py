import os
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
except Exception:  # pragma: no cover - optional dependency
    Celery = None

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

if Celery is not None:
    celery = Celery(
        "ticketing",
        broker=redis_url,
        backend=redis_url,
    )
    celery.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])
else:  # pragma: no cover - celery not installed in some environments
    celery = None
    logger.info("Celery not available; task queue disabled")
