import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

from typing import Any

# import celery app lazily; Celery may be optional in some envs
from app.tasks.celery_app import celery

if celery:
    # register a simple celery task to run notifications in the worker
    @celery.task(name="app.tasks.notifications.send_notification_task")
    def send_notification_task(message: str) -> None:
        logger.info(f"NOTIFICATION (worker): {message}")


async def send_notification(message: str) -> None:
    """Enqueue a notification to the Celery worker if available, otherwise log locally."""
    if celery:
        try:
            # use delay to enqueue the task
            send_notification_task.delay(message)
            return
        except Exception:
            logger.exception("Failed to enqueue notification task; falling back to local log")

    logger.info(f"NOTIFICATION: {message}")
