# Implementation Plan: Email Notifications to Watch Owners

**Branch**: `retro/004-email-notifications` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: As-built reconstruction from Slice 16a (2026-06-25) and the prod email
go-live (2026-06-26).

## Summary

`EmailAlertChannel` (`src/alerts/email_channel.py`) implements the spec-003
`AlertChannel` seam over stdlib SMTP: `build_message` composes a route-first subject +
`render_text` body + dashboard link; `send` opens a fresh STARTTLS connection per
alert, targeting `recipient` (the watch owner passed by the poll) with `ALERT_EMAIL_TO`
as fallback. The factory builds it uncached from current settings and degrades to log
when SMTP is unconfigured. The `AlertChannel.send` contract gained the `recipient`
parameter in the same slice (log/webhook ignore it).

## Technical Context

**Language/Version**: Python 3.13; stdlib `smtplib`, `ssl`, `email.message` only

**Primary Dependencies**: none added (explicit Slice 16 constraint)

**Storage**: none — recipient comes from the watch's `owner_email` (spec 002/005)

**Testing**: in-process unit checks on `build_message` / no-recipient raise (Slice 16
changelog); Bruno `notify/` suite for the detection side; live verification via
`alert.fired` in prod logs (2026-06-26)

**Target Platform**: Cloud Run (prod: Gmail SMTP egress) + local dev

**Project Type**: web service — one seam implementation + config

**Performance Goals**: alerts are rare (rising-edge × daily poll) → connection-per-send
is deliberate (`email_channel.py:9-11`)

**Constraints**: $0/mo (free Gmail SMTP); secrets live in Cloud Run env (SMTP_PASSWORD);
Gmail From must equal the authenticated account

**Scale/Scope**: 1 channel (~80 lines) + factory branch + 8 config keys

## Constitution Check

Gated against `.specify/memory/constitution.md` (distillation; `GEMINI.md` supreme).

- **I. Context-First Architecture Map — PASS.** `src/alerts/email_channel.py` mapped
  (`Project_Structure.md:51`); the Slice 16 changelog row lists every touched file.
- **II. Pattern Reference Integrity — PASS.** Extends the sacred `AlertChannel` seam
  (log/webhook/email named in `.specify/memory/constitution.md:29`) by widening
  `send()` — no bypass, no parallel mailer.
- **III. Automated Maintenance via Agentic Skills — PASS.** No manual state; factory
  reads current settings per call so env flips need no code.
- **IV. Continuous API Validation (Bruno) — PASS.** The API-visible surface
  (threshold + route-carrying signal) is covered by the self-cleaning `notify/` suite
  in the 97/242/13 gate; SMTP delivery is outside Bruno's reach and was verified
  in-process + live (documented, not hand-waved).
- **V. Infrastructure-as-Code & Cost Gating — PASS.** No new infra (SMTP is Gmail's);
  Cloud Run env change only; cost review $0 (Slice 16 changelog). Terraform correctly
  untouched.

## Project Structure

### Documentation (this feature)

```text
specs/004-email-notifications/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    └── email-channel-contract.md
```

### Source Code (repository root)

```text
src/
├── alerts/
│   ├── email_channel.py       # EmailAlertChannel: build_message + STARTTLS send  (Slice 16)
│   ├── base.py                # send(signal, recipient) contract widening         (Slice 16)
│   └── factory.py             # email branch + degrade-to-log (_build_email)      (Slice 16)
├── poll.py:105-107            # recipient = watch.owner_email                     (Slice 16)
├── signal.py:48-50            # origin/destination on Signal (route-first email)  (Slice 16)
└── config.py:72-86            # SMTP_* / ALERT_EMAIL_* / APP_BASE_URL             (Slice 16)
```

**Structure Decision**: a third `AlertChannel` implementation — the seam absorbed the
feature; the only cross-cutting change was the additive `recipient` parameter.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Email channel is NOT lru_cached (unlike log/webhook) | it must reflect current settings and holds no persistent client (`factory.py:33-37`) | caching rejected: stale SMTP creds after an env flip would silently fail until restart |
| `send()` signature changed on the whole seam for one channel | per-owner delivery is the feature; a channel-specific side API would leak email knowledge into the poll | poll calling `EmailAlertChannel` concretely rejected — breaks the seam the constitution names |
