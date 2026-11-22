# syntax=docker/dockerfile:1
# STATUS: written but NOT built or run in the authoring sandbox (no Docker there). Verify with `docker compose build`.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/models/hf \
    MLAI_DATABASE_URL=sqlite:////data/app.sqlite3

RUN pip install --no-cache-dir uv

# Mirror the repository layout so the helper scripts (../scripts) work inside the container too.
WORKDIR /repo/backend
COPY backend/pyproject.toml ./
# CPU-only PyTorch comes from the index configured in pyproject.toml. No lock file is committed yet:
# run `uv lock` in backend/ on your machine, commit uv.lock, then change this line to `uv sync --frozen ...`.
RUN uv sync --no-install-project --no-dev --extra ml

COPY backend/ /repo/backend/
COPY scripts/ /repo/scripts/
COPY docs/ /repo/docs/

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /models /data \
    && chown -R appuser:appuser /models /data /repo
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3).status == 200 else 1)"

# Weights are NOT baked into the image: they live in the /models volume (see docs/INSTALLATION.md).
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
