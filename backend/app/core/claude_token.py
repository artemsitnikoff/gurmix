"""Claude OAuth token auto-refresh (sync + async).

Tokens stored in data/.claude_token.json. Refresh tokens are single-use; writes
are atomic to prevent corruption.

This is OPTIONAL for local runs: if no token file and no env vars exist, the
functions log and no-op — the code relies on an already-logged-in `claude` CLI.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

TOKEN_FILE = Path("data/.claude_token.json")
TOKEN_URL = "https://api.anthropic.com/v1/oauth/token"
CLAUDE_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
REFRESH_BUFFER_MS = 600_000  # refresh 10 min before expiry

_sync_lock = threading.Lock()
_async_lock: asyncio.Lock | None = None


def _get_async_lock() -> asyncio.Lock:
    global _async_lock
    if _async_lock is None:
        _async_lock = asyncio.Lock()
    return _async_lock


def _load() -> dict:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save(data: dict) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = TOKEN_FILE.with_suffix(TOKEN_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, TOKEN_FILE)


def init_token_file() -> None:
    """Seed token file from env vars on first start (if not already present)."""
    if TOKEN_FILE.exists():
        data = _load()
        if data.get("refresh_token"):
            logger.info("Claude token file exists with refresh token")
            return

    access_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    refresh_token = os.environ.get("CLAUDE_REFRESH_TOKEN", "")

    if not refresh_token:
        if access_token:
            logger.warning(
                "CLAUDE_CODE_OAUTH_TOKEN set but no CLAUDE_REFRESH_TOKEN — "
                "token will not auto-refresh"
            )
        else:
            logger.info(
                "No Claude OAuth tokens in env — relying on an already "
                "logged-in `claude` CLI."
            )
        return

    _save({"access_token": access_token, "refresh_token": refresh_token, "expires_at": 0})
    logger.info("Claude token file initialized from env vars")


def _do_refresh(data: dict) -> dict | None:
    """Perform HTTP refresh, return new token data or None on failure."""
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        logger.debug("No refresh token available")
        return None

    # Import httpx lazily so the module imports cleanly even if httpx is absent.
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed — cannot refresh Claude token")
        return None

    logger.info("Refreshing Claude OAuth token...")
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": CLAUDE_OAUTH_CLIENT_ID,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            result = resp.json()

        now_ms = time.time() * 1000
        expires_in = result.get("expires_in", 28800)
        new_data = {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "expires_at": now_ms + expires_in * 1000,
        }
        _save(new_data)
        logger.info("Claude token refreshed, expires in %d hours", expires_in // 3600)
        return new_data
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to refresh Claude token: %s", e)
        return None


def ensure_fresh_token_sync() -> None:
    """Refresh token if needed. Thread-safe, blocking. No-op if no token file."""
    with _sync_lock:
        data = _load()
        if not data:
            return  # nothing to refresh — rely on logged-in CLI
        now_ms = time.time() * 1000

        if data.get("expires_at", 0) > now_ms + REFRESH_BUFFER_MS:
            if data.get("access_token"):
                os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = data["access_token"]
            return

        new_data = _do_refresh(data)
        if new_data:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = new_data["access_token"]
        elif data.get("access_token"):
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = data["access_token"]


async def ensure_fresh_token() -> None:
    """Async variant — use from async context. No-op if no token file."""
    async with _get_async_lock():
        data = _load()
        if not data:
            return
        now_ms = time.time() * 1000

        if data.get("expires_at", 0) > now_ms + REFRESH_BUFFER_MS:
            if data.get("access_token"):
                os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = data["access_token"]
            return

        new_data = await asyncio.to_thread(_do_refresh, data)
        if new_data:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = new_data["access_token"]
        elif data.get("access_token"):
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = data["access_token"]
