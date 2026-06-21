"""Quota state computation and enforcement.

Pure functions over (session_id, ip): compute the current window, look up /
create the counter row, expose `get_quota` and `increment`. The current quota
config (limit + period) lives in module-level mutable state so the admin
`PUT /admin/quota/config` can change it at runtime; defaults come from Settings.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.limits.models import UsageCounter

logger = logging.getLogger(__name__)

_VALID_PERIODS = ("day", "week", "month")

# Runtime-mutable quota config (admin can change via PUT /admin/quota/config).
_quota_limit: int = settings.quota_limit
_quota_period: str = settings.quota_period if settings.quota_period in _VALID_PERIODS else "day"


def get_config() -> dict:
    return {"limit": _quota_limit, "period": _quota_period}


def set_config(limit: int | None = None, period: str | None = None) -> dict:
    """Update runtime quota config. Returns the new config."""
    global _quota_limit, _quota_period
    if limit is not None:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        _quota_limit = int(limit)
    if period is not None:
        if period not in _VALID_PERIODS:
            raise ValueError(f"period must be one of {_VALID_PERIODS}")
        _quota_period = period
    return get_config()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_start(d: date, period: str) -> date:
    if period == "day":
        return d
    if period == "week":
        return d - timedelta(days=d.weekday())  # Monday
    if period == "month":
        return d.replace(day=1)
    return d


def _next_period_start(start: date, period: str) -> date:
    if period == "day":
        return start + timedelta(days=1)
    if period == "week":
        return start + timedelta(days=7)
    if period == "month":
        if start.month == 12:
            return start.replace(year=start.year + 1, month=1, day=1)
        return start.replace(month=start.month + 1, day=1)
    return start + timedelta(days=1)


def _window() -> tuple[str, str]:
    """Return (period_start_iso, reset_at_iso) for the current window."""
    today = _now().date()
    start = _period_start(today, _quota_period)
    reset = _next_period_start(start, _quota_period)
    reset_dt = datetime(reset.year, reset.month, reset.day, tzinfo=timezone.utc)
    return start.isoformat(), reset_dt.isoformat()


def _quota_state(used: int, reset_at: str) -> dict:
    remaining = max(0, _quota_limit - used)
    return {
        "used": used,
        "limit": _quota_limit,
        "remaining": remaining,
        "period": _quota_period,
        "reset_at": reset_at,
        "blocked": remaining <= 0,
    }


def get_quota(db: Session, session_id: str, ip: str) -> dict:
    """Return the current QuotaState dict for (session_id, ip) without mutating."""
    period_start, reset_at = _window()
    row = db.execute(
        select(UsageCounter).where(
            UsageCounter.session_id == session_id,
            UsageCounter.ip == ip,
            UsageCounter.period_start == period_start,
        )
    ).scalar_one_or_none()
    used = row.count if row else 0
    return _quota_state(used, reset_at)


def increment(db: Session, session_id: str, ip: str, est_tokens: int = 0) -> dict:
    """Increment the counter for the current window; return new QuotaState.

    Creates the row if absent. Caller commits the session (or relies on
    get_db's auto-commit).
    """
    period_start, reset_at = _window()
    row = db.execute(
        select(UsageCounter).where(
            UsageCounter.session_id == session_id,
            UsageCounter.ip == ip,
            UsageCounter.period_start == period_start,
        )
    ).scalar_one_or_none()

    if row is None:
        row = UsageCounter(
            session_id=session_id,
            ip=ip,
            period_start=period_start,
            count=1,
            est_tokens=est_tokens,
        )
        db.add(row)
    else:
        row.count += 1
        row.est_tokens += est_tokens

    db.flush()
    return _quota_state(row.count, reset_at)
