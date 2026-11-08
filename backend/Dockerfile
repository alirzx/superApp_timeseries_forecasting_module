FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES="" \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
WORKDIR /srv
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser
COPY backend/requirements.txt /tmp/requirements.txt
# Runtime installs a pinned Granite dependency range; build requires PyPI availability.
ARG TORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --index-url "$TORCH_CPU_INDEX_URL" torch==2.10.0 \
    && pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend/app /srv/app
COPY backend/scripts /srv/scripts
USER appuser
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--no-access-log"]
