# Seam Contract: EmailAlertChannel (SMTP)

The email implementation of the spec-003 `AlertChannel` seam
(`src/alerts/email_channel.py`).

## Interface surface

```python
EmailAlertChannel(host, port, username, password, from_addr,
                  default_to=None, use_tls=True, timeout_s=15.0,
                  dashboard_url=None)                    # email_channel.py:25-37
.build_message(signal, to_addr) -> EmailMessage          # :48 (pure, unit-testable)
.send(signal, recipient=None) -> None                    # :66
```

## Behavioral guarantees

| Guarantee | Detail |
|---|---|
| Recipient resolution | `recipient` (watch owner from the poll) → else `default_to` (`ALERT_EMAIL_TO`) → else `AlertError` (:66-71) |
| Transport | fresh `smtplib.SMTP` per send; STARTTLS with default SSL context when `use_tls`; `login()` only when a username is set (:74-79) |
| Failure | `smtplib.SMTPException` / `OSError` → `AlertError("email delivery failed: …")` (:80-81); caller (poll) survives |
| Subject | `✈️ cheapsawari — fare bucket reopened: {route} (−{drop:.1f}%)`; route falls back to `watch {id}` (:50-57) |
| Body | shared `render_text(signal)` + optional `View your trackings: {dashboard_url}` + signature (:59-63) |

## Selection & degrade modes (`src/alerts/factory.py:32-61`)

| Condition | Result |
|---|---|
| `ALERT_CHANNEL=email` + `SMTP_HOST` + `ALERT_EMAIL_FROM` set | EmailAlertChannel (built per call, uncached) |
| `ALERT_CHANNEL=email`, SMTP incomplete | LogAlertChannel + warning — poll never crashes |

## Env knobs

`SMTP_HOST`, `SMTP_PORT=587`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS=true`,
`ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO`, `APP_BASE_URL`, `REQUEST_TIMEOUT_S`
(`src/config.py:79-86`).

## Known limitations (accepted)

- Free Gmail SMTP rewrites unverified From addresses → prod sender is the
  display-name form `cheapsawari (no-reply) <mpatel.mi24@gmail.com>`, not a
  custom-domain no-reply (research Decision 3).
- Plain-text body only; no HTML template, no unsubscribe (invite-only personal tool).
- One recipient per alert; no CC/BCC/digest.
