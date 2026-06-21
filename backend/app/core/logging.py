"""Logging configuration for the «Нейро-шеф Гурмикс» backend."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from .config import settings


def setup_logging() -> None:
    """Configure root logging: console + rotating-ish file handler."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    file_handler = logging.FileHandler(logs_dir / "gurmix.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Quiet down noisy libraries.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
