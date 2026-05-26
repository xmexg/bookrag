from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from .models import ChunkRecord, DocumentRecord, SearchResult, now_iso


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            rel_path TEXT NOT NULL,
            abs_path TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            file_size INTEGER NOT NULL,
            mtime REAL NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS document_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            rel_path TEXT NOT NULL,
            seen_at TEXT NOT NULL,
            UNIQUE(document_id, file_name, rel_path),
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(is_active);

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
        with self.connection() as conn:
            conn.executescript(schema)

    def upsert_document(
        self,
        *,
        file_name: str,
        rel_path: str,
        abs_path: str,
        content_hash: str,
        file_size: int,
        mtime: float,
        is_active: bool = True,
    ) -> DocumentRecord:
        timestamp = now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (file_name, rel_path, abs_path, content_hash, file_size, mtime, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    file_name = excluded.file_name,
                    rel_path = excluded.rel_path,
                    abs_path = excluded.abs_path,
                    file_size = excluded.file_size,
                    mtime = excluded.mtime,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at
                """,
                (file_name, rel_path, abs_path, content_hash, file_size, mtime, 1 if is_active else 0, timestamp, timestamp),
            )
        document = self.get_document_by_hash(content_hash)
        if document is None:
            raise RuntimeError("文档写入后未能读取")
        return document

    def touch_document_alias(self, document_id: int, file_name: str, rel_path: str) -> None:
        timestamp = now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO document_aliases (document_id, file_name, rel_path, seen_at)
                VALUES (?, ?, ?, ?)
                """,
                (document_id, file_name, rel_path, timestamp),
            )

    def get_document_by_hash(self, content_hash: str) -> DocumentRecord | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE content_hash = ?", (content_hash,)).fetchone()
        return self._row_to_document(row) if row else None

    def get_document_by_path(self, rel_path: str) -> DocumentRecord | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE rel_path = ? ORDER BY updated_at DESC LIMIT 1", (rel_path,)).fetchone()
        return self._row_to_document(row) if row else None

    def list_active_documents(self) -> list[DocumentRecord]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM documents WHERE is_active = 1 ORDER BY updated_at DESC").fetchall()
        return [self._row_to_document(row) for row in rows]

    def list_documents(self) -> list[DocumentRecord]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY updated_at DESC").fetchall()
        return [self._row_to_document(row) for row in rows]

    def mark_document_inactive(self, document_id: int) -> None:
        timestamp = now_iso()
        with self.connection() as conn:
            conn.execute("UPDATE documents SET is_active = 0, updated_at = ? WHERE id = ?", (timestamp, document_id))
            conn.execute("UPDATE chunks SET is_active = 0 WHERE document_id = ?", (document_id,))

    def mark_document_active(self, document_id: int) -> None:
        timestamp = now_iso()
        with self.connection() as conn:
            conn.execute("UPDATE documents SET is_active = 1, updated_at = ? WHERE id = ?", (timestamp, document_id))
            conn.execute("UPDATE chunks SET is_active = 1 WHERE document_id = ?", (document_id,))

    def replace_document_chunks(self, document_id: int, chunks: Sequence[tuple[int, str, int, int, bytes]]) -> list[int]:
        timestamp = now_iso()
        with self.connection() as conn:
            conn.execute("UPDATE chunks SET is_active = 0 WHERE document_id = ?", (document_id,))
            inserted_ids: list[int] = []
            for chunk_index, content, start_char, end_char, embedding in chunks:
                cursor = conn.execute(
                    """
                    INSERT INTO chunks (document_id, chunk_index, content, start_char, end_char, embedding, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (document_id, chunk_index, content, start_char, end_char, embedding, timestamp),
                )
                inserted_ids.append(int(cursor.lastrowid))
        return inserted_ids

    def insert_chunks(self, document_id: int, chunks: Sequence[tuple[int, str, int, int, bytes]]) -> list[int]:
        timestamp = now_iso()
        with self.connection() as conn:
            inserted_ids: list[int] = []
            for chunk_index, content, start_char, end_char, embedding in chunks:
                cursor = conn.execute(
                    """
                    INSERT INTO chunks (document_id, chunk_index, content, start_char, end_char, embedding, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (document_id, chunk_index, content, start_char, end_char, embedding, timestamp),
                )
                inserted_ids.append(int(cursor.lastrowid))
        return inserted_ids

    def get_active_chunks(self) -> list[ChunkRecord]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM chunks WHERE is_active = 1 ORDER BY id ASC").fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def get_chunks_by_document(self, document_id: int, include_inactive: bool = True) -> list[ChunkRecord]:
        query = "SELECT * FROM chunks WHERE document_id = ? ORDER BY id ASC"
        if not include_inactive:
            query = "SELECT * FROM chunks WHERE document_id = ? AND is_active = 1 ORDER BY id ASC"
        with self.connection() as conn:
            rows = conn.execute(query, (document_id,)).fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def get_chunks_by_ids(self, chunk_ids: Sequence[int]) -> list[ChunkRecord]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        with self.connection() as conn:
            rows = conn.execute(f"SELECT * FROM chunks WHERE id IN ({placeholders})", tuple(chunk_ids)).fetchall()
        chunks = [self._row_to_chunk(row) for row in rows]
        chunk_map = {chunk.id: chunk for chunk in chunks}
        return [chunk_map[chunk_id] for chunk_id in chunk_ids if chunk_id in chunk_map]

    def get_search_result(self, chunk_id: int, score: float) -> SearchResult | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT c.*, d.file_name, d.rel_path, d.abs_path, d.content_hash
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.id = ? AND c.is_active = 1 AND d.is_active = 1
                """,
                (chunk_id,),
            ).fetchone()
        if row is None:
            return None
        return SearchResult(
            chunk_id=int(row["id"]),
            document_id=int(row["document_id"]),
            file_name=str(row["file_name"]),
            rel_path=str(row["rel_path"]),
            abs_path=str(row["abs_path"]),
            content_hash=str(row["content_hash"]),
            chunk_index=int(row["chunk_index"]),
            content=str(row["content"]),
            score=float(score),
            start_char=int(row["start_char"]),
            end_char=int(row["end_char"]),
        )

    def get_document(self, document_id: int) -> DocumentRecord | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._row_to_document(row) if row else None

    def ensure_conversation(self, conversation_id: str, title: str = "图书对话") -> None:
        timestamp = now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title = excluded.title, updated_at = excluded.updated_at
                """,
                (conversation_id, title, timestamp, timestamp),
            )

    def append_message(self, conversation_id: str, role: str, content: str, sources_json: str | None = None) -> None:
        timestamp = now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, sources_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, sources_json, timestamp),
            )
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (timestamp, conversation_id))

    def get_conversation_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, str | None]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT role, content, sources_json, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()
        result = [dict(row) for row in rows]
        return list(reversed(result))

    def list_conversations(self) -> list[dict[str, str]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def set_meta(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO meta (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def _row_to_document(self, row: sqlite3.Row | None) -> DocumentRecord:
        if row is None:
            raise ValueError("row is None")
        return DocumentRecord(
            id=int(row["id"]),
            file_name=str(row["file_name"]),
            rel_path=str(row["rel_path"]),
            abs_path=str(row["abs_path"]),
            content_hash=str(row["content_hash"]),
            file_size=int(row["file_size"]),
            mtime=float(row["mtime"]),
            is_active=bool(row["is_active"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _row_to_chunk(self, row: sqlite3.Row | None) -> ChunkRecord:
        if row is None:
            raise ValueError("row is None")
        return ChunkRecord(
            id=int(row["id"]),
            document_id=int(row["document_id"]),
            chunk_index=int(row["chunk_index"]),
            content=str(row["content"]),
            start_char=int(row["start_char"]),
            end_char=int(row["end_char"]),
            embedding=bytes(row["embedding"]),
            is_active=bool(row["is_active"]),
            created_at=str(row["created_at"]),
        )
