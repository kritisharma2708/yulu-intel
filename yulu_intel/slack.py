import logging
import time
from typing import Dict, List, Optional

import requests

from yulu_intel.config import settings

logger = logging.getLogger(__name__)


def _post_webhook(payload: Dict) -> None:
    resp = requests.post(
        settings.SLACK_WEBHOOK_URL,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()


def _post_bot(payload: Dict, thread_ts: Optional[str] = None) -> Optional[str]:
    body = {
        "channel": settings.SLACK_CHANNEL,
        "blocks": payload["blocks"],
    }
    if thread_ts:
        body["thread_ts"] = thread_ts

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        json=body,
        headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")
    return data.get("ts")


def send_messages(payloads: List[Dict]) -> None:
    if settings.SLACK_BOT_TOKEN and settings.SLACK_CHANNEL:
        logger.info("Sending via bot token to %s", settings.SLACK_CHANNEL)
        thread_ts = None
        for i, payload in enumerate(payloads):
            ts = _post_bot(payload, thread_ts=thread_ts)
            if i == 0:
                thread_ts = ts
            logger.info("  Message %d/%d sent", i + 1, len(payloads))
            time.sleep(1)
    elif settings.SLACK_WEBHOOK_URL:
        logger.info("Sending via webhook")
        for i, payload in enumerate(payloads):
            _post_webhook(payload)
            logger.info("  Message %d/%d sent", i + 1, len(payloads))
            time.sleep(1)
    else:
        raise RuntimeError(
            "No Slack credentials configured. Set SLACK_WEBHOOK_URL or (SLACK_BOT_TOKEN + SLACK_CHANNEL) in .env"
        )
