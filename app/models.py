from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class LoadedDocument:
    text: str
    source_type: str
    page_count: int | None = None


@dataclass(slots=True)
class SplitChunk:
    chunk_index: int
    content: str
    start_char: int
    end_char: int


@dataclass(slots=True)
class DocumentRecord:
    id: int
    file_name: str
    rel_path: str
    abs_path: str
    content_hash: str
    file_size: int
    mtime: float
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ChunkRecord:
    id: int
    document_id: int
    chunk_index: int
    content: str
    start_char: int
    end_char: int
    embedding: bytes
    is_active: bool
    created_at: str


@dataclass(slots=True)
class SearchResult:
    chunk_id: int
    document_id: int
    file_name: str
    rel_path: str
    abs_path: str
    content_hash: str
    chunk_index: int
    content: str
    score: float
    start_char: int
    end_char: int


@dataclass(slots=True)
class SourceCitation:
    source_index: int
    file_name: str
    rel_path: str
    book_name: str
    chapter_name: str
    chunk_index: int
    score: float
    excerpt: str
    content_hash: str


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return obj
