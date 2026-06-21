"""SQLAlchemy model for per-user quota counters.

«Один пользователь» = пара (session_id, ip). Лимит на запросы (первично) +
опц. оценка токенов; период сброса day/week/month настраивается в конфиге.
"""
from __future__ import annotations

import logging

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, engine
from app.core.migrations import register_schema_probe

logger = logging.getLogger(__name__)


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("session_id", "ip", "period_start", name="uq_usage_window"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    ip: Mapped[str] = mapped_column(String, index=True, nullable=False, default="")
    # ISO-date string of the window start (e.g. "2026-06-21" for day period).
    period_start: Mapped[str] = mapped_column(String, index=True, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    est_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


def _init_schema() -> bool:
    try:
        Base.metadata.create_all(bind=engine, tables=[UsageCounter.__table__])
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("usage_counters schema init failed: %s", e)
        return False


_schema_ok = _init_schema()
register_schema_probe("usage_counters", lambda: _schema_ok)
