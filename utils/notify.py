"""Push notification utilities for error alerting."""

import os

from loguru import logger
from pushbullet import Pushbullet


def send_error_notification(message: str, title: str = "REJECTION SCRIPTING ERROR") -> None:
    """Send error notification via Pushbullet.
    
    Args:
        message: Error message to send
        title: Notification title (default: "REJECTION SCRIPTING ERROR")
    """
    api_key = os.getenv('PUSHBULLET_API_KEY')
    
    if not api_key:
        logger.warning("PUSHBULLET_API_KEY not set, skipping notification")
        return
    
    try:
        pb = Pushbullet(api_key)
        pb.push_note(title, message)
        logger.info(f"Sent notification: {title}")
    except Exception as e:
        logger.error(f"Failed to send Pushbullet notification: {e}")