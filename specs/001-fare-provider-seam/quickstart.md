# Quickstart: Fare-Provider Seam & Cheapest-Offer Lookup

## 0. Run the API locally (mock provider — the default, no credentials)

```bash
cd C:\Docs\Build\mananUtils\cheapsawari
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8050        # documented in src/main.py:3-4
```

`AUTH_MODE` defaults to `dev` (`src/config.py:97`), and the offers endpoint requires a
session — sign in first (allowlist: the admin email is always allowed):

```bash
curl -s -c c.txt -X POST http://127.0.0.1:8050/api/v1/auth/dev \
  -H "content-type: application/json" -d '{"email":"mpatel.mi24@gmail.com"}'
```

## 1. Exercise the seam

```bash
# health — shows the active provider (and the affiliate marker, spec 006)
curl -s http://127.0.0.1:8050/health
# → {"status":"ok","provider":"mock","marker":null}

# deterministic cheapest offer (same query → same price, every run)
curl -s -b c.txt "http://127.0.0.1:8050/api/v1/offers/cheapest?origin=JFK&destination=LAX&date=2026-12-01"

# failure semantics
curl -s -b c.txt "http://127.0.0.1:8050/api/v1/offers/cheapest?origin=JFK&destination=ZZZ&date=2026-12-01"   # 404 no inventory
curl -s -b c.txt "http://127.0.0.1:8050/api/v1/offers/cheapest?origin=JFK&destination=JFK&date=2026-12-01"   # 400 same city
curl -s -b c.txt "http://127.0.0.1:8050/api/v1/offers/cheapest?origin=J1K&destination=LAX&date=2026-12-01"   # 422 bad IATA
```

## 2. Bruno contract gate

```bash
cd bruno/cheapsawari
bru run offers --env local          # 7 requests; baseUrl http://127.0.0.1:8050
```

## 3. Live fares (optional — Travelpayouts token required)

In `.env` (gitignored; template in `.env.example`):

```
FARE_PROVIDER=travelpayouts
TRAVELPAYOUTS_TOKEN=<your Data-API token>
```

Restart uvicorn; `/health` now reports `"provider":"travelpayouts"`. Note: cached data —
popular routes (JFK→LAX) return prices; quiet routes/far-out dates may 404 until real
users search them (`src/providers/travelpayouts.py:11-14`).
