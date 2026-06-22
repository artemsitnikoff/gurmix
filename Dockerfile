# ── Stage 1: build React (Vite) frontend ─────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# VERSION (корень репо) нужен vite для подстановки __APP_VERSION__ (../VERSION).
COPY VERSION /VERSION
RUN npm run build
# -> /build/dist

# ── Stage 2: Python runtime + Claude CLI ─────────────────────────────────────
FROM python:3.11-slim

# System deps + Node.js (нужен для Claude CLI), + Claude Code CLI глобально.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g @anthropic-ai/claude-code && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python-зависимости отдельно (лучше кэш слоёв).
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Код бэкенда.
COPY backend/ /app/backend/

# Версия (единый источник истины) — читается бэкендом в рантайме (app/core/version.py).
COPY VERSION /app/VERSION

# Собранный SPA из stage 1. main.py отдаёт его из <repo>/frontend/dist,
# что в образе резолвится как /app/frontend/dist.
COPY --from=frontend-builder /build/dist /app/frontend/dist

# base/ и data/ монтируются как volume в рантайме — не пекём в образ.
# data/ на проде — симлинк (-> ArkadiyJarvis/data), поэтому он в .dockerignore.

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1
ENV APP_PORT=8420

# cwd = backend, чтобы base/gurmix.db и data/.claude_token.json резолвились.
WORKDIR /app/backend

EXPOSE 8420

# Порт настраивается одной переменной APP_PORT (на проде «много чего занято»).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8420}"]
