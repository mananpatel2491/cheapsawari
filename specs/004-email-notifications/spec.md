# Feature Specification: Email Notifications to Watch Owners

**Feature Branch**: `retro/004-email-notifications` (as-built record — no branch created)

**Created**: 2026-07-05

**Status**: Shipped (Slice 16a, 2026-06-25; live in prod 2026-06-26, Cloud Run rev
cheapsawari-api-00015-mv9)

**Input**: retro-spec conversion of the Slice-16 email-notification portion — the
`EmailAlertChannel` + SMTP config + owner-targeted delivery, and the Gmail
From-address constraint discovered at go-live.

## Why

Log and webhook alerts (spec 003) reach the operator, not the traveler. The product is
invite-only for the owner + friends; when *their* bucket reopens, *they* should get the
email — without adding a dependency or a bill. The channel is stdlib `smtplib` +
`email.message`, Gmail-ready via an app password, and delivers to the watch owner's
Google-account email (which auth guarantees exists — spec 005).

## User Scenarios & Testing

### User Story 1 - The watch owner gets the email (Priority: P1)

The daily poll detects a reopening on Bob's watch; Bob (not the admin) receives
"✈️ cheapsawari — fare bucket reopened: JFK→LAX (−18.2%)".

**Why this priority**: the whole point — per-owner delivery is what makes alerts
useful in a multi-user invite-only app.

**Independent Test**: in-process — `EmailAlertChannel.build_message(signal, to)`
composes to the owner with the route in the subject (verified at Slice 16, changelog);
live — poll-triggered `alert.fired` observed in prod logs 2026-06-26.

**Acceptance Scenarios**:

1. **Given** a fresh signal on a watch, **When** the poll alerts, **Then** the channel
   receives `recipient=watch.owner_email` (`src/poll.py:105-107`).
2. **Given** origin/destination on the signal, **Then** the subject reads
   `✈️ cheapsawari — fare bucket reopened: {origin}→{destination} (−X.X%)`, else falls
   back to `watch {id}` (`src/alerts/email_channel.py:48-57`).
3. **Given** `APP_BASE_URL`, **Then** the body appends
   "View your trackings: https://cheapsawari.web.app" (`email_channel.py:60-62`;
   `src/config.py:86`).
4. **Given** a watch with no `owner_email` (legacy), **Then** delivery falls back to
   `ALERT_EMAIL_TO`; with neither, `AlertError` — surfaced as `alert.error`, run
   continues (`email_channel.py:66-71`; `src/poll.py:111-113`).

---

### User Story 2 - Misconfiguration never breaks the poll (Priority: P1)

`ALERT_CHANNEL=email` without SMTP settings must not crash the daily heartbeat.

**Why this priority**: constitution — the unattended run is sacred; config drift is
inevitable.

**Independent Test**: unset `SMTP_HOST`, set `ALERT_CHANNEL=email`, run a poll → a
warning "falling back to log" and a normal log alert.

**Acceptance Scenarios**:

1. **Given** `SMTP_HOST` or `ALERT_EMAIL_FROM` missing, **When** the channel is built,
   **Then** `LogAlertChannel` is returned with a warning
   (`src/alerts/factory.py:38-53`).
2. **Given** an SMTP auth/network/protocol failure at send time, **Then**
   `AlertError("email delivery failed: …")` (`email_channel.py:80-81`), counted and
   logged by the poll, never fatal.

---

### User Story 3 - Gmail-ready transport (Priority: P2)

The owner configures a Gmail app password and the channel delivers over
`smtp.gmail.com:587` with STARTTLS.

**Why this priority**: Gmail is the owner's actual mail platform; $0 posture rules out
transactional-email vendors.

**Independent Test**: prod config (2026-06-26): `SMTP_*` set on Cloud Run, from
`mpatel.mi24@gmail.com`; verified via a poll-triggered `alert.fired` in live logs.

**Acceptance Scenarios**:

1. **Given** `SMTP_USE_TLS=true` (default), **When** sending, **Then** STARTTLS with a
   default SSL context before login (`email_channel.py:74-77`;
   `src/config.py:83,130`).
2. **Given** `SMTP_USER`, **Then** `login(user, password)` runs; without it, anonymous
   relay is attempted (local relay case) (`email_channel.py:77-78`).
3. **Given** alerts are rare (rising-edge, daily poll), **Then** a fresh SMTP
   connection per alert is acceptable by design (`email_channel.py:9-11`).

### Edge Cases

- **From-address constraint (discovered at go-live, 2026-06-26)**: free Gmail SMTP
  rewrites an unverified From, so "noreply@cheapsawari.web.app" is impossible; prod
  uses the display-name workaround `cheapsawari (no-reply) <mpatel.mi24@gmail.com>` as
  the `ALERT_EMAIL_FROM` value. A true custom-domain sender needs Workspace or a
  transactional provider — accepted limitation (see research.md Decision 3).
- **Manual price entries** update the on-screen badge but email fires only from the
  poll path — stated to users in the dashboard hint (spec 006;
  `src/web/dashboard.html:719-721`).
- **Delivery timeout** bounded by `REQUEST_TIMEOUT_S` (`src/alerts/factory.py:47`).

## Requirements

### Functional Requirements

- **FR-001**: The email channel MUST be stdlib-only (`smtplib` + `email.message`) —
  no new dependency (`src/alerts/email_channel.py:14-16`; requirements.txt unchanged
  at Slice 16).
- **FR-002**: `send(signal, recipient)` MUST target the per-alert recipient, falling
  back to `ALERT_EMAIL_TO`, and raise `AlertError` when neither exists
  (`email_channel.py:66-71`).
- **FR-003**: Message composition MUST be separated from delivery
  (`build_message`) so it is unit-testable without a server (`email_channel.py:48-64`).
- **FR-004**: The channel MUST be selected by `ALERT_CHANNEL=email` and degrade to log
  when `SMTP_HOST`/`ALERT_EMAIL_FROM` are unset (`src/alerts/factory.py:56-61,38-53`).
- **FR-005**: Config MUST cover `SMTP_HOST/PORT/USER/PASSWORD/USE_TLS`,
  `ALERT_EMAIL_FROM/TO`, `APP_BASE_URL` with documented Gmail values
  (`src/config.py:72-86,126-133`; `.env.example` email block).
- **FR-006**: The email body MUST reuse the shared `render_text(signal)` one-liner so
  all channels describe an alert identically (`email_channel.py:59`;
  `src/alerts/base.py:20-34`).

### Key Entities

- **EmailAlertChannel**: the SMTP implementation of the spec-003 seam.
- **EmailMessage**: stdlib message — subject/from/to + plain-text body (shape in
  data-model.md).

## Success Criteria

- **SC-001**: Bruno `notify/` suite green (7 requests — threshold + route-carrying
  signal proofs; SMTP itself is out of Bruno's reach, verified in-process per the
  Slice 16 changelog: "email composes to the owner with route subject; no-recipient
  raises").
- **SC-002**: LIVE + VERIFIED 2026-06-26: Gmail app password set on Cloud Run
  (rev 00015-mv9), recipients = watch owners, poll-triggered `alert.fired` observed in
  prod logs.
- **SC-003**: $0/mo maintained — no dependency added, no email vendor.

## Assumptions

- The owner's Gmail account has 2FA + an app password (documented in
  `.env.example` and `src/config.py:73-78`).
- Gmail requires From == authenticated user; the display-name workaround is acceptable
  for a personal invite-only tool.
- Watch `owner_email` values are real Google accounts (guaranteed by the auth gate,
  spec 005) — so "deliver to the owner" needs no address book.
