"""Версия приложения. Источник истины — файл VERSION в корне репозитория.

Читается один раз при импорте. Локально это `<repo>/VERSION`; в Docker-образе
файл копируется в `/app/VERSION` (см. Dockerfile). Бампается git-хуком
`.githooks/pre-commit`. Если файл недоступен — отдаём `0.0.0`, не падаем.
"""
from __future__ import annotations

from pathlib import Path

_DEFAULT = "0.0.0"


def _read_version() -> str:
    here = Path(__file__).resolve()  # backend/app/core/version.py
    candidates = [
        here.parents[3] / "VERSION",  # <repo>/VERSION (локально) и /app/VERSION (Docker)
        Path("/app/VERSION"),         # явная подстраховка для контейнера
    ]
    for p in candidates:
        try:
            if p.is_file():
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    return text
        except OSError:
            continue
    return _DEFAULT


APP_VERSION = _read_version()
