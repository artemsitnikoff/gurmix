"""Admin router (basic-auth) — skeleton that works and extends.

Все эндпоинты под /api/v1/admin, защищены basic-auth (require_admin).
  modules           — GET / POST status
  quota config      — GET / PUT
  documents/chunks/pipeline — заглушки 501 (корректная форма ответа, фаза 2)
  distributors      — рабочий CRUD (SQLite)
  journal           — GET (порт query_logs)
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.admin.deps import require_admin
from app.api.distributors_models import Distributor
from app.api.journal_models import QueryLog
from app.core.database import get_db
from app.limits import store as quota_store
from app.modules.registry import MODULES, MODULES_BY_ID, public_dict
from app.schemas import (
    DistributorCreate,
    DistributorResponse,
    DistributorUpdate,
    QuotaConfig,
    QuotaConfigUpdate,
)

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])

# In-memory status overrides (фаза 2: persist в БД/конфиг). The registry stays
# the source of truth; this lets the admin flip status without code edits.
_status_overrides: dict[str, str] = {}


# ── Modules ────────────────────────────────────────────────────────────────
def _module_admin_dict(m) -> dict:
    d = public_dict(m)
    d["status"] = _status_overrides.get(m.id, d["status"])
    return d


@router.get("/modules")
async def admin_list_modules() -> dict:
    return {"modules": [_module_admin_dict(m) for m in sorted(MODULES, key=lambda x: x.order)]}


@router.post("/modules")
async def admin_set_module_status(payload: dict) -> dict:
    """Set a module's status. Body: {module_id, status: 'active'|'locked'}."""
    module_id = payload.get("module_id")
    new_status = payload.get("status")
    if module_id not in MODULES_BY_ID:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module_id}")
    if new_status not in ("active", "locked"):
        raise HTTPException(status_code=422, detail="status must be 'active' or 'locked'")
    _status_overrides[module_id] = new_status
    return _module_admin_dict(MODULES_BY_ID[module_id])


# ── Quota config ─────────────────────────────────────────────────────────────
@router.get("/quota/config", response_model=QuotaConfig)
async def admin_get_quota_config() -> QuotaConfig:
    cfg = quota_store.get_config()
    return QuotaConfig(**cfg)


@router.put("/quota/config", response_model=QuotaConfig)
async def admin_set_quota_config(payload: QuotaConfigUpdate) -> QuotaConfig:
    try:
        cfg = quota_store.set_config(limit=payload.limit, period=payload.period)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return QuotaConfig(**cfg)


# ── Documents / RAG (заглушки 501, форма ответа корректна — фаза 2) ──────────
@router.get("/documents")
async def admin_list_documents() -> dict:
    return {"documents": [], "total": 0, "status": "not_implemented"}


@router.post("/documents/upload", status_code=501)
async def admin_upload_document() -> dict:
    raise HTTPException(
        status_code=501,
        detail="Ингестия документов — фаза 2 (RAG-корпус ещё не подключён).",
    )


@router.get("/chunks")
async def admin_list_chunks() -> dict:
    return {"chunks": [], "total": 0, "status": "not_implemented"}


@router.post("/pipeline/rebuild-index", status_code=501)
async def admin_rebuild_index() -> dict:
    raise HTTPException(
        status_code=501,
        detail="Пересборка индекса — фаза 2 (E5 + индекс ещё не подключены).",
    )


# ── Distributors CRUD (рабочий, SQLite) ──────────────────────────────────────
def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def _dist_response(d: Distributor) -> DistributorResponse:
    return DistributorResponse(
        id=d.id,
        region=d.region,
        name=d.name,
        phone=d.phone,
        email=d.email,
        address=d.address,
        note=d.note,
        created_at=_iso(d.created_at),
        updated_at=_iso(d.updated_at),
    )


@router.get("/distributors", response_model=list[DistributorResponse])
async def admin_list_distributors(
    region: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[DistributorResponse]:
    q = select(Distributor)
    if region:
        q = q.where(func.lower(Distributor.region).contains(region.lower()))
    rows = db.execute(q.order_by(Distributor.region, Distributor.name)).scalars().all()
    return [_dist_response(d) for d in rows]


@router.post("/distributors", response_model=DistributorResponse, status_code=201)
async def admin_create_distributor(
    payload: DistributorCreate,
    db: Session = Depends(get_db),
) -> DistributorResponse:
    d = Distributor(**payload.model_dump())
    db.add(d)
    db.flush()
    db.refresh(d)
    return _dist_response(d)


@router.put("/distributors/{dist_id}", response_model=DistributorResponse)
async def admin_update_distributor(
    dist_id: int,
    payload: DistributorUpdate,
    db: Session = Depends(get_db),
) -> DistributorResponse:
    d = db.get(Distributor, dist_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Distributor not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.flush()
    db.refresh(d)
    return _dist_response(d)


@router.delete("/distributors/{dist_id}")
async def admin_delete_distributor(
    dist_id: int,
    db: Session = Depends(get_db),
) -> dict:
    d = db.get(Distributor, dist_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Distributor not found")
    db.delete(d)
    return {"ok": True}


# ── Journal (порт query_logs) ────────────────────────────────────────────────
@router.get("/journal")
async def admin_journal(
    module_id: str | None = Query(None),
    feedback: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    q = select(QueryLog)
    if module_id:
        q = q.where(QueryLog.module_id == module_id)
    if feedback == "none":
        q = q.where(QueryLog.feedback.is_(None))
    elif feedback:
        q = q.where(QueryLog.feedback == feedback)
    if search:
        q = q.where(func.lower(QueryLog.question).contains(search.lower()))

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    offset = (page - 1) * per_page
    rows = db.execute(
        q.order_by(desc(QueryLog.ts)).offset(offset).limit(per_page)
    ).scalars().all()

    items = [
        {
            "id": r.id,
            "ts": _iso(r.ts),
            "session_id": r.session_id,
            "module_id": r.module_id,
            "question": r.question,
            "answer": r.answer,
            "query_type": r.query_type,
            "latency_ms": r.latency_ms,
            "t_answer_model": r.t_answer_model,
            "top_score": r.top_score,
            "chunks_used": r.chunks_used,
            "feedback": r.feedback,
            "feedback_note": r.feedback_note,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "per_page": per_page}
