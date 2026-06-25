"""Webhook alert channel: POST the alert as JSON to a configured URL.

The single "real" delivery channel. The payload carries a ``text`` field (so it
drops straight into a Slack/Discord/Mattermost incoming webhook) plus the full
structured ``signal`` for anything that wants the raw data. Uses httpx, already a
dependency — no new package, still ~$0/mo.
"""
from __future__ import annotations

import httpx

from ..signal import Signal
from .base import AlertChannel, AlertError, render_text


class WebhookAlertChannel(AlertChannel):
    name = "webhook"

    def __init__(self, url: str, timeout_s: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout_s

    def send(self, signal: Signal, recipient: str | None = None) -> None:
        payload = {"text": render_text(signal), "signal": signal.model_dump(mode="json")}
        try:
            resp = httpx.post(self._url, json=payload, timeout=self._timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # network error or non-2xx
            raise AlertError(f"webhook delivery failed: {exc}") from exc
