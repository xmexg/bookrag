from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_path: Path) -> Path:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    if getattr(root_logger, "_rag_logging_configured", False):
        return log_path

    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    root_logger._rag_logging_configured = True  # type: ignore[attr-defined]
    return log_path


def tail_log(log_path: Path, max_lines: int = 100) -> list[str]:
    if not log_path.exists() or max_lines <= 0:
        return []

    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return lines[-max_lines:]
