"""Idempotent migration helpers shared by all model modules.

SQLAlchemy `create_all` never alters existing tables, so a model file that adds
a new column emits an ALTER on import. Concurrent processes can race on the
ALTER — whichever loses gets "duplicate column" / "already exists", which we
treat as success.

Each model module registers a `_schema_ok` probe so startup code can fail-fast
instead of running queries against a broken schema. Use `assert_schema_ready()`
from `main.py` before serving traffic.
"""
from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy import text

logger = logging.getLogger(__name__)

_schema_probes: list[tuple[str, Callable[[], bool]]] = []


def safe_alter(conn, sql: str) -> None:
    """Execute an ALTER, swallowing 'column already exists' races.

    Re-raises any other error so genuine schema bugs surface.
    """
    try:
        conn.execute(text(sql))
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        if "duplicate column" in msg or "already exists" in msg:
            return
        raise


# Backwards-compatible alias matching the teplodar reference name.
_safe_alter = safe_alter


def register_schema_probe(name: str, probe: Callable[[], bool]) -> None:
    """Register a `() -> bool` that reports whether `name`'s schema is OK."""
    _schema_probes.append((name, probe))


def assert_schema_ready(expected: list[str] | None = None) -> None:
    """Raise RuntimeError if any registered model failed to init.

    Pass `expected` to also guard against calling this before the model modules
    have been imported (empty probe list would otherwise sail through).
    """
    registered = {name for name, _ in _schema_probes}
    if expected:
        missing = [name for name in expected if name not in registered]
        if missing:
            raise RuntimeError(
                f"Schema probes not registered for: {', '.join(missing)} — "
                "import the model modules before calling assert_schema_ready()"
            )

    broken = [name for name, probe in _schema_probes if not probe()]
    logger.info(
        "Schema probe check: %d registered (%s), %d broken",
        len(_schema_probes),
        ", ".join(sorted(registered)),
        len(broken),
    )
    if broken:
        raise RuntimeError(
            f"DB schema not ready for modules: {', '.join(broken)} "
            "(check earlier log for the underlying SQLAlchemy error)"
        )
