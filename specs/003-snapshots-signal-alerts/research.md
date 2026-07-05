# Research: Snapshots, Poll Engine, Reopen Detection & Alert Seam

As-built record — decisions reconstructed 2026-07-05 from Slice 3a/4/16 changelog rows
and module docstrings.

## Decision 1 — Quota cap as the poll's core design constraint

**Choice**: hard cap `POLL_MAX_PER_RUN` (default 60) per run; one provider failure is
counted, not fatal (`src/poll.py:7-11,75-83`).
**Why**: designed against Amadeus's per-API free quota (budget math documented at
`src/config.py:34-38`); survives unchanged on Travelpayouts where it's now a politeness
cap (`docs/DEPLOYMENT.md:90`).
**Rejected**: unbounded polling (one bad day of watch growth burns the month's quota).

## Decision 2 — Optional shared-secret poll token, not full auth

**Choice**: `POLL_TOKEN` + `X-Poll-Token` header; endpoint open when unset
(`src/main.py:462-472`; `src/config.py:39-41`).
**Why**: the caller is a machine (Cloud Scheduler), not a user — session auth doesn't
fit; the threat is quota-burning by strangers on a public URL, which a static header
secret fully addresses at $0. The poll stays outside `require_user` deliberately
(`src/main.py:478` comment in Slice 6 row: "poll stays token-gated for the scheduler").

## Decision 3 — Rising-edge trigger with zero persisted alert state

**Choice**: fire only when the latest point is a drop AND the previous point was not
(`src/signal.py:104-111`); minimum history 3 (`src/signal.py:28-31`).
**Why**: an unattended daily poll would otherwise re-fire every day the price stayed
low; the snapshot series itself is the dedup memory (`src/signal.py:12-17`).
**Rejected**: persisted `alerted_at` state (schema + corruption risk on backfill),
cooldown timers (arbitrary; still re-fires on long lows).

## Decision 4 — Trailing moving-average baseline (mean over a day-window)

**Choice**: baseline = mean of prior points within `window_days` of the pivot
(`src/signal.py:61-76`); defaults 15% / 7 days env-tunable (`src/config.py:70-71`).
**Why**: robust to slow drift (window moves), cheap, explainable in an alert ("−X%
below the 7-day avg of $Y").
**Rejected**: min-of-window (over-sensitive to a single spike), EWMA (harder to
explain, marginal benefit at daily granularity).

## Decision 5 — Manual snapshots as a first-class endpoint

**Choice**: `POST /watches/{id}/snapshots` records `provider="manual"` rows, past
`observed_at` allowed (`src/main.py:398-429`; `src/models.py:226-242`).
**Why**: dual purpose — user backfill/reference logging (surfaced in UI at Slice 19)
AND deterministic test seeding: the stateless mock can't build a trend by polling, so
Bruno's signal cases seed exact series (Slice 4 changelog).
**Clarified (Slice 19)**: there is deliberately NO "baseline input" — the baseline is
always the computed trailing average; a manual $900 series is just history.

## Decision 6 — Per-watch threshold override, server default fallback

**Choice**: `alert_threshold_pct` (1..90, optional) on the watch;
`watch.alert_threshold_pct or default` at both detection sites
(`src/models.py:106-112`; `src/main.py:454-455`; `src/poll.py:99-100`).
**Why**: different trips have different noise (a $2000 multi-city vs a $150 shuttle);
`None` keeps the server default authoritative. The 1-floor makes the falsy `or` safe
(0 is not a legal value).
**Rejected**: per-user global preference (wrong granularity), separate thresholds
table (a nullable column suffices).

## Decision 7 — AlertChannel as the third seam, degrade-to-log

**Choice**: `AlertChannel.send(signal, recipient)` with log (default) / webhook /
email implementations; factory degrades to log on missing webhook URL or SMTP config
instead of crashing the poll loop (`src/alerts/factory.py:20-53`).
**Why**: the daily heartbeat must never die because notification config is incomplete;
alerts still surface in Cloud Run logs (`src/alerts/log_channel.py:1-6`). Multi-channel
fan-out later = "register more channels", not a rewrite (`src/alerts/base.py:5-8`).
