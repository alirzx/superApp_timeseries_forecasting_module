# Local / server deployment

## Bootstrap on a network-enabled host

Python 3.11, Docker Engine/Compose v2, Node 22 (for local UI dev). The *one-shot*
model setup needs internet for the first download; inference is fully offline.

```bash
cp .env.example .env
openssl rand -hex 32
# Paste the output as API_TOKEN in .env; never commit it.
python3 -m venv .venv
. .venv/bin/activate
pip install 'huggingface-hub>=0.34,<2' safetensors
make model
make model-verify
# Install CPU PyTorch + the other Python dependencies if testing locally:
pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt
python scripts/model_smoke.py

docker compose --env-file .env config --quiet
make build
make up
make ps
curl -fsS http://127.0.0.1:8005/health/ready
```

UI: `http://127.0.0.1:8086` · API: `http://127.0.0.1:8005`
· OpenAPI (development only): `http://127.0.0.1:8005/docs`.

Run `python scripts/smoke_api.py --model granite-ttm-r3` from the project root
with `API_TOKEN` exported in the shell (or use `set -a; . ./.env; set +a`).

The backend Dockerfile uses **PyTorch CPU wheels** from the official CPU wheel
index; it does not pull GPU/CUDA libraries deliberately. The actual Docker build
still requires live package registry access and must be verified on the target host.

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
- Use `APP_ENV=production`, `API_AUTH_ENABLED=true`; bind host ports to loopback.
- Place authenticated TLS ingress with per-user access control and rate limits in front of UI.
- Use Docker secrets or protected deployment variables in a real production environment.
- API has one worker and bounded inference semaphore. Do not scale replica count blindly.
- The nginx token proxy is not user authentication.
- Start with `API_CPUS=2`, `API_MEMORY=2g`; these are **unvalidated budgets**.
- Pin Docker base image digests and npm lock after the first network-enabled validation.
- If UI is healthy but API readiness is 503, do not claim deploy success.

## Not included

No CI/CD file is included by request. No remote Git repository or running server
was modified. No third-party pretrained weights are committed to this source archive.
