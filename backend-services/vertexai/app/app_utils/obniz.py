import logging
import time
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class ObnizController:
    def __init__(self, obniz_id: Optional[str] = None):
        self.obniz_id = obniz_id
        self.webhook_url = os.environ.get("OBNIZ_WEBHOOK_URL")

        if not self.webhook_url:
            logger.warning("OBNIZ_WEBHOOK_URL is not set. ObnizController will run in MOCK mode.")
        else:
            logger.info(f"Initialized ObnizController with Webhook URL: {self.webhook_url[:20]}...")

    def rotate(self, angle: int) -> bool:
        """
        Rotates the motor to the specified absolute angle (0-180).
        Sends a POST request to the obniz Webhook.
        """
        logger.info(f"[Obniz] Rotating motor to angle: {angle}")

        if not self.webhook_url:
            logger.info("[Obniz] Mock rotation (no webhook url).")
            return True

        try:
            payload = {"angle": angle}
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"[Obniz] Webhook success: {response.text}")
            return True
        except Exception as e:
            logger.error(f"[Obniz] Webhook failed: {e}")
            return False

    def scan_surroundings(self) -> str:
        """
        Performs a sequence of rotations to scan the surroundings.
        Returns a session ID for the scan.
        """
        session_id = f"scan_{int(time.time())}"
        logger.info(f"[Obniz] Starting scan session: {session_id}")

        # Real logic would likely involve generator or callback to capture images at each step
        # For now, just a placeholder as scan logic is complex via simple webhook
        return session_id

    def get_current_angle(self) -> int:
        """
        Returns the current estimated motor angle.
        """
        # Without bi-directional comms, we can't easily get the real angle.
        # We might track it locally if needed.
        return 0
