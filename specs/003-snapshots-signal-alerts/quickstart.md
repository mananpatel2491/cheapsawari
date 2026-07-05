# Quickstart: Snapshots, Poll Engine, Reopen Detection & Alerts

Prereq: API on port 8050 + dev session cookie `c.txt` (spec 001 quickstart step 0).

## 1. Seed a deterministic series and trigger a signal

```bash
# create a watch
WID=$(curl -s -b c.txt -X POST http://127.0.0.1:8050/api/v1/watches \
  -H "content-type: application/json" \
  -d '{"origin":"JFK","destination":"LAX","departure_date":"2026-12-01"}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# seed 110 / 108 / 112 then a 90 drop (manual snapshots, provider='manual')
for p in 110 108 112 90; do
  curl -s -b c.txt -X POST http://127.0.0.1:8050/api/v1/watches/$WID/snapshots \
    -H "content-type: application/json" -d "{\"price\": $p}" > /dev/null
done

# on-demand detection → detected=true, drop_pct ≈ 18.18 (90 vs mean(110,108,112)=110)
curl -s -b c.txt http://127.0.0.1:8050/api/v1/watches/$WID/signal
```

Re-run the last call after seeding another low point — `detected` stays true on the
endpoint (level check per latest point) but the POLL only alerts on the rising edge.

## 2. Run the poll engine

```bash
# open locally when POLL_TOKEN is unset:
curl -s -X POST http://127.0.0.1:8050/api/v1/poll
# → {"active_watches":N,"polled":N,"recorded":…,"no_inventory":…,"errors":0,
#    "skipped_over_cap":0,"alerts_fired":…}

# with a token (prod posture): set POLL_TOKEN=test-poll-token in .env, restart, then
curl -s -X POST http://127.0.0.1:8050/api/v1/poll -H "X-Poll-Token: test-poll-token"
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8050/api/v1/poll   # 401
```

Watch the terminal: the run emits `poll.run` (and `ALERT ✈️ Bucket reopened…` +
`alert.fired` when a seeded drop is fresh) via the structured logger (spec 007).

## 3. Per-watch threshold

```bash
# a watch alerting at 8% instead of the 15% default
curl -s -b c.txt -X POST http://127.0.0.1:8050/api/v1/watches \
  -H "content-type: application/json" \
  -d '{"origin":"DTW","destination":"ORD","departure_date":"2026-11-15","alert_threshold_pct":8}'
```

## 4. Bruno gates

```bash
cd bruno/cheapsawari
bru run poll signal notify --env local
```

(`local.bru` sets `pollToken: test-poll-token` — export POLL_TOKEN accordingly before
running the poll suite.)
