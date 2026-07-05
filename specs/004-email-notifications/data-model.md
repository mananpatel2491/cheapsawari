# Data Model: Email Notifications

Nothing persisted — this capability is transport (SMTP) + config. Recipient identity
lives on the watch (`owner_email`, spec 002).

## Composed message (`src/alerts/email_channel.py:48-64`)

| Header/part | Value |
|---|---|
| Subject | `✈️ cheapsawari — fare bucket reopened: {origin}→{destination} (−{drop_pct:.1f}%)` — falls back to `watch {watch_id}` when the signal has no route |
| From | `ALERT_EMAIL_FROM` verbatim (prod value uses the display-name form `cheapsawari (no-reply) <mpatel.mi24@gmail.com>`) |
| To | `recipient` (watch owner) or `ALERT_EMAIL_TO` fallback |
| Body | `render_text(signal)` (`src/alerts/base.py:20-34`) + `\n\nView your trackings: {APP_BASE_URL}` + `\n\n— cheapsawari` |

Example body line:

```
✈️ Bucket reopened for JFK→LAX: USD 365.00 (59.4% below the 7-day avg of USD 900.00)

View your trackings: https://cheapsawari.web.app

— cheapsawari
```

## Config / env keys (`src/config.py:79-86,126-133`)

| Key | Default | Notes |
|---|---|---|
| `SMTP_HOST` | unset | unset → channel degrades to log |
| `SMTP_PORT` | 587 | Gmail STARTTLS port |
| `SMTP_USER` / `SMTP_PASSWORD` | unset | Gmail: the account + 16-char app password (needs 2FA) |
| `SMTP_USE_TLS` | true | STARTTLS with `ssl.create_default_context()`; false only for a local relay |
| `ALERT_EMAIL_FROM` | unset | unset → degrade to log; Gmail rewrites unverified addresses (see research Decision 3) |
| `ALERT_EMAIL_TO` | unset | fallback recipient for ownerless (legacy) watches |
| `APP_BASE_URL` | `https://cheapsawari.web.app` | linked in the body |
| `ALERT_CHANNEL` | `log` | must be `email` to activate this channel |

Delivery timeout: `REQUEST_TIMEOUT_S` (15 s default) passed as `timeout_s`
(`src/alerts/factory.py:47`).
