"""Pydantic request/response schemas for «Нейро-шеф Гурмикс»."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Chat ──────────────────────────────────────────────────────────────────
class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    module_id: str
    message: str
    session_id: str
    history: list[HistoryTurn] = Field(default_factory=list)


class ChatFeedbackRequest(BaseModel):
    log_id: int
    feedback: Literal["good", "bad"]
    note: str | None = None


# ── Quota ─────────────────────────────────────────────────────────────────
class QuotaState(BaseModel):
    used: int
    limit: int
    remaining: int
    period: Literal["day", "week", "month"]
    reset_at: str
    blocked: bool


class QuotaConfig(BaseModel):
    limit: int = Field(ge=0)
    period: Literal["day", "week", "month"]


class QuotaConfigUpdate(BaseModel):
    limit: int | None = Field(default=None, ge=0)
    period: Literal["day", "week", "month"] | None = None


# ── Distributors (module 8) ────────────────────────────────────────────────
class DistributorBase(BaseModel):
    region: str
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    note: str | None = None


class DistributorCreate(DistributorBase):
    pass


class DistributorUpdate(BaseModel):
    region: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    note: str | None = None


class DistributorResponse(DistributorBase):
    id: int
    created_at: str
    updated_at: str
    model_config = ConfigDict(from_attributes=True)
