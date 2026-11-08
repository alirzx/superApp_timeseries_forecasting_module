# syntax=docker/dockerfile:1.6
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES="" \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
WORKDIR /srv
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

# Reuse the known-good SuperApp Image Search strategy:
# first pure-Python CPU-Torch dependencies via Liara -> Chabokan;
# then only the official +cpu PyTorch wheel with --no-deps;
# finally Granite / FastAPI dependencies via Liara -> Chabokan.
# No fallback to pypi.org: the deployment host times out on files.pythonhosted.org.
ARG PIP_PRIMARY_INDEX_URL=https://package-mirror.liara.ir/repository/pypi/simple
ARG PIP_FALLBACK_INDEX_URL=https://mirror2.chabokan.net/pypi/simple/
ARG TORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
COPY backend/requirements-torch-cpu.txt /tmp/requirements-torch-cpu.txt
COPY backend/requirements.txt /tmp/requirements.txt

# The CPU index may delegate ordinary dependencies to files.pythonhosted.org.
# Do not allow that: install them from regional mirrors before fetching the wheel.
RUN --mount=type=cache,target=/root/.cache/pip \
    set -eu; \
    if python -m pip install --retries 2 --timeout 30 \
        --index-url "$PIP_PRIMARY_INDEX_URL" -r /tmp/requirements-torch-cpu.txt; then \
      echo "Torch runtime dependencies installed via Liara"; \
    else \
      echo "Liara unavailable for Torch deps; trying Chabokan"; \
      python -m pip install --retries 2 --timeout 30 \
        --index-url "$PIP_FALLBACK_INDEX_URL" -r /tmp/requirements-torch-cpu.txt; \
    fi

# IMPORTANT: --no-deps prevents CPU-index resolution reaching files.pythonhosted.org.
# Do not substitute the generic Linux torch wheel: it may pull CUDA libraries.
RUN --mount=type=cache,target=/root/.cache/pip \
    set -eu; \
    python -m pip install --retries 2 --timeout 90 --no-deps \
      --index-url "$TORCH_CPU_INDEX_URL" 'torch==2.10.0+cpu'; \
    python -c "import torch; assert torch.version.cuda is None, 'CUDA Torch wheel detected'; assert torch.__version__.startswith('2.10.0+cpu'), torch.__version__; print('CPU-only PyTorch verified:', torch.__version__)"

# With exact CPU Torch already installed, the resolver sees the pinned compatible
# package and should NOT attempt to replace it with generic CUDA-enabled Torch.
RUN --mount=type=cache,target=/root/.cache/pip \
    set -eu; \
    if python -m pip install --retries 2 --timeout 30 \
        --index-url "$PIP_PRIMARY_INDEX_URL" -r /tmp/requirements.txt; then \
      echo "Granite / API dependencies installed via Liara"; \
    else \
      echo "Liara unavailable for API deps; trying Chabokan"; \
      python -m pip install --retries 2 --timeout 30 \
        --index-url "$PIP_FALLBACK_INDEX_URL" -r /tmp/requirements.txt; \
    fi; \
    python -m pip check; \
    python -c "import torch; assert torch.version.cuda is None, 'CUDA Torch wheel detected'; assert torch.__version__.startswith('2.10.0+cpu'), torch.__version__; print('CPU-only PyTorch preserved:', torch.__version__)"

COPY backend/app /srv/app
COPY backend/scripts /srv/scripts
USER appuser
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--no-access-log"]
