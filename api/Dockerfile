# Builder stage
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY engine/ engine/
COPY api/ api/

# Install dependencies, then swap torch for CPU-only build (~200 MB vs ~3.7 GB CUDA)
RUN uv sync --frozen --no-dev --package margin-api && \
    uv pip install torch --index-url https://download.pytorch.org/whl/cpu --reinstall

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages and source
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/engine/src /app/engine/src
COPY --from=builder /app/engine/universe.yaml /app/engine/universe.yaml
COPY --from=builder /app/api/src /app/api/src
COPY --from=builder /app/api/alembic.ini /app/api/alembic.ini
COPY --from=builder /app/api/alembic /app/api/alembic

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "cd /app/api && alembic upgrade head && cd /app && uvicorn margin_api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
