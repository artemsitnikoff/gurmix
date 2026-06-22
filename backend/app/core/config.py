"""Configuration settings for «Нейро-шеф Гурмикс» backend.

All values load from environment / .env via pydantic-settings. Secrets
(OAuth tokens, admin password) must come from the environment — never hardcode.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_path: Path = Field(default=Path("base/gurmix.db"))

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Claude CLI (Pro subscription via OAuth — NOT the paid API) ────────
    # Final-answer model. Default = Opus 4.8 (best quality on Russian).
    claude_model: str = Field(default="claude-opus-4-8")
    # Intent extraction / reformulation. Default = Opus 4.8 for consistency;
    # set to Haiku (claude-haiku-4-5) for lower latency on the intent phase.
    claude_intent_model: str = Field(default="claude-opus-4-8")
    # LLM-as-judge (асессор полезности ответа). Бежит асинхронно в фоне после
    # ответа — Haiku ради скорости и низкой нагрузки на Pro-аккаунт.
    claude_judge_model: str = Field(default="claude-haiku-4-5-20251001")
    # Path to the `claude` CLI binary (already logged in to the Pro account).
    claude_cli_path: str = Field(default="claude")
    # Cross-process upper bound on concurrent Claude CLI subprocesses — a
    # file-lock slot pool protects the Pro OAuth account from a 429-storm.
    claude_cli_max_concurrent: int = Field(default=4)
    claude_cli_slots_dir: Path = Field(default=Path("/tmp/gurmix_claude_slots"))
    # Hard timeout (seconds) for a single Claude CLI subprocess.
    claude_cli_timeout: int = Field(default=120)

    # ── Claude OAuth token (optional — auto-refresh from data/.claude_token.json)
    claude_code_oauth_token: str = Field(default="")
    claude_refresh_token: str = Field(default="")

    # ── Quota / limits (подстраховка Pro-аккаунта) ────────────────────────
    quota_limit: int = Field(default=30)
    # Reset period: "day" | "week" | "month".
    quota_period: str = Field(default="day")

    # ── Admin basic-auth ──────────────────────────────────────────────────
    admin_user: str = Field(default="admin")
    admin_pass: str = Field(default="")

    # ── CORS (dev) ────────────────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
