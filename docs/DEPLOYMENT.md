# Local / server deployment

## Bootstrap on a network-enabled Docker host

Only Docker Engine + Compose v2 are required for the container workflow. Model setup is an ephemeral **profiled** service, not a third always-on container. Docker's Python dependency installs use Liara, then Chabokan if needed. The CPU-only PyTorch wheel is fetched separately from the CPU wheel index (override `TORCH_CPU_INDEX_URL` with a trusted internal CPU-wheel mirror if needed). Hugging Face weights, npm dependencies and Docker base images are separate distribution channels.

```bash
cp .env.example .env
# Generate API_TOKEN with: openssl rand -hex 32, and set it in .env
make doctor
make model
make model-verify
python3 - <<'PYIN'
import json
from pathlib import Path
print('Pin MODEL_REVISION='+json.loads(Path('.models/granite-ttm-r3/manifest.json').read_text())['revision'])
PYIN
# Production: add that exact MODEL_REVISION to .env before make up
make build
make up
make ps
make health
```

Local UI: `http://127.0.0.1:8086`, API: `http://127.0.0.1:8005`.
Server UI from LAN: set `UI_BIND_IP=0.0.0.0` (or a specific interface IP), then browse `http://SERVER_LAN_IP:8086`. API should remain bound to `127.0.0.1` on the host; the UI proxy uses `http://api:8000` inside Compose. A LAN listener is **not** authenticated user access; apply a firewall and/or identity-aware HTTPS ingress.

For an optional **host Python** smoke test, install CPU PyTorch and dependencies with the designated indexes, then run the actual model smoke test:

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.10.0+cpu'
python -m pip install --index-url https://package-mirror.liara.ir/repository/pypi/simple -r backend/requirements.txt || python -m pip install --index-url https://mirror2.chabokan.net/pypi/simple/ -r backend/requirements.txt
python scripts/model_smoke.py
```

## Local UI without Docker

```bash
cd frontend
npm install
# from repository root: set -a; . ./.env; set +a (in the shell running npm)
npm run dev
```

Run the backend separately with `PYTHONPATH=backend uvicorn app.main:app --port 8005`.
The Vite dev server proxies `/api/*` and attaches `API_TOKEN` **server-side**, not
from a browser `VITE_` variable. Never include the key in front-end JavaScript.

## Production

- Use `.env.production.example` as a checklist, **not** as a secret file.
- Set a strong per-service token and immutable model revision.
- Transfer `.models/granite-ttm-r3` securely after `model-verify`; retain manifest.
- Use `APP_ENV=production`, `API_AUTH_ENABLED=true`; keep API host port on loopback. Bind UI to the LAN interface only if the firewall/ingress limits clients.
- Place authenticated TLS ingress with per-user access control and rate limits in front of UI.
- Use Docker secrets or protected deployment variables in a real production environment.
- API has one worker and bounded inference semaphore. Do not scale replica count blindly.
- The nginx token proxy is not user authentication.
- Start with `API_CPUS=2`, `API_MEMORY=2g`; these are **unvalidated budgets**.
- Pin Docker base image digests and generate a reviewed npm lockfile after the first network-enabled validation.
- If UI is healthy but API readiness is 503, do not claim deploy success.

## Not included

No CI/CD file is included by request. The server has not been modified by this patch.
No third-party pretrained weights are committed to the repository.
