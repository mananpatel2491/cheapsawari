"""Email alert channel — Slice 16: notify the watch owner by email.

Stdlib only (``smtplib`` + ``email.message``), so no new dependency and still
~$0/mo. Built for Gmail SMTP (``smtp.gmail.com:587``, STARTTLS) using an app
password, but works against any SMTP server. The recipient is the per-alert
address the poll engine passes (the watch owner's Google account email); a
configured ``default_to`` is used as a fallback when an owner is unknown.

A fresh SMTP connection is opened per alert — alerts are rare (one per reopening,
once-daily poll), so a pooled client would buy nothing.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from ..signal import Signal
from .base import AlertChannel, AlertError, render_text


class EmailAlertChannel(AlertChannel):
    name = "email"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        from_addr: str,
        default_to: str | None = None,
        use_tls: bool = True,
        timeout_s: float = 15.0,
        dashboard_url: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = from_addr
        self._default_to = default_to
        self._use_tls = use_tls
        self._timeout = timeout_s
        self._dashboard_url = dashboard_url

    def build_message(self, signal: Signal, to_addr: str) -> EmailMessage:
        """Compose the alert email (separated from delivery so it's unit-testable)."""
        route = (
            f"{signal.origin}→{signal.destination}"
            if signal.origin and signal.destination
            else f"watch {signal.watch_id}"
        )
        msg = EmailMessage()
        msg["Subject"] = f"✈️ cheapsawari — fare bucket reopened: {route} (−{signal.drop_pct:.1f}%)"
        msg["From"] = self._from
        msg["To"] = to_addr
        body = render_text(signal)
        if self._dashboard_url:
            body += f"\n\nView your trackings: {self._dashboard_url}"
        body += "\n\n— cheapsawari"
        msg.set_content(body)
        return msg

    def send(self, signal: Signal, recipient: str | None = None) -> None:
        to_addr = recipient or self._default_to
        if not to_addr:
            raise AlertError(
                "email alert has no recipient (watch has no owner_email and ALERT_EMAIL_TO is unset)."
            )
        msg = self.build_message(signal, to_addr)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                if self._use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if self._username:
                    smtp.login(self._username, self._password or "")
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:  # auth / network / protocol error
            raise AlertError(f"email delivery failed: {exc}") from exc
