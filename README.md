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

## Docker quick start (CPU only)

On the host, only Docker Engine and Compose v2 are required for the container workflow. All Python requirements are installed **inside Docker**. As in SuperApp Image Search, pure-Python Torch dependencies and Granite/API requirements use **Liara first, then Chabokan**. The exact PyTorch CPU-only wheel is installed separately with `--no-deps` to avoid timeouts on `files.pythonhosted.org` (configurable `TORCH_CPU_INDEX_URL`). Initial model preparation also needs Hugging Face network access.

```bash
cp .env.example .env
# Edit .env: set API_TOKEN to a fresh secret: openssl rand -hex 32
make doctor
make model              # optional manual setup; normal compose up now auto-runs this one-shot step
make model-verify       # verifies model SHA256 manifest
# Production may derive the revision from the verified cached manifest; pin it in .env for repeatability.
make build
make up
make ps
make health             # checks Granite readiness and UI inside Docker
```

For LAN access set `UI_BIND_IP=0.0.0.0` or the server's exact LAN address in `.env`, then browse `http://SERVER_LAN_IP:8086` from a permitted LAN client. Keep `API_BIND_IP=127.0.0.1`: Nginx reaches the API through Docker's internal `api:8000` service. **The Nginx API token is not browser user authentication.** Restrict LAN access with a firewall or authenticated ingress.

Local inference test (optional, installs heavyweight Python dependencies on the host): see `docs/DEPLOYMENT.md`. Model setup requires access to Hugging Face; PyPI mirrors do **not** mirror Hugging Face model weights or Docker base images.

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
5. Frontend still uses `npm install` until a reviewed `package-lock.json` is generated and committed. Switch to `npm ci` after validating it on a network-enabled machine.
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
