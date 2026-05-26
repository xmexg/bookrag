from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(slots=True)
class BookPathInfo:
    book_name: str
    chapter_name: str
    rel_path: str
    display_path: str


def _safe_segment(value: str) -> str:
    segment = Path(value).name.strip()
    if not segment or segment in {".", ".."}:
        raise ValueError("非法路径段")
    return segment


def normalize_uploaded_rel_path(raw_filename: str, book_name: str | None = None) -> str:
    raw = (raw_filename or "").replace("\\", "/").strip()
    if not raw:
        raise ValueError("空文件名")

    parts = [part for part in PurePosixPath(raw).parts if part not in {"", "."}]
    if any(part == ".." for part in parts):
        raise ValueError("不允许上传到上级目录")

    if len(parts) == 1:
        file_name = _safe_segment(parts[0])
        folder_name = _safe_segment(book_name) if book_name else Path(file_name).stem
        return str(PurePosixPath(folder_name) / file_name)

    safe_parts = [_safe_segment(part) for part in parts]
    return str(PurePosixPath(*safe_parts))


def derive_book_info(rel_path: str, file_name: str | None = None) -> BookPathInfo:
    normalized = (rel_path or "").replace("\\", "/").strip()
    parts = [part for part in PurePosixPath(normalized).parts if part not in {"", "."}]
    fallback_name = file_name or (parts[-1] if parts else normalized)
    fallback_stem = Path(fallback_name).stem if fallback_name else "未知图书"

    if len(parts) > 1:
        book_name = parts[0]
        chapter_name = Path(parts[-1]).stem or parts[-1]
        display_path = str(PurePosixPath(*parts))
        return BookPathInfo(book_name=book_name, chapter_name=chapter_name, rel_path=display_path, display_path=display_path)

    if len(parts) == 1:
        file_only = parts[0]
        book_name = Path(file_only).stem or fallback_stem
        chapter_name = Path(file_only).stem or file_only
        display_path = file_only
        return BookPathInfo(book_name=book_name, chapter_name=chapter_name, rel_path=display_path, display_path=display_path)

    return BookPathInfo(book_name=fallback_stem, chapter_name=fallback_stem, rel_path=normalized or fallback_stem, display_path=normalized or fallback_stem)
