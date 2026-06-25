"""Alert-channel selection — resolves the active AlertChannel from settings.

Cached so a channel (and any client it holds) is built once per process, matching
the providers/ and store/ factories.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from ..config import Settings, get_settings
from .base import AlertChannel
from .email_channel import EmailAlertChannel
from .log_channel import LogAlertChannel
from .webhook_channel import WebhookAlertChannel

_log = logging.getLogger("cheapsawari.alerts")


@lru_cache(maxsize=1)
def _build(channel: str, webhook_url: str | None, timeout_s: float) -> AlertChannel:
    if channel == "webhook":
        if webhook_url:
            return WebhookAlertChannel(webhook_url, timeout_s=timeout_s)
        # Configured for webhook but no URL — degrade to log rather than crash the
        # poll loop. Alerts still surface (in logs); they just aren't delivered out.
        _log.warning("ALERT_CHANNEL=webhook but ALERT_WEBHOOK_URL is unset; falling back to log.")
        return LogAlertChannel()
    return LogAlertChannel()


def _build_email(settings: Settings) -> AlertChannel:
    """Build the email channel, or degrade to log if SMTP isn't configured.

    Not cached (an EmailAlertChannel holds no persistent client — it connects per
    send), so it always reflects the current settings.
    """
    if settings.smtp_host and settings.alert_email_from:
        return EmailAlertChannel(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.alert_email_from,
            default_to=settings.alert_email_to,
            use_tls=settings.smtp_use_tls,
            timeout_s=settings.request_timeout_s,
            dashboard_url=settings.app_base_url,
        )
    _log.warning(
        "ALERT_CHANNEL=email but SMTP_HOST/ALERT_EMAIL_FROM are not set; falling back to log."
    )
    return LogAlertChannel()


def get_alert_channel(settings: Settings | None = None) -> AlertChannel:
    """Return the configured AlertChannel (default: log)."""
    settings = settings or get_settings()
    if settings.alert_channel == "email":
        return _build_email(settings)
    return _build(settings.alert_channel, settings.alert_webhook_url, settings.request_timeout_s)
