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

### PyTorch CPU and mirror-only dependency resolution

The server previously timed out on `files.pythonhosted.org` while installing `filelock` as a dependency of `torch==2.10.0+cpu` from PyTorch's CPU wheel index. Follow the verified Image Search module pattern:

1. Install **ordinary Torch runtime dependencies** from Liara, falling back to Chabokan (`backend/requirements-torch-cpu.txt`).
2. Install only the **exact CPU-specific PyTorch wheel** from `TORCH_CPU_INDEX_URL` using `--no-deps`. This deliberately prevents the CPU index from forwarding dependency requests to the unreachable PyPI file host.
3. Install the remaining Granite / FastAPI requirements from Liara, falling back to Chabokan.
4. Run `pip check` and assert `torch.__version__.startswith('2.10.0+cpu')` and `torch.version.cuda is None`.

The ordinary Python dependency installer has **no automatic official PyPI fallback** on this host. If both regional mirrors fail, the build fails rather than silently using a broken upstream path. This fix does not mirror PyTorch's binary wheel, Hugging Face model weights, npm dependencies, or Docker base images. Real builds still require HTTPS access to those endpoints (or separately configured trusted mirrors).

For optional **host Python** smoke testing, use the same order. Execute from the repository root:

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install --index-url https://package-mirror.liara.ir/repository/pypi/simple -r backend/requirements-torch-cpu.txt || python -m pip install --index-url https://mirror2.chabokan.net/pypi/simple/ -r backend/requirements-torch-cpu.txt
python -m pip install --no-deps --index-url https://download.pytorch.org/whl/cpu 'torch==2.10.0+cpu'
python -m pip install --index-url https://package-mirror.liara.ir/repository/pypi/simple -r backend/requirements.txt || python -m pip install --index-url https://mirror2.chabokan.net/pypi/simple/ -r backend/requirements.txt
python -m pip check
python -c "import torch; assert torch.version.cuda is None; assert torch.__version__.startswith('2.10.0+cpu')"
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

The organization's CI file is maintained separately by the DevOps team; this service does not modify or generate it.
The current CI must be reviewed before auto-deploy, including SSH setup, model staging, revision pinning and deployment gating.
The server has not been modified by this source patch. No third-party pretrained weights are committed.

## Rootless UI: Nginx temp directories and API DNS resilience

The UI runs as non-root UID 10001 with a read-only filesystem. Nginx needs all
five temporary paths on the writable `/tmp` tmpfs: client-body, proxy,
FastCGI, uWSGI and SCGI. Leaving the three latter modules at the Nginx default
(`/var/cache/nginx`) causes `mkdir(...fastcgi_temp) failed (13: Permission denied)`
and restarts.

The API may not exist in Docker DNS during startup (for example, if
production is missing `MODEL_REVISION`). The UI uses Docker's embedded DNS
resolver `127.0.0.11` and a variable upstream to resolve `api:8000` when each
`/api/...` request arrives. Static frontend routes stay available while the
API is unavailable; failed API requests return an upstream error until the API
is started. The `/api/v1/...` prefix is stripped before proxying so FastAPI
still receives `/v1/...`. The UI has no startup dependency on API.

Useful diagnostics on the actual server:

```bash
docker compose ps -a
docker compose logs --tail=100 ui
docker compose logs --tail=100 api
docker compose port ui 8080
curl -i http://127.0.0.1:8086/
curl -i http://127.0.0.1:8005/health/ready
```

Successful `docker compose up -d` only confirms the start command ran. It
does not prove that API or UI stays running. If UI is healthy but the model
API is not, check production `MODEL_REVISION`, readable model files and
`manifest.json`; run `make model`, `make model-verify` and set the exact
verified revision before restarting API. Do not turn off the production
revision guard or publish `API_TOKEN` in diagnostics.
