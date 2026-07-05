# Quickstart: Watch Tracking

Prereq: API running on port 8050 with a dev session cookie (`c.txt`) — see
`specs/001-fare-provider-seam/quickstart.md` steps 0.

## 1. One-way watch lifecycle

```bash
# create
curl -s -b c.txt -X POST http://127.0.0.1:8050/api/v1/watches \
  -H "content-type: application/json" \
  -d '{"origin":"JFK","destination":"LAX","departure_date":"2026-12-01"}'
# → 201 {"id":"<uuid>", "active":true, "owner_email":"mpatel.mi24@gmail.com", ...}

WID=<uuid from above>
curl -s -b c.txt http://127.0.0.1:8050/api/v1/watches                    # list (yours)
curl -s -b c.txt -X POST http://127.0.0.1:8050/api/v1/watches/$WID/refresh   # price now
curl -s -b c.txt "http://127.0.0.1:8050/api/v1/watches/$WID/snapshots?limit=10"
```

## 2. Round-trip with flex

```bash
curl -s -b c.txt -X POST http://127.0.0.1:8050/api/v1/watches \
  -H "content-type: application/json" \
  -d '{"origin":"DTW","destination":"AMS","departure_date":"2026-10-08",
       "trip_type":"round_trip","return_date":"2026-10-20",
       "depart_flex_days":3,"return_flex_days":3}'
```

## 3. Multi-city (transfer hub as an explicit leg)

```bash
curl -s -b c.txt -X POST http://127.0.0.1:8050/api/v1/watches \
  -H "content-type: application/json" \
  -d '{"trip_type":"multi_city","legs":[
        {"origin":"DTW","destination":"CDG","date":"2026-12-01","flex_days":2},
        {"origin":"CDG","destination":"AMD","date":"2026-12-03","flex_days":2}]}'
```

## 4. Edit in place (history preserved)

```bash
curl -s -b c.txt -X PUT http://127.0.0.1:8050/api/v1/watches/$WID \
  -H "content-type: application/json" \
  -d '{"origin":"JFK","destination":"SFO","departure_date":"2026-12-05",
       "trip_type":"one_way","depart_flex_days":1}'
# id/created_at/owner unchanged; snapshots kept

curl -s -b c.txt -X DELETE http://127.0.0.1:8050/api/v1/watches/$WID     # 204, cascades
```

## 5. Bruno gates

```bash
cd bruno/cheapsawari
bru run watches roundtrip multicity update --env local
```

Store swap: set `WATCH_STORE=firestore` + ADC/`GOOGLE_CLOUD_PROJECT` to run the same
flows against Cloud Firestore (prod parity; the full gate was verified green on both —
Slice 3b changelog).
