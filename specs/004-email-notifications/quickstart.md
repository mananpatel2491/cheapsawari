# Quickstart: Email Notifications

## 0. Compose without sending (no SMTP server needed)

```bash
cd C:\Docs\Build\mananUtils\cheapsawari
python - <<'PY'
from datetime import datetime, timezone
from src.signal import Signal
from src.alerts.email_channel import EmailAlertChannel

ch = EmailAlertChannel(host="localhost", port=25, username=None, password=None,
                       from_addr="cheapsawari (no-reply) <me@example.com>",
                       dashboard_url="https://cheapsawari.web.app")
sig = Signal(watch_id="w1", current_price=365.0, baseline_price=900.0, drop_pct=59.44,
             currency="USD", observed_at=datetime.now(timezone.utc),
             window_days=7, threshold_pct=15.0, origin="JFK", destination="LAX")
print(ch.build_message(sig, "owner@example.com"))
PY
```

Expect subject `✈️ cheapsawari — fare bucket reopened: JFK→LAX (−59.4%)` addressed to
the owner.

## 1. Degrade-to-log proof

In `.env`: `ALERT_CHANNEL=email` with `SMTP_HOST` left blank → start the app, run a
poll (spec 003 quickstart) → console warning
`ALERT_CHANNEL=email but SMTP_HOST/ALERT_EMAIL_FROM are not set; falling back to log.`
and alerts appear as log lines. The poll never crashes.

## 2. Real Gmail delivery (owner setup)

1. Gmail account: enable 2-Step Verification → create an App Password
   (Google Account → Security → App passwords).
2. `.env` (local) or Cloud Run env (prod):

```
ALERT_CHANNEL=email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<your gmail>
SMTP_PASSWORD=<16-char app password>
ALERT_EMAIL_FROM=cheapsawari (no-reply) <your gmail>
APP_BASE_URL=https://cheapsawari.web.app
```

3. Seed a dropping series on a watch you own (spec 003 quickstart step 1) so the NEXT
   recorded snapshot is a fresh rising-edge drop, then run the poll — the owner inbox
   receives the alert; logs show `alert.fired` with the recipient.

Note: Gmail will not send "from" an unverified domain (no
`noreply@cheapsawari.web.app` on free Gmail) — the display-name From above is the
supported workaround.
