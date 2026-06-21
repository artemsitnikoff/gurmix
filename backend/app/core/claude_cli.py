"""Cross-process Claude CLI concurrency limiter + subprocess invocation.

The bot/admin/eval workers all call `claude --print` subprocesses against the
same Pro OAuth account. Nothing coordinates across processes by default, so a
traffic spike fans the total concurrent CLI count out and the Pro account
starts 429-ing.

Solution: a slot pool implemented as N lock files. Each CLI call wraps its
subprocess in `with claude_cli_slot():`, which polls all N slots with
`fcntl.flock(LOCK_EX | LOCK_NB)` until one succeeds. The OS releases the flock
automatically when the holding fd is closed (or the process dies), so crashed
processes never leak slots.

If the slots directory cannot be created (read-only FS, perms), we log loudly
and yield without rate-limiting rather than crash — the Claude CLI itself will
still surface a 429, which is preferable to taking the whole app down.

This module must import cleanly even when the `claude` CLI is absent or not
authenticated; missing-binary / auth failures surface only at call time as a
clean RuntimeError, never as an ImportError.
"""
from __future__ import annotations

import fcntl
import logging
import os
import subprocess
import tempfile
import time
from contextlib import contextmanager
from typing import Iterator

from .config import settings

logger = logging.getLogger(__name__)

# How long to back off between full passes over the slot pool.
_POLL_INTERVAL_SEC = 0.1


@contextmanager
def claude_cli_slot() -> Iterator[None]:
    """Acquire one of N global Claude CLI slots, then yield it.

    Polls all N slots non-blockingly each iteration so a free slot is picked up
    immediately instead of waiting FIFO on slot_0. Pure stdlib (`fcntl.flock`),
    POSIX-only (Linux + macOS). Slot released on context-manager exit OR process
    death.
    """
    slots_dir = settings.claude_cli_slots_dir
    cap = max(1, settings.claude_cli_max_concurrent)

    try:
        slots_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(
            "Claude CLI slot dir %s unavailable (%s) — running uncapped",
            slots_dir, e,
        )
        yield
        return

    waited_first = False
    while True:
        any_opened = False
        for i in range(cap):
            slot_path = slots_dir / f"slot_{i}"
            try:
                f = open(slot_path, "a")
            except OSError as e:
                logger.warning("Cannot open slot file %s (%s) — skipping", slot_path, e)
                continue
            any_opened = True
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                f.close()
                continue
            # Got it.
            try:
                yield
            finally:
                f.close()  # closing the fd releases the flock
            return

        if not any_opened:
            logger.error(
                "Claude CLI: cannot open any slot file in %s — running uncapped",
                slots_dir,
            )
            yield
            return

        if not waited_first:
            logger.info("Claude CLI: all %d slots busy, polling…", cap)
            waited_first = True
        time.sleep(_POLL_INTERVAL_SEC)


class ClaudeCLIError(RuntimeError):
    """Raised when the Claude CLI subprocess fails or is unavailable."""


def call_cli(prompt: str, model: str = "") -> str:
    """Call the Claude CLI subprocess. Uses the Pro subscription via OAuth.

    `model` is forwarded as `--model <...>`. Empty string = CLI default.

    Degrades gracefully: if the `claude` binary is missing or not authenticated,
    raises a clean ClaudeCLIError instead of crashing the caller. Always runs in
    a fresh TemporaryDirectory as cwd so no session/state leaks between calls.
    """
    # Best-effort OAuth refresh; never fatal if the token file is absent.
    try:
        from .claude_token import ensure_fresh_token_sync

        ensure_fresh_token_sync()
    except Exception as e:  # noqa: BLE001 — token refresh is optional
        logger.debug("Claude token refresh skipped (%s)", e)

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)

    args = [
        settings.claude_cli_path,
        "--print",
        "--output-format", "text",
        "--no-session-persistence",
    ]
    if model:
        args += ["--model", model]

    t_sub = time.monotonic()
    try:
        with claude_cli_slot(), tempfile.TemporaryDirectory(prefix="gurmix_claude_") as cwd:
            result = subprocess.run(
                args,
                input=prompt.encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=cwd,
                timeout=settings.claude_cli_timeout,
            )
    except FileNotFoundError as e:
        raise ClaudeCLIError(
            f"Claude CLI binary '{settings.claude_cli_path}' not found — "
            "install it and log in to the Pro account."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise ClaudeCLIError(
            f"claude CLI timed out after {settings.claude_cli_timeout}s"
        ) from e

    logger.info(
        "[claude-cli] model=%s subprocess=%.2fs rc=%d",
        model or "(default)", time.monotonic() - t_sub, result.returncode,
    )

    if result.returncode != 0:
        err = (result.stderr.decode().strip() or result.stdout.decode().strip())[:300]
        raise ClaudeCLIError(f"claude CLI (code {result.returncode}): {err}")

    text = result.stdout.decode().strip()
    if not text:
        raise ClaudeCLIError("claude CLI returned empty response")
    return text
