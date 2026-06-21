"""Database configuration and session management (SQLAlchemy + SQLite)."""
from __future__ import annotations

import sqlite3
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


# Ensure the DB parent directory exists before the engine connects.
settings.database_path.parent.mkdir(parents=True, exist_ok=True)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite PRAGMA tuning + Cyrillic-aware lower()/upper()."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

        # SQLite's C-level lower()/upper() only folds ASCII; override so
        # case-insensitive search works for Cyrillic too.
        dbapi_connection.create_function(
            "lower", 1, lambda s: s.lower() if isinstance(s, str) else s
        )
        dbapi_connection.create_function(
            "upper", 1, lambda s: s.upper() if isinstance(s, str) else s
        )


engine = create_engine(
    f"sqlite:///{settings.database_path}",
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: a DB session with automatic commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """Create all tables. Imports model modules to register them on Base."""
    from app.limits import models as _limits_models  # noqa: F401
    from app.api import distributors_models as _distributor_models  # noqa: F401
    from app.api import journal_models as _journal_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
