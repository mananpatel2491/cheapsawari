"""Alerts: the swappable notification seam for cheapsawari (Slice 4).

Mirrors providers/ and store/. Detection produces a Signal; an AlertChannel
delivers it. Default channel is log (zero-cost, prod-safe); webhook is the real
outbound channel. Multi-channel fan-out is a future slice — register more
channels behind the same contract.
"""
from .base import AlertChannel, AlertError, render_text
from .factory import get_alert_channel

__all__ = ["AlertChannel", "AlertError", "render_text", "get_alert_channel"]
