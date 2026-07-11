# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS flightdeck
WORKDIR /build/apps/flight-deck

COPY apps/flight-deck/package*.json ./
RUN npm ci

COPY apps/flight-deck/ ./
RUN npm run build

FROM python:3.11-slim AS python-deps

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra server --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra server

FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Kaaval Assurance" \
      org.opencontainers.image.description="Contract-gated inference assurance plane" \
      org.opencontainers.image.source="https://github.com/kaaval-ai/kaaval-assurance" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    KAAVAL_STATIC_DIR=/app/apps/flight-deck/dist \
    KAAVAL_LIVE_RUNS_ENABLED=0 \
    KAAVAL_ALLOW_PAID_REMOTE=0 \
    KAAVAL_ALLOW_ARTIFACT_EXPORT=0 \
    KAAVAL_ALLOW_DIAGNOSTIC_RAW=0 \
    PORT=8000

WORKDIR /app

COPY --from=python-deps /app/.venv /app/.venv
COPY --chown=root:root src ./src
COPY --chown=root:root apps/api ./apps/api
COPY --chown=root:root data ./data
COPY --chown=root:root demo_artifacts ./demo_artifacts
COPY --chown=root:root artifacts ./artifacts

RUN adduser --system --uid 10001 --group --no-create-home kaaval \
    && mkdir -p /app/artifacts/live-exports /tmp/kaaval \
    && chown -R kaaval:kaaval /app/artifacts/live-exports /tmp/kaaval

COPY --from=flightdeck --chown=root:root /build/apps/flight-deck/dist ./apps/flight-deck/dist

USER kaaval
EXPOSE 8000
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT','8000') + '/api/health', timeout=3).read()"

CMD ["sh", "-c", "exec uvicorn apps.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
