# Data Model: Fare-Provider Seam & Cheapest-Offer Lookup

Nothing persisted by this capability (snapshots persist Offers — spec 002/003). Shapes
below are transport and config.

## Offer (`src/models.py:47-72`) — the normalized fare record

| Field | Type | Notes |
|---|---|---|
| `origin` / `destination` | str | IATA, upper-cased by the caller (`src/main.py:250`) |
| `departure_date` | date | local to origin |
| `price` | float ≥ 0 | total price |
| `currency` | str | ISO 4217 (`USD` mock; `TRAVELPAYOUTS_CURRENCY` upper-cased live, `src/providers/travelpayouts.py:103`) |
| `cabin` | str | requested cabin (Travelpayouts does not filter by it) |
| `fare_basis` | str \| None | the "bucket" (mock: `QLXOW`… ring; Travelpayouts: always None) |
| `carrier` | str \| None | airline IATA (`airline` field upstream) |
| `provider` | str | `mock` / `travelpayouts` / `amadeus` |
| `observed_at` | datetime (UTC) | defaults to now — the time-series key |

## Travelpayouts wire shapes (`src/providers/travelpayouts.py:52-96`)

Request: `GET https://api.travelpayouts.com/v1/prices/cheap` with params
`origin, destination, depart_date=YYYY-MM-DD, currency` and header
`X-Access-Token: <token>`.

Response (documented shape, parsed at `_parse`):

```json
{
  "success": true,
  "data": { "<DEST>": { "0": { "price": 365, "airline": "B6",
             "flight_number": 615, "departure_at": "…", "return_at": "…",
             "expires_at": "…" } } },
  "error": null
}
```

- `success: false` → `ProviderError(error)` (`travelpayouts.py:87-88`)
- missing/empty `data[destination]` → `None` (`travelpayouts.py:91-94`)
- multiple tickets → min by `price` (`travelpayouts.py:96`)

## Config / env keys (`src/config.py:44-57,107-115`)

| Key | Default | Behavior |
|---|---|---|
| `FARE_PROVIDER` | `mock` | provider selection (`mock`/`travelpayouts`/`amadeus`) |
| `TRAVELPAYOUTS_TOKEN` | unset | required for `travelpayouts`; missing → `ProviderError` at construction |
| `TRAVELPAYOUTS_CURRENCY` | `usd` | request currency (lower-cased in, upper-cased on the Offer) |
| `REQUEST_TIMEOUT_S` | `15.0` | outbound HTTP timeout for all providers |
| `AMADEUS_CLIENT_ID/SECRET/BASE_URL/CURRENCY` | unset / test URL / USD | DEPRECATED — reference only |

(`TRAVELPAYOUTS_MARKER` is a dashboard/affiliate concern — spec 006.)
