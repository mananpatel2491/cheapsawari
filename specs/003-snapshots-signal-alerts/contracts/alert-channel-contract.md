# Seam Contract: AlertChannel

Every notification destination implements `src/alerts/base.py:37-50`.

## Interface surface

```python
class AlertChannel(abc.ABC):                      # src/alerts/base.py:37
    name: str
    def send(self, signal: Signal, recipient: str | None = None) -> None
```

| Guarantee | Detail |
|---|---|
| Failure | raises `AlertError`; the poll logs `alert.error` and continues (`src/poll.py:111-113`) |
| `recipient` | per-alert destination for person-targeting channels (email → watch owner); fixed-destination channels (log, webhook) ignore it |
| Rendering | human text comes from shared `render_text(signal)` (`base.py:20-34`) — route-first wording, falls back to watch id |
| Cardinality | called at most once per watch per poll run (rising-edge detection upstream) |

## Implementations & selection

| Channel | `name` | Destination | Failure mode |
|---|---|---|---|
| `LogAlertChannel` | `log` | app log WARNING `ALERT …` (`log_channel.py:20-21`) | none (default; prod-safe, Cloud Run captures it) |
| `WebhookAlertChannel` | `webhook` | httpx POST `{text, signal}` to `ALERT_WEBHOOK_URL` (`webhook_channel.py:23-29`) | non-2xx/network → `AlertError` |
| `EmailAlertChannel` | `email` | SMTP to `recipient` or `ALERT_EMAIL_TO` (spec 004) | SMTP/OS error → `AlertError`; no recipient → `AlertError` |

Factory (`src/alerts/factory.py:56-61`): `ALERT_CHANNEL` ∈ {log, webhook, email};
misconfiguration (webhook without URL :22-28, email without SMTP_HOST/FROM :38-53)
**degrades to log with a warning — never crashes the poll loop**. Log/webhook channels
are lru_cached per process; email is rebuilt per call (holds no connection, :33-37).

## Env knobs

| Knob | Effect |
|---|---|
| `ALERT_CHANNEL` | selects the channel (default `log`) |
| `ALERT_WEBHOOK_URL` | webhook target |
| `SMTP_*`, `ALERT_EMAIL_FROM/TO`, `APP_BASE_URL` | email channel (spec 004 contract) |
| `REQUEST_TIMEOUT_S` | delivery timeout for webhook/email |
