import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


async def send_notification(message: str):

    logger.info(f"NOTIFICATION: {message}")
