"""Public modules router: GET /api/v1/modules."""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.registry import public_list

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.get("")
async def list_modules() -> dict:
    """Публичные карточки 8 модулей-экспертов (без системных промптов)."""
    return {"modules": public_list()}
