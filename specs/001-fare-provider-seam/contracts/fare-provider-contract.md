# Provider Contract: FareProvider seam

Any fare data source plugged into cheapsawari must honor this contract
(`src/providers/base.py`).

## Interface surface

```python
class FareProvider(abc.ABC):                     # src/providers/base.py:17
    name: str                                    # stamped onto every Offer
    def get_cheapest_offer(self, origin, destination,
                           departure_date, cabin="ECONOMY") -> Offer | None
```

| Guarantee | Detail |
|---|---|
| Success value | normalized `Offer` (`src/models.py:47-72`) — never an upstream shape |
| "No inventory" | returns `None`; the API maps it to 404, the poll counts `no_inventory` |
| Failure | raises `ProviderError` (auth/network/upstream); API → 502, poll → counted, never fatal |
| Input precondition | IATA codes validated + upper-cased by the caller (`src/main.py:74,250`) |
| Composition | `src/trip.py:_cheapest_in_window` calls it once per date in a flex window; `ProviderError` must propagate unmasked (`src/trip.py:51-53`) |

## Implementations

| Provider | `name` | Mode | Auth | fare_basis | Notes |
|---|---|---|---|---|---|
| `MockFareProvider` | `mock` | default; deterministic, offline | none | ring `QLXOW/HLXOW/MLXOW/KLXOW/VLXOW` | `ZZZ` route = no-inventory sentinel (`mock.py:32`) |
| `TravelpayoutsFareProvider` | `travelpayouts` | LIVE (prod since 2026-06-24) | `X-Access-Token` header | always `None` (`travelpayouts.py:105`) | cached ~2–7-day price-trend data; cabin not filtered |
| `AmadeusFareProvider` | `amadeus` | DEPRECATED reference | OAuth2 client-credentials | real booking class | Self-Service decommissioned 2026-07-17 |

## Error mapping (Travelpayouts)

| Condition | Result |
|---|---|
| missing token at construction | `ProviderError("Travelpayouts token missing…")` (`travelpayouts.py:44-48`) |
| `httpx.HTTPError` / non-2xx | `ProviderError("Travelpayouts request failed: …")` (`travelpayouts.py:70-71`) |
| `success: false` payload | `ProviderError("Travelpayouts error: <error>")` (`travelpayouts.py:87-88`) |
| no tickets for route/date | `None` (`travelpayouts.py:93-94`) |

## Env / config knobs

| Knob | Effect |
|---|---|
| `FARE_PROVIDER` | selects the implementation (factory, `src/providers/factory.py:11-28`) |
| `TRAVELPAYOUTS_TOKEN` / `TRAVELPAYOUTS_CURRENCY` | live auth + request currency |
| `REQUEST_TIMEOUT_S` | outbound timeout (default 15 s) |
