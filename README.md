# SuperApp Module 05: CPU Time-Series Forecasting

A standalone Persian RTL forecasting service built around **IBM Granite
TinyTimeMixer R3**, running *only on CPU*. Backend: FastAPI + Python 3.11.
Frontend: React/TypeScript/Vite + Nginx. Two long-running Docker services.

## Scope

- Zero-shot single-series forecast (Granite TTM-R3, 512 observed points, up to 30 future points).
- CSV/JSON upload with strict timestamp/value validation and bounded interpolation.
- JSON and file forecasting endpoints, bounded multi-series batch, and historical backtesting.
- Forecast point values, timestamp generation and native quantiles (when emitted).
- Explicit seasonal-naive reference engine for debugging/short histories.
- Responsive RTL forecasting dashboard with charts, upload, results table and JSON export.
- Synthetic 720-hour energy-demand input, usable in the UI and API.
- Model revision/hash manifest, offline-only runtime, request authentication, health and metrics.

## Quick start

```bash
cp .env.example .env
# Replace API_TOKEN with: openssl rand -hex 32
python3 -m venv .venv && . .venv/bin/activate
pip install 'huggingface-hub>=0.34,<2' safetensors
make model              # first time requires Hugging Face access
make model-verify       # verify pinned model SHA256 manifest
make build
make up
make health             # Granite readiness required
python scripts/smoke_api.py --model granite-ttm-r3
```

UI: http://127.0.0.1:8086 · API: http://127.0.0.1:8005.

For direct local model execution:

```bash
pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt
python scripts/model_smoke.py
```

See `docs/DEPLOYMENT.md` for deployment details and `docs/API.md` for requests.

## Testing the service without model weights

This is intentionally **not** an ML inference test. It exercises only the API,
preprocessing and explicitly labeled statistical reference model.

```bash
pip install -r backend/requirements-test.txt
PYTHONPATH=backend pytest -q backend/tests
# API can run without weights but Granite readiness will be HTTP 503.
# For local-only reference mode, use API_AUTH_ENABLED=false and request model=seasonal-naive.
```

## Important caveats

1. Source archive **does not contain pretrained model weights**, npm dependencies,
   or CI/CD configuration (per request).
2. The IBM checkpoint requires a real one-time download and runtime validation on
   the intended CPU; no fake model is used in the production inference path.
3. Local development/verification of the backend tests passed, but the real
   Granite CPU smoke and full UI build could not run in the offline artifact environment.
4. The 2 GB memory and sub-second latency are design targets, not measured claims.
5. Docker Vite build currently uses `npm install` because the registry is unavailable
   in the artifact environment. Generate and commit `package-lock.json`, then
   switch to `npm ci` on a machine with registry access.
6. `/v1/forecast/batch` runs independently per series. This is NOT native
   multivariate/covariate forecasting.
7. Model license is Apache-2.0 per IBM's model card; verify model and dependency
   license and distribution requirements before commercial release.

## API

`/health/live`, `/health/ready`, `/v1/models`, `/v1/forecast`,
`/v1/forecast/file`, `/v1/forecast/batch`, `/v1/forecast/backtest`, `/metrics`.

## Source

Based on the user-provided SuperApp deep-research architecture and current
IBM Granite R3 model/API documentation. The implementation code in this repo
is new, not a mirror of IBM's source repository.
