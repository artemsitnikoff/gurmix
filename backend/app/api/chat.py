"""Chat router — SSE pipeline with module routing + quota enforcement.

POST /chat/stream — SSE по контракту: события phase/done/error/limit.
  Перед пайплайном проверяется квота (session_id из тела + IP из запроса).
  Если исчерпана → событие 'limit' и Claude НЕ вызывается (HTTP всё равно 200).
  При успешном ответе счётчик инкрементится.
POST /chat/feedback — 👍/👎 (+ заметка) на строку query_logs.
GET  /quota — текущая QuotaState для (session_id, ip).
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.database import SessionLocal
from app.limits import store as quota_store
from app.schemas import ChatFeedbackRequest, ChatRequest
from app.services.answer import answer_with_meta

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])

_LIMIT_TEXT = (
    "Лимит запросов исчерпан. Попробуйте позже — счётчик сбросится "
    "в начале нового периода."
)


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _client_ip(request: Request) -> str:
    # Respect a single proxy hop; fall back to the socket peer.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


# ── LLM-as-judge (асессор полезности) — fire-and-forget после ответа ──────────
# Судья (Haiku) оценивает полезность ответа в фоне и пишет usefulness_* в
# query_logs. Планируется ДО финального yield (чтобы задача создалась даже при
# мгновенном дисконнекте клиента); strong-ref в _judge_tasks переживает отмену
# генератора. Параллелизм судей < размера слот-пула — оставляем слот живому чату.
_judge_tasks: set[asyncio.Task] = set()
_judge_sem: asyncio.Semaphore | None = None


def _get_judge_sem() -> asyncio.Semaphore:
    global _judge_sem
    if _judge_sem is None:
        cap = max(1, min(2, settings.claude_cli_max_concurrent - 1))
        _judge_sem = asyncio.Semaphore(cap)
    return _judge_sem


def _judge_and_persist(log_id: int, question: str, answer: str) -> None:
    """Синхронно: оценить ответ и записать usefulness_* (в worker-потоке)."""
    from sqlalchemy import update

    from app.api.journal_models import QueryLog
    from app.services.judge import judge_answer

    verdict = judge_answer(question, answer)
    if not verdict:
        return
    # Таргетный UPDATE только колонок судьи — не затираем пользовательский feedback.
    with SessionLocal() as s:
        s.execute(
            update(QueryLog)
            .where(QueryLog.id == log_id)
            .values(
                usefulness_score=verdict["score"],
                usefulness_verdict=verdict["verdict"],
            )
        )
        s.commit()


async def _judge_in_background(log_id: int, question: str, answer: str) -> None:
    async with _get_judge_sem():
        try:
            # И CLI-вызов, и запись в БД — в worker-потоке, не блокируя event loop.
            await asyncio.to_thread(_judge_and_persist, log_id, question, answer)
        except Exception as e:  # noqa: BLE001 — судья best-effort, не критичен
            logger.debug("[judge] failed for log_id=%s: %s", log_id, e)


def _spawn_judge(log_id: int, question: str, answer: str) -> None:
    """Оценить ответ судьёй в фоне — не блокирует выдачу ответа пользователю."""
    try:
        task = asyncio.create_task(_judge_in_background(log_id, question, answer))
    except RuntimeError:
        return  # нет running loop — пропускаем
    _judge_tasks.add(task)
    task.add_done_callback(_judge_tasks.discard)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    """Run the pipeline and stream phase events, then one `done` (or `limit`)."""
    message = req.message.strip()
    module_id = req.module_id
    session_id = req.session_id
    ip = _client_ip(request)
    history = [{"role": t.role, "content": t.content} for t in req.history]

    async def event_stream():
        # ── Quota gate (before any Claude call) ───────────────────────────
        with SessionLocal() as s:
            quota = quota_store.get_quota(s, session_id, ip)
        if quota["blocked"]:
            yield _sse({"type": "limit", "message": _LIMIT_TEXT, "quota": quota})
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_phase_threadsafe(name: str) -> None:
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "phase", "phase": name}
            )

        def worker():
            # Fresh DB session per call (used by the dormant db-mode branch).
            with SessionLocal() as session:
                return answer_with_meta(
                    session, module_id, message,
                    history=history, on_phase=on_phase_threadsafe,
                )

        gen_task = asyncio.create_task(asyncio.to_thread(worker))
        try:
            while not gen_task.done() or not queue.empty():
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=0.3)
                except asyncio.TimeoutError:
                    continue
                yield _sse(ev)
            answer_html, meta = await gen_task
        except Exception as e:  # noqa: BLE001
            logger.error("[chat] generation failed: %s", e, exc_info=True)
            if not gen_task.done():
                gen_task.cancel()
            yield _sse({
                "type": "error",
                "message": "Извините, не удалось получить ответ. Попробуйте ещё раз.",
            })
            return

        # ── Persist + increment quota on a real answer ────────────────────
        log_id = None
        new_quota = quota
        with SessionLocal() as s:
            try:
                from app.api.journal_models import QueryLog

                row = QueryLog(
                    session_id=session_id,
                    module_id=module_id,
                    question=message,
                    answer=answer_html,
                    query_type=meta.query_type,
                    latency_ms=meta.latency_ms,
                    t_answer_model=meta.t_answer_model,
                    top_score=meta.top_score,
                    chunks_used=meta.chunks_used,
                )
                s.add(row)
                s.flush()
                log_id = row.id
                if meta.query_type != "ERROR":
                    new_quota = quota_store.increment(s, session_id, ip)
                s.commit()
            except Exception as e:  # noqa: BLE001
                logger.error("[chat] persist/increment failed: %s", e, exc_info=True)
                s.rollback()

        # Планируем судью в фоне ДО финального yield — задача создаётся даже если
        # клиент отключится сразу после 'done' (judge_answer + запись идут в
        # worker-потоке и переживают завершение SSE-ответа).
        if log_id and answer_html and meta.query_type != "ERROR":
            _spawn_judge(log_id, message, answer_html)

        yield _sse({
            "type": "done",
            "answer_html": answer_html,
            "log_id": log_id,
            "meta": meta.to_dict(),
            "quota": new_quota,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/feedback")
async def chat_feedback(req: ChatFeedbackRequest) -> dict:
    """Store 👍/👎 (+ optional note) against a query_logs row."""
    note = (req.note or "").strip()[:4000] or None

    def _store():
        from app.api.journal_models import QueryLog

        with SessionLocal() as s:
            row = s.get(QueryLog, req.log_id)
            if row is None:
                return False
            row.feedback = req.feedback
            row.feedback_note = note
            s.commit()
            return True

    ok = await asyncio.to_thread(_store)
    return {"ok": ok}


@router.get("/quota")
async def get_quota(request: Request, session_id: str = Query(...)) -> dict:
    """Current QuotaState for (session_id, ip)."""
    ip = _client_ip(request)

    def _read():
        with SessionLocal() as s:
            return quota_store.get_quota(s, session_id, ip)

    return await asyncio.to_thread(_read)
