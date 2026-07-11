# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS flightdeck
WORKDIR /build/apps/flight-deck

COPY apps/flight-deck/package*.json ./
RUN npm ci

COPY apps/flight-deck/ ./
RUN npm run build

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KAAVAL_STATIC_DIR=/app/apps/flight-deck/dist \
    KAAVAL_LIVE_RUNS_ENABLED=0 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY apps/api ./apps/api
COPY data ./data
COPY demo_artifacts ./demo_artifacts
COPY artifacts ./artifacts

RUN pip install --no-cache-dir ".[server]" \
    && adduser --disabled-password --gecos "" kaaval \
    && chown -R kaaval:kaaval /app

COPY --from=flightdeck --chown=kaaval:kaaval /build/apps/flight-deck/dist ./apps/flight-deck/dist

USER kaaval
EXPOSE 8000

CMD ["sh", "-c", "uvicorn apps.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
