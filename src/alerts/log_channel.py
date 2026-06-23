"""Default alert channel: write the alert to the application log.

Zero cost, zero configuration, zero external dependency, and safe in production —
so the alerting path is always wired and observable (Cloud Run captures logs)
even before an owner configures a real destination like a webhook.
"""
from __future__ import annotations

import logging

from ..signal import Signal
from .base import AlertChannel, render_text

_log = logging.getLogger("cheapsawari.alerts")


class LogAlertChannel(AlertChannel):
    name = "log"

    def send(self, signal: Signal) -> None:
        _log.warning("ALERT %s", render_text(signal))
