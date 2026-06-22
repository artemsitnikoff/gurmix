#!/bin/sh
# Одноразовая настройка git-хуков версионности (запусти после клонирования репо).
# Включает .githooks как источник хуков и делает их исполняемыми.
set -e

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

echo "[gurmix] git-хуки включены: core.hooksPath=.githooks"
echo "[gurmix] текущая версия: v$(cat VERSION 2>/dev/null || echo '0.1.0')"
echo "[gurmix] PATCH будет авто-бампаться на каждом коммите; пропустить — GURMIX_NO_BUMP=1 git commit ..."
