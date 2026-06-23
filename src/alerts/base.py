"""The AlertChannel contract — the swappable notification seam.

Mirrors the providers/ and store/ seams: the rest of the app fires a Signal at an
``AlertChannel`` and never knows whether it became a log line, a webhook POST, or
something added later. Keeping a single-channel contract here is deliberate — the
roadmap's multi-channel fan-out (Discord/Slack/Telegram) becomes "register more
channels", not a rewrite.
"""
from __future__ import annotations

import abc

from ..signal import Signal


class AlertError(RuntimeError):
    """Raised when a channel fails to deliver an alert (caller decides fatality)."""


def render_text(signal: Signal) -> str:
    """Human-readable one-liner shared by every channel."""
    return (
        f"✈️ Bucket reopened for watch {signal.watch_id}: "
        f"{signal.currency} {signal.current_price:.2f} "
        f"({signal.drop_pct:.1f}% below the {signal.window_days}-day avg of "
        f"{signal.currency} {signal.baseline_price:.2f})"
        + (f" — bucket {signal.fare_basis}" if signal.fare_basis else "")
    )


class AlertChannel(abc.ABC):
    """Abstract single-destination alert sink."""

    name: str

    @abc.abstractmethod
    def send(self, signal: Signal) -> None:
        """Deliver one alert. Raise :class:`AlertError` on delivery failure."""
