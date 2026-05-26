from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Iterable


def _load_simple_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        os.environ.setdefault(key, value)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _as_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_path(base_dir: Path, value: str | None, default_relative: str) -> Path:
    raw = (value or default_relative).strip()
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _split_extensions(raw_value: str | None) -> tuple[str, ...]:
    if not raw_value:
        return (".txt", ".md", ".markdown", ".pdf", ".docx")
    items: list[str] = []
    for part in raw_value.replace(";", ",").split(","):
        normalized = part.strip().lower()
        if not normalized:
            continue
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        items.append(normalized)
    return tuple(dict.fromkeys(items))


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or normalized.lower() in {"none", "null", "false"}:
        return None
    return normalized


@dataclass(frozen=True)
class Settings:
    project_root: Path
    books_dir: Path
    sqlite_db_path: Path
    index_path: Path
    api_base: str
    chat_model: str
    embedding_model: str
    reranking_model: str
    token: str
    proxy: str | None
    listen_extensions: tuple[str, ...]
    host: str
    port: int
    recheck_interval: int
    chunk_size: int
    chunk_overlap: int
    top_k: int
    max_context_chunks: int
    history_turns: int
    request_timeout: int
    rerank_enabled: bool
    rebuild_index_on_startup: bool

    @property
    def api_root(self) -> str:
        base = self.api_base.rstrip("/")
        suffixes = ("/chat/completions", "/embeddings", "/rerank")
        for suffix in suffixes:
            if base.endswith(suffix):
                return base[: -len(suffix)]
        return base


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    _load_simple_dotenv(project_root / ".env")

    api_base = os.getenv("apibase", "https://api.siliconflow.cn/v1/chat/completions").strip()
    chat_model = os.getenv("chat_model", "deepseek-ai/DeepSeek-V4-Flash").strip()
    embedding_model = os.getenv("embedding_model", "Qwen/Qwen3-Embedding-8B").strip()
    reranking_model = os.getenv("reranking_model", "Qwen/Qwen3-Reranker-8B").strip()
    token = os.getenv("token", "").strip()
    proxy = _normalize_optional_text(os.getenv("proxy"))
    listen_extensions = _split_extensions(os.getenv("ListeningFileType"))

    return Settings(
        project_root=project_root,
        books_dir=_resolve_path(project_root, os.getenv("ListeningDirectory"), "./books"),
        sqlite_db_path=_resolve_path(project_root, os.getenv("sqlite_db_path"), "./books.db"),
        index_path=_resolve_path(project_root, os.getenv("index_path"), "./rag.faiss"),
        api_base=api_base,
        chat_model=chat_model,
        embedding_model=embedding_model,
        reranking_model=reranking_model,
        token=token,
        proxy=proxy,
        listen_extensions=listen_extensions,
        host=os.getenv("host", "0.0.0.0").strip() or "0.0.0.0",
        port=_as_int(os.getenv("port"), 8092),
        recheck_interval=max(5, _as_int(os.getenv("recheck_interval"), 600)),
        chunk_size=max(200, _as_int(os.getenv("chunk_size"), 1200)),
        chunk_overlap=max(0, _as_int(os.getenv("chunk_overlap"), 200)),
        top_k=max(1, _as_int(os.getenv("top_k"), 6)),
        max_context_chunks=max(1, _as_int(os.getenv("max_context_chunks"), 6)),
        history_turns=max(1, _as_int(os.getenv("history_turns"), 8)),
        request_timeout=max(10, _as_int(os.getenv("request_timeout"), 30)),
        rerank_enabled=_as_bool(os.getenv("rerank_enabled"), True),
        rebuild_index_on_startup=_as_bool(os.getenv("rebuild_index_on_startup"), True),
    )


def ensure_directories(paths: Iterable[Path]) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
