"""SQLAlchemy model for the query journal (порт teplodar query_logs).

Каждый ход чата сохраняется сюда: вопрос, ответ, модуль, тайминги, фидбэк.
"""
from __future__ import annotations

import logging

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, engine
from app.core.migrations import register_schema_probe, safe_alter

logger = logging.getLogger(__name__)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped["DateTime"] = mapped_column(DateTime, server_default=func.now(), index=True)
    session_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    module_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_type: Mapped[str | None] = mapped_column(String, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    t_answer_model: Mapped[str | None] = mapped_column(String, nullable=True)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    chunks_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Feedback (set via POST /chat/feedback).
    feedback: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # LLM-as-judge usefulness (асинхронно после ответа). NULL = ещё не оценено.
    usefulness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usefulness_verdict: Mapped[str | None] = mapped_column(Text, nullable=True)


def _init_schema() -> bool:
    try:
        Base.metadata.create_all(bind=engine, tables=[QueryLog.__table__])
        # Идемпотентные ALTER для legacy-БД (созданных до появления колонок судьи).
        with engine.begin() as conn:
            safe_alter(conn, "ALTER TABLE query_logs ADD COLUMN usefulness_score INTEGER")
            safe_alter(conn, "ALTER TABLE query_logs ADD COLUMN usefulness_verdict TEXT")
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("query_logs schema init failed: %s", e)
        return False


_schema_ok = _init_schema()
register_schema_probe("query_logs", lambda: _schema_ok)
