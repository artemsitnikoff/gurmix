"""Admin basic-auth dependency (порт teplodar basic-auth)."""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

_security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Validate HTTP Basic credentials against ADMIN_USER / ADMIN_PASS.

    Refuses all access when ADMIN_PASS is empty — no hard-coded fallback.
    """
    if not settings.admin_pass:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin is disabled: ADMIN_PASS is not configured.",
        )
    ok_user = secrets.compare_digest(credentials.username, settings.admin_user)
    ok_pass = secrets.compare_digest(credentials.password, settings.admin_pass)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
