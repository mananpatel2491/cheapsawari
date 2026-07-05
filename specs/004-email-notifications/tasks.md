---
description: "As-built task record for owner-targeted email notifications"
---

# Tasks: Email Notifications to Watch Owners

As-built record — reconstructed 2026-07-05 from Slice 16a (2026-06-25) and the prod
go-live (2026-06-26). `[X]` = shipped; `[ ]` = genuinely open.

## Phase 1: Seam widening (US1)

- [X] T001 [US1] `AlertChannel.send(signal, recipient=None)` contract change;
  log/webhook ignore the recipient (`src/alerts/base.py:43-50`) (Slice 16)
- [X] T002 [US1] Poll passes `recipient=watch.owner_email`; `alert.fired` event logs
  the recipient (`src/poll.py:105-110`) (Slice 16)
- [X] T003 [US1] `Signal.origin/destination` from the triggering snapshot's legs
  (`src/signal.py:48-50,116-119`) (Slice 16)

## Phase 2: Channel (US1, US2, US3)

- [X] T004 [US3] `src/alerts/email_channel.py`: stdlib SMTP channel — STARTTLS,
  optional login, fresh connection per send, timeout (Slice 16)
- [X] T005 [US1] `build_message`: route-first subject, `render_text` body, dashboard
  link, `— cheapsawari` signature; separated from delivery for unit tests (Slice 16)
- [X] T006 [US2] No-recipient → `AlertError`; SMTP/OS failures → `AlertError`
  (Slice 16)
- [X] T007 [US2] `src/alerts/factory.py:_build_email`: build from current settings
  (uncached), degrade to log when SMTP_HOST/ALERT_EMAIL_FROM unset (Slice 16)

## Phase 3: Config + verification

- [X] T008 [P] `src/config.py` + `.env.example`: SMTP_HOST/PORT/USER/PASSWORD/USE_TLS,
  ALERT_EMAIL_FROM/TO, APP_BASE_URL with Gmail app-password instructions (Slice 16)
- [X] T009 In-process verification: per-owner composition, no-recipient raise; Bruno
  `notify/` suite green (97/242/13) for the API-visible side (Slice 16)
- [X] T010 Prod go-live: SMTP_* set on Cloud Run rev cheapsawari-api-00015-mv9, From =
  `cheapsawari (no-reply) <mpatel.mi24@gmail.com>` (Gmail rewrites unverified Froms);
  verified via poll-triggered `alert.fired` in live logs (2026-06-26)

## Open follow-ups (genuinely pending)

- [ ] T011 True custom-domain sender (noreply@cheapsawari.web.app) — requires Google
  Workspace or a transactional provider; deliberately deferred (research Decision 3)
- [ ] T012 `docs/DEPLOYMENT.md` still documents prod as `ALERT_CHANNEL=log`
  (`docs/DEPLOYMENT.md:24-25`) — stale since the 2026-06-26 email go-live (doc-only
  drift; report to Director)
