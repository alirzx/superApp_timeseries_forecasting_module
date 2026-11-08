# API contract (v0.1)

## Authentication

Send `X-API-Key: <API_TOKEN>` on all `/v1/*` and `/metrics` endpoints. A loopback-bound
Nginx proxy injects the key server-side when using `/api/*` from the browser.
**This API key authenticates the proxy, not individual end users.** Put authenticated
HTTPS ingress / SSO ahead of the UI if exposed beyond the host.

## Routes

| Method | Route | Details |
|---|---|---|
| GET | `/health/live` | 200 while process alive |
| GET | `/health/ready` | 503 until Granite checkpoint loaded |
| GET | `/v1/models` | Loaded engines, context, horizon, revision |
| POST | `/v1/forecast` | Forecast JSON series |
| POST | `/v1/forecast/batch` | Bounded independent series |
| POST | `/v1/forecast/file` | Multipart CSV/JSON, with `timestamp_column`, `value_column`, `frequency`, `horizon`, `model_name`, `seasonal_period` |
| POST | `/v1/forecast/backtest` | Chronological holdouts; limited windows |
| GET | `/metrics` | Minimal operational metrics |

### JSON example

```json
{
  "model":"granite-ttm-r3", "frequency":"h", "horizon":12,
  "points":[
    {"timestamp":"2026-10-01T00:00:00Z","value":100.5},
    {"timestamp":"2026-10-01T01:00:00Z","value":101.0}
  ]
}
```

**Note:** The above is a *schema example*, not a valid Granite context (512 points required).
Use `datasets/sample/sample-energy.csv` for real inference examples.

### File request

```bash
set -a; . ./.env; set +a
curl -fsS -H "X-API-Key: $API_TOKEN" \
 -F 'file=@datasets/sample/sample-energy.csv' \
 -F 'model_name=granite-ttm-r3' -F 'frequency=h' -F 'horizon=24' \
 http://127.0.0.1:8005/v1/forecast/file
```

If the checkpoint has not loaded, `/v1/forecast` with `model=granite-ttm-r3`
returns HTTP 503. There is **no** silent substitution with statistical guesses.
For a deterministic statistical reference only, request `model=seasonal-naive`.

Responses contain `model`, `model_revision`, `frequency`, `horizon`,
`observations_used`, `history` (last 120 observations), `forecast` with
`timestamp`, `value`, `q10`, `q90`, `warnings`, `latency_ms`, and
`quantiles_available`. Quantiles are null for engines without quantified uncertainty.

## Preprocessing policy

- CSV requires UTF-8 (optional UTF-8 BOM), one header row, Gregorian ISO timestamps.
- Accepts timestamped numeric series only, hourly (`h`) or daily (`D`).
- Naive timestamps are UTC. Timezones normalize to UTC and are returned in UTC.
- Times must be sorted, unique, and align to exact hourly/daily frequency.
- Missing timestamps: at most `MAX_MISSING_FRACTION` and interpolate **within the observed history**.
- Backtesting rejects missing timestamps entirely. Splits occur before inference.
- Model has a fixed 512-step context, 30-step horizon, univariate channel.
- Neither outliers nor negative predictions are arbitrarily clipped or rounded.
- HTML/browser CSV preview is for display only; server validates the authoritative payload.

## Errors

- `401` invalid/missing API key.
- `413` upload too large.
- `415` unsupported media type.
- `422` validation, incompatible frequency, too-short series, unsupported horizon.
- `429` bounded inference queue full.
- `503` Granite model unavailable.
- `500` unexpected runtime/model inference failure, investigate logs.
