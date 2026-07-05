# Research: Email Notifications to Watch Owners

As-built record — decisions reconstructed 2026-07-05 from the Slice 16 changelog row,
module docstrings, and the 2026-06-26 go-live notes.

## Decision 1 — Stdlib SMTP over a transactional-email vendor

**Choice**: `smtplib` + `email.message`, Gmail app-password auth
(`src/alerts/email_channel.py:1-11`).
**Why**: zero new dependency, ~$0/mo, and the audience is the owner + a few friends —
volume is a handful of emails a month. Deliverability tooling (SendGrid/SES/Postmark)
buys nothing at this scale and breaks the $0 gate.
**Rejected**: SendGrid/Mailgun/SES (account + billing + API key management for ~5
emails/month), Gmail API via OAuth (heavier auth for the same outcome).

## Decision 2 — Deliver to the watch owner, not a fixed inbox

**Choice**: `AlertChannel.send` gained `recipient`; the poll passes
`watch.owner_email`; `ALERT_EMAIL_TO` is only a fallback for ownerless legacy watches
(`src/alerts/base.py:43-50`; `src/poll.py:105-107`; `email_channel.py:66-71`).
**Why**: invite-only multi-user product — Bob's fare drop is Bob's email. The owner
email is guaranteed real (it's the Google sign-in identity, spec 005).
**Rejected**: single configured recipient (owner would forward alerts by hand),
per-watch email field (redundant with ownership).

## Decision 3 — Gmail From-address constraint: display-name workaround

**Context (go-live 2026-06-26)**: the desired sender was
`noreply@cheapsawari.web.app`, but free Gmail SMTP rewrites any From the account
hasn't verified — the email arrives from the raw Gmail address regardless.
**Choice**: set `ALERT_EMAIL_FROM` to the display-name form
`cheapsawari (no-reply) <mpatel.mi24@gmail.com>` so clients show a product-ish sender
while the address remains the authenticated account (config value, not code; the code
just honors `ALERT_EMAIL_FROM`, `email_channel.py:57`; config note "Gmail requires
this to be the authenticated SMTP_USER", `.env.example`).
**Rejected**: Google Workspace / custom-domain SMTP or a transactional provider (cost
and setup for a personal tool) — recorded as the known path if a true custom-domain
sender is ever wanted.

## Decision 4 — Route on the Signal so the email reads as a place

**Choice**: `Signal` carries `origin`/`destination` from the triggering snapshot's
legs; subject = `fare bucket reopened: JFK→LAX (−18.2%)` (`src/signal.py:48-50,116-119`;
`email_channel.py:50-57`).
**Why**: "watch 3f2a…" is meaningless in an inbox; the route is the user's mental key.
Fallback wording keeps legacy (leg-less) snapshots working.

## Decision 5 — Degrade to log, never crash the heartbeat

**Choice**: factory returns `LogAlertChannel` (with a warning) when
`SMTP_HOST`/`ALERT_EMAIL_FROM` are unset (`src/alerts/factory.py:38-53`); send-time
failures raise `AlertError`, which the poll counts and survives.
**Why**: same posture as the webhook channel (spec 003 Decision 7): notification
config must never take down the daily poll; alerts still surface in Cloud Run logs.

## Decision 6 — Fresh connection per send

**Choice**: `with smtplib.SMTP(...)` per alert (`email_channel.py:74-79`).
**Why**: alerts are rare by construction (rising edge × once-daily poll); pooling adds
state and reconnect logic for zero benefit (`email_channel.py:9-11`).
