# Builder stage
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY engine/ engine/
COPY api/ api/

# Install dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages and source
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/engine/src /app/engine/src
COPY --from=builder /app/api/src /app/api/src

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "margin_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
