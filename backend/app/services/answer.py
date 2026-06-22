"""Answer service: per-module prompt → Claude CLI → (answer_html, meta).

Phase callbacks mirror the teplodar SSE pipeline: intent → retrieval → answer.
This is a thin orchestration layer:

  - module_id → Module.full_system_prompt from the registry
  - assemble prompt (system + ~6 turns of history + question)
  - call Claude CLI (llm mode — активные модули 6, 7, 8 в демо-режиме)
  - module mode='db' answers from the distributors table (дремлющая ветка:
    активируется, когда у модуля выставлен mode=db и в базе есть контакты)

Демо-режим (фаза 1): активные модули отвечают напрямую промптом к Opus, без
RAG-корпуса (подмешивание — фаза 2). Ответ модели — Markdown; бэкенд отдаёт его
как есть (`answer_html`), фронт рендерит и санитизирует (marked + DOMPurify).
CPU/blocking work runs in a worker thread (SSE route → asyncio.to_thread).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.claude_cli import ClaudeCLIError, call_cli
from app.core.config import settings
from app.modules.registry import MODULES_BY_ID, ModuleMode

logger = logging.getLogger(__name__)

PhaseCallback = Callable[[str], None]

_HISTORY_TURNS = 6  # ~6 ходов истории

_NO_DISTRIBUTOR_TEXT = (
    "Подтверждённых контактов в базе нет — оставьте заявку, "
    "менеджер свяжется."
)

_FALLBACK_TEXT = (
    "Извините, не удалось получить ответ. Попробуйте ещё раз чуть позже."
)


@dataclass
class AnswerMeta:
    module_id: str
    query_type: str = "llm"
    top_score: float | None = None
    chunks_used: int = 0
    t_intent_ms: int = 0
    t_retrieval_ms: int = 0
    t_answer_ms: int = 0
    t_answer_model: str = ""
    latency_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "module_id": self.module_id,
            "query_type": self.query_type,
            "top_score": self.top_score,
            "chunks_used": self.chunks_used,
            "t_intent_ms": self.t_intent_ms,
            "t_retrieval_ms": self.t_retrieval_ms,
            "t_answer_ms": self.t_answer_ms,
            "t_answer_model": self.t_answer_model,
            "latency_ms": self.latency_ms,
        }


def _build_prompt(system_prompt: str, message: str, history: list[dict]) -> str:
    """Assemble the full text prompt for the CLI (system + history + question)."""
    parts: list[str] = [system_prompt, ""]
    recent = history[-_HISTORY_TURNS:] if history else []
    if recent:
        parts.append("Контекст диалога:")
        for turn in recent:
            role = turn.get("role", "user")
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            label = "Пользователь" if role == "user" else "Ассистент"
            parts.append(f"{label}: {content}")
        parts.append("")
    parts.append(f"Вопрос пользователя: {message}")
    parts.append("")
    parts.append("Дай развёрнутый экспертный ответ по делу, оформи его в Markdown.")
    return "\n".join(parts)


def _answer_db(db: Session, message: str, meta: AnswerMeta) -> str:
    """Module 8: answer strictly from the distributors table.

    Naive region match: ищем дистрибьюторов, где регион входит в текст вопроса
    (или наоборот). Если ничего — текст «оставьте заявку».
    """
    from app.api.distributors_models import Distributor

    rows = db.execute(select(Distributor)).scalars().all()
    q = message.lower()
    matched = [
        d for d in rows
        if d.region and (d.region.lower() in q or q in d.region.lower())
    ]
    meta.query_type = "db"
    meta.chunks_used = len(matched)

    if not matched:
        return _NO_DISTRIBUTOR_TEXT

    lines = ["**Подтверждённые контакты из базы:**", ""]
    for d in matched:
        bits = [f"- **{d.name}** ({d.region})"]
        if d.phone:
            bits.append(f"  тел.: {d.phone}")
        if d.email:
            bits.append(f"  email: {d.email}")
        if d.address:
            bits.append(f"  адрес: {d.address}")
        if d.note:
            bits.append(f"  {d.note}")
        lines.append("\n".join(bits))
    return "\n".join(lines)


def answer_with_meta(
    db: Session,
    module_id: str,
    message: str,
    history: list[dict] | None = None,
    on_phase: PhaseCallback | None = None,
) -> tuple[str, AnswerMeta]:
    """Produce (answer_html, meta) for one chat turn.

    Blocking — designed to run in a worker thread. `on_phase` is invoked with
    "intent" → "retrieval" → "answer" so the SSE route can stream phase events.
    """
    history = history or []
    meta = AnswerMeta(module_id=module_id)
    t_start = time.monotonic()

    def phase(name: str) -> None:
        if on_phase:
            try:
                on_phase(name)
            except Exception:  # noqa: BLE001 — phase callback must never break the pipeline
                logger.debug("on_phase callback raised", exc_info=True)

    module = MODULES_BY_ID.get(module_id)
    if module is None:
        meta.query_type = "ERROR"
        meta.latency_ms = int((time.monotonic() - t_start) * 1000)
        return f"Неизвестный модуль: {module_id}", meta

    # ── Phase 1: intent (заглушка — фаза вычисляется тривиально) ──────────
    phase("intent")
    t0 = time.monotonic()
    meta.t_intent_ms = int((time.monotonic() - t0) * 1000)

    # ── Phase 2: retrieval (RAG-подмешивание — заглушка, фаза 2) ──────────
    phase("retrieval")
    t0 = time.monotonic()
    if module.mode == ModuleMode.DB:
        answer_html = _answer_db(db, message, meta)
        meta.t_retrieval_ms = int((time.monotonic() - t0) * 1000)
        phase("answer")
        meta.latency_ms = int((time.monotonic() - t_start) * 1000)
        return answer_html, meta
    # llm modes (6, 7, 8): RAG corpus not wired yet — фаза 2.
    meta.t_retrieval_ms = int((time.monotonic() - t0) * 1000)

    # ── Phase 3: answer (Claude CLI) ──────────────────────────────────────
    phase("answer")
    t0 = time.monotonic()
    prompt = _build_prompt(module.full_system_prompt, message, history)
    meta.t_answer_model = settings.claude_model
    try:
        answer_html = call_cli(prompt, model=settings.claude_model)
    except ClaudeCLIError as e:
        logger.error("[answer] Claude CLI failed for module=%s: %s", module_id, e)
        meta.query_type = "ERROR"
        meta.t_answer_ms = int((time.monotonic() - t0) * 1000)
        meta.latency_ms = int((time.monotonic() - t_start) * 1000)
        return _FALLBACK_TEXT, meta

    meta.t_answer_ms = int((time.monotonic() - t0) * 1000)
    meta.latency_ms = int((time.monotonic() - t_start) * 1000)
    return answer_html, meta
