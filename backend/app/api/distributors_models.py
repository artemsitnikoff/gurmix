"""SQLAlchemy model for the distributors directory (module 8, mode='db')."""
from __future__ import annotations

import logging

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, engine
from app.core.migrations import register_schema_probe

logger = logging.getLogger(__name__)


class Distributor(Base):
    __tablename__ = "distributors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


def _init_schema() -> bool:
    try:
        Base.metadata.create_all(bind=engine, tables=[Distributor.__table__])
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("distributors schema init failed: %s", e)
        return False


_schema_ok = _init_schema()
register_schema_probe("distributors", lambda: _schema_ok)
