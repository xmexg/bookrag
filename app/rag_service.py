from __future__ import annotations

import logging
import re
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import json
from datetime import datetime, timedelta, timezone
from collections.abc import Iterator
import threading
import uuid

import numpy as np

from .config import Settings
from .book_paths import derive_book_info
from .loaders import is_supported_file, load_document
from .models import SearchResult, SourceCitation, now_iso
from .siliconflow import SiliconFlowClient
from .storage import SQLiteStore
from .text_splitter import split_text
from .vector_index import VectorIndex


logger = logging.getLogger("rag")


class RAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = SQLiteStore(settings.sqlite_db_path)
        self.vector_index = VectorIndex(settings.index_path)
        self.client = SiliconFlowClient(
            api_root=settings.api_root,
            token=settings.token,
            chat_model=settings.chat_model,
            embedding_model=settings.embedding_model,
            reranking_model=settings.reranking_model,
            proxy=settings.proxy,
            timeout=settings.request_timeout,
        )
        self._lock = threading.RLock()
        self._scanner_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.store.initialize()
        self.vector_index.load()

    def start_background_scanner(self) -> None:
        if self._scanner_thread and self._scanner_thread.is_alive():
            return

        self._stop_event.clear()
        self._scanner_thread = threading.Thread(target=self._scan_loop, name="rag-directory-scanner", daemon=True)
        self._scanner_thread.start()

    def stop_background_scanner(self) -> None:
        self._stop_event.set()
        if self._scanner_thread and self._scanner_thread.is_alive():
            self._scanner_thread.join(timeout=5)

    def initial_sync(self) -> dict[str, int]:
        with self._lock:
            scan_stats = self.scan_and_update()
            if self.settings.rebuild_index_on_startup or not self.vector_index.has_index():
                rebuild_stats = self.rebuild_index()
                scan_stats.update(rebuild_stats)
            return scan_stats

    def scan_and_update(self) -> dict[str, int]:
        with self._lock:
            self.settings.books_dir.mkdir(parents=True, exist_ok=True)
            current_files = self._discover_files()
            logger.info("scan started: books_dir=%s files=%s", self.settings.books_dir, len(current_files))
            existing_active_docs = {doc.rel_path: doc for doc in self.store.list_active_documents()}
            active_docs_by_hash = {doc.content_hash: doc for doc in self.store.list_documents()}
            seen_document_ids: set[int] = set()
            added_chunk_ids: list[int] = []
            removed_chunk_ids: list[int] = []
            new_documents = 0
            updated_documents = 0
            deleted_documents = 0

            for file_path in current_files:
                rel_path = str(file_path.relative_to(self.settings.books_dir).as_posix())
                file_name = file_path.name
                file_bytes = file_path.read_bytes()
                content_hash = sha256(file_bytes).hexdigest()
                file_size = len(file_bytes)
                mtime = file_path.stat().st_mtime

                existing_by_hash = active_docs_by_hash.get(content_hash)
                existing_by_path = existing_active_docs.get(rel_path)

                if existing_by_hash is not None:
                    changed_name = existing_by_hash.file_name != file_name
                    changed_path = existing_by_hash.rel_path != rel_path
                    if changed_name or changed_path:
                        self.store.touch_document_alias(existing_by_hash.id, existing_by_hash.file_name, existing_by_hash.rel_path)
                        self.store.upsert_document(
                            file_name=file_name,
                            rel_path=rel_path,
                            abs_path=str(file_path.resolve()),
                            content_hash=content_hash,
                            file_size=file_size,
                            mtime=mtime,
                            is_active=True,
                        )
                        updated_documents += 1
                    else:
                        self.store.upsert_document(
                            file_name=file_name,
                            rel_path=rel_path,
                            abs_path=str(file_path.resolve()),
                            content_hash=content_hash,
                            file_size=file_size,
                            mtime=mtime,
                            is_active=True,
                        )
                    if not existing_by_hash.is_active:
                        self.store.mark_document_active(existing_by_hash.id)
                        self._sync_existing_document_chunks_to_index(existing_by_hash.id)
                    seen_document_ids.add(existing_by_hash.id)
                    continue

                if existing_by_path is not None and existing_by_path.content_hash != content_hash:
                    removed_chunk_ids.extend([chunk.id for chunk in self.store.get_chunks_by_document(existing_by_path.id)])
                    self.store.mark_document_inactive(existing_by_path.id)
                    deleted_documents += 1

                document = self.store.upsert_document(
                    file_name=file_name,
                    rel_path=rel_path,
                    abs_path=str(file_path.resolve()),
                    content_hash=content_hash,
                    file_size=file_size,
                    mtime=mtime,
                    is_active=True,
                )
                seen_document_ids.add(document.id)
                new_documents += 1

                loaded = load_document(file_path)
                chunks = split_text(loaded.text, self.settings.chunk_size, self.settings.chunk_overlap)
                if not chunks:
                    continue
                chunk_payloads = self._embed_chunks([chunk.content for chunk in chunks])
                chunk_records = [
                    (chunk.chunk_index, chunk.content, chunk.start_char, chunk.end_char, embedding)
                    for chunk, embedding in zip(chunks, chunk_payloads)
                ]
                inserted_ids = self.store.insert_chunks(document.id, chunk_records)
                added_chunk_ids.extend(inserted_ids)

            inactive_docs = [doc for doc in self.store.list_active_documents() if doc.id not in seen_document_ids]
            for document in inactive_docs:
                removed_chunk_ids.extend([chunk.id for chunk in self.store.get_chunks_by_document(document.id)])
                self.store.mark_document_inactive(document.id)
                deleted_documents += 1

            if removed_chunk_ids:
                self.vector_index.remove(removed_chunk_ids)
            if added_chunk_ids:
                self._sync_new_chunks_to_index(added_chunk_ids)
            self.vector_index.save()

            stats = {
                "current_files": len(current_files),
                "new_documents": new_documents,
                "updated_documents": updated_documents,
                "deleted_documents": deleted_documents,
                "added_chunks": len(added_chunk_ids),
                "removed_chunks": len(removed_chunk_ids),
            }
            self.store.set_meta("last_scan_at", now_iso())
            self.store.set_meta("last_scan_stats", json.dumps(stats, ensure_ascii=False))
            logger.info("scan finished: %s", stats)

            return stats

    def rebuild_index(self) -> dict[str, int]:
        with self._lock:
            active_chunks = self.store.get_active_chunks()
            if not active_chunks:
                self.vector_index.rebuild([], [])
                return {"documents": len(self.store.list_active_documents()), "chunks": 0}

            chunk_ids = [chunk.id for chunk in active_chunks]
            embeddings = [chunk.embedding for chunk in active_chunks]
            self.vector_index.rebuild(chunk_ids, embeddings)
            return {"documents": len(self.store.list_active_documents()), "chunks": len(active_chunks)}

    def chat_stream(self, question: str, conversation_id: str | None = None) -> tuple[str, Iterator[str]]:
        with self._lock:
            if conversation_id is None:
                conversation_id = str(uuid.uuid4())
            self.store.ensure_conversation(conversation_id)

            history = self.store.get_conversation_messages(conversation_id, limit=self.settings.history_turns * 2)
            retrieved = self.retrieve(question, top_k=self.settings.top_k)
            messages, citations = self._build_chat_payload(question, history, retrieved)

        def stream() -> Iterator[str]:
            answer_parts: list[str] = []
            yield self._sse_event("meta", {"conversation_id": conversation_id, "stream": True})
            try:
                for chunk in self.client.chat_stream(messages):
                    if not chunk:
                        continue
                    answer_parts.append(chunk)
                    yield self._sse_event("token", {"content": chunk})
            except Exception:
                logger.warning("stream chat failed, falling back to local answer", exc_info=True)
                fallback_answer = self._local_fallback_answer(question, retrieved, citations)
                if answer_parts:
                    notice = "\n\n[流式模型响应中断，以下为本地回退结果]\n"
                    answer_parts.append(notice)
                    yield self._sse_event("token", {"content": notice})
                else:
                    fallback_answer = fallback_answer or "当前模型暂不可用，且没有检索到足够的本地依据。请稍后重试。"
                for chunk in self._chunk_text(fallback_answer, 24):
                    answer_parts.append(chunk)
                    yield self._sse_event("token", {"content": chunk})

            answer = "".join(answer_parts)
            self.store.append_message(
                conversation_id,
                "user",
                question,
            )
            self.store.append_message(
                conversation_id,
                "assistant",
                answer,
                sources_json=json.dumps([asdict(citation) for citation in citations], ensure_ascii=False),
            )
            logger.info("chat completed: conversation_id=%s sources=%s", conversation_id, len(citations))
            yield self._sse_event(
                "done",
                {
                    "conversation_id": conversation_id,
                    "answer": answer,
                    "sources": [asdict(citation) for citation in citations],
                    "source_count": len(citations),
                },
            )

        return conversation_id, stream()

    def chat(self, question: str, conversation_id: str | None = None) -> dict:
        with self._lock:
            if conversation_id is None:
                conversation_id = str(uuid.uuid4())
            self.store.ensure_conversation(conversation_id)

            history = self.store.get_conversation_messages(conversation_id, limit=self.settings.history_turns * 2)
            retrieved = self.retrieve(question, top_k=self.settings.top_k)
            answer, citations = self._answer_with_sources(question, history, retrieved)

            self.store.append_message(conversation_id, "user", question)
            self.store.append_message(conversation_id, "assistant", answer, sources_json=json.dumps([asdict(citation) for citation in citations], ensure_ascii=False))
            logger.info("chat completed: conversation_id=%s sources=%s", conversation_id, len(citations))

            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [asdict(citation) for citation in citations],
                "source_count": len(citations),
            }

    def retrieve(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        if not self.vector_index.has_index():
            return []

        query_embedding = self._embed_texts([query])[0]
        candidate_count = max(top_k or self.settings.top_k, self.settings.top_k * 3)
        raw_results = self.vector_index.search(query_embedding, candidate_count)
        if not raw_results:
            return []

        candidates = [self.store.get_search_result(chunk_id, score) for chunk_id, score in raw_results]
        results = [candidate for candidate in candidates if candidate is not None]
        if not results:
            return []

        if self.settings.rerank_enabled and self.settings.reranking_model:
            try:
                rerank_order = self.client.rerank(query, [result.content for result in results])
                if rerank_order:
                    ordered: list[SearchResult] = []
                    for index in rerank_order:
                        if 0 <= index < len(results):
                            ordered.append(results[index])
                    if ordered:
                        results = ordered
            except Exception:
                pass

        limited: list[SearchResult] = []
        per_document_count: dict[int, int] = {}
        for result in results:
            current_count = per_document_count.get(result.document_id, 0)
            if current_count >= 2:
                continue
            per_document_count[result.document_id] = current_count + 1
            limited.append(result)
            if top_k is not None and len(limited) >= top_k:
                break
        return limited

    def list_documents(self) -> list[dict]:
        documents: list[dict] = []
        for document in self.store.list_documents():
            info = derive_book_info(document.rel_path, document.file_name)
            documents.append(
                {
                    **asdict(document),
                    "book_name": info.book_name,
                    "chapter_name": info.chapter_name,
                    "display_path": info.display_path,
                }
            )
        return documents

    def list_books(self) -> list[dict]:
        grouped: dict[str, dict] = {}
        for document in self.store.list_documents():
            info = derive_book_info(document.rel_path, document.file_name)
            group = grouped.setdefault(
                info.book_name,
                {
                    "book_name": info.book_name,
                    "book_path": info.book_name,
                    "source_count": 0,
                    "active_source_count": 0,
                    "latest_update_at": document.updated_at,
                    "files": [],
                },
            )
            group["source_count"] += 1
            if document.is_active:
                group["active_source_count"] += 1
            if document.updated_at > group["latest_update_at"]:
                group["latest_update_at"] = document.updated_at
            group["files"].append(
                {
                    "file_name": document.file_name,
                    "chapter_name": info.chapter_name,
                    "rel_path": info.display_path,
                    "content_hash": document.content_hash,
                    "file_size": document.file_size,
                    "mtime": document.mtime,
                    "is_active": document.is_active,
                    "updated_at": document.updated_at,
                }
            )

        books = list(grouped.values())
        for book in books:
            book["files"] = sorted(book["files"], key=lambda item: item["rel_path"])
        books.sort(key=lambda item: item["latest_update_at"], reverse=True)
        return books

    def list_conversations(self) -> list[dict]:
        return self.store.list_conversations()

    def get_dashboard_status(self) -> dict:
        documents = self.store.list_documents()
        active_documents = [document for document in documents if document.is_active]
        latest_update_at = None
        if documents:
            latest_update_at = max(document.updated_at for document in documents)

        last_scan_at = self.store.get_meta("last_scan_at")
        next_scan_at = None
        if last_scan_at:
            try:
                parsed = datetime.fromisoformat(last_scan_at.replace("Z", "+00:00"))
                next_scan_at = (parsed + timedelta(seconds=self.settings.recheck_interval)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            except ValueError:
                next_scan_at = None

        last_scan_stats_raw = self.store.get_meta("last_scan_stats")
        last_scan_stats = None
        if last_scan_stats_raw:
            try:
                last_scan_stats = json.loads(last_scan_stats_raw)
            except json.JSONDecodeError:
                last_scan_stats = None

        return {
            "server_time": now_iso(),
            "books_dir": str(self.settings.books_dir),
            "scan_interval": self.settings.recheck_interval,
            "last_scan_at": last_scan_at,
            "next_scan_at": next_scan_at,
            "latest_update_at": latest_update_at,
            "document_count": len(documents),
            "active_document_count": len(active_documents),
            "book_count": len(self.list_books()),
            "conversation_count": len(self.store.list_conversations()),
            "last_scan_stats": last_scan_stats,
        }

    def get_conversation(self, conversation_id: str) -> dict:
        messages = self.store.get_conversation_messages(conversation_id, limit=200)
        return {"conversation_id": conversation_id, "messages": messages}

    def _scan_loop(self) -> None:
        while not self._stop_event.wait(self.settings.recheck_interval):
            try:
                self.scan_and_update()
            except Exception:
                logger.exception("background scan failed")
                continue

    def _discover_files(self) -> list[Path]:
        if not self.settings.books_dir.exists():
            return []
        files: list[Path] = []
        for path in self.settings.books_dir.rglob("*"):
            if is_supported_file(path, self.settings.listen_extensions):
                files.append(path)
        return sorted(files)

    def _embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        vectors = self.client.embed_texts(texts)
        return [np.asarray(vector, dtype=np.float32) for vector in vectors]

    def _embed_chunks(self, texts: list[str]) -> list[bytes]:
        vectors = self._embed_texts(texts)
        return [vector.astype(np.float32).tobytes() for vector in vectors]

    def _sync_new_chunks_to_index(self, chunk_ids: list[int]) -> None:
        chunks = self.store.get_chunks_by_ids(chunk_ids)
        embeddings = [chunk.embedding for chunk in chunks]
        self.vector_index.add(chunk_ids, embeddings)

    def _sync_existing_document_chunks_to_index(self, document_id: int) -> None:
        chunks = self.store.get_chunks_by_document(document_id)
        active_chunks = [chunk for chunk in chunks if chunk.is_active]
        if not active_chunks:
            return
        self.vector_index.add([chunk.id for chunk in active_chunks], [chunk.embedding for chunk in active_chunks])

    def _answer_with_sources(
        self,
        question: str,
        history: list[dict[str, str | None]],
        retrieved: list[SearchResult],
    ) -> tuple[str, list[SourceCitation]]:
        messages, citations = self._build_chat_payload(question, history, retrieved)
        try:
            answer = self.client.chat(messages)
            return answer, citations
        except Exception:
            logger.warning("chat failed with retrieved sources, falling back to local answer", exc_info=True)
            return self._local_fallback_answer(question, retrieved, citations), citations

    def _build_chat_payload(
        self,
        question: str,
        history: list[dict[str, str | None]],
        retrieved: list[SearchResult],
    ) -> tuple[list[dict[str, str]], list[SourceCitation]]:
        if not retrieved:
            prompt = [
                {"role": "system", "content": "你是一个本地图书知识库助手。当前没有检索到相关内容，请明确说明没有找到依据，不要编造。"},
                *self._trim_history(history),
                {"role": "user", "content": question},
            ]
            return prompt, []

        source_blocks: list[str] = []
        citations: list[SourceCitation] = []
        for index, result in enumerate(retrieved, start=1):
            excerpt = self._trim_excerpt(result.content)
            book_info = derive_book_info(result.rel_path, result.file_name)
            source_blocks.append(
                f"[来源{index}] 书名：{book_info.book_name}\n章节：{book_info.chapter_name}\n文件：{result.rel_path}\n块：第{result.chunk_index + 1}块\n内容：{excerpt}"
            )
            citations.append(
                SourceCitation(
                    source_index=index,
                    file_name=result.file_name,
                    rel_path=result.rel_path,
                    book_name=book_info.book_name,
                    chapter_name=book_info.chapter_name,
                    chunk_index=result.chunk_index,
                    score=result.score,
                    excerpt=excerpt,
                    content_hash=result.content_hash,
                )
            )

        system_prompt = (
            "你是一个严格依赖检索结果的图书RAG助手。"
            "只能根据给定来源回答，不要混合不同文件的内容，不要把一个文件的段落和另一个文件拼接成一个结论。"
            "如果多个文件都相关，请分开说明来源。"
            "回答时要明确注明依据来自哪本书、哪个章节、哪一块。"
            "如果资料不足，直接说明不足并指出缺少什么。"
        )
        source_context = "\n\n".join(source_blocks)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._trim_history(history))
        messages.append(
            {
                "role": "user",
                "content": f"问题：{question}\n\n可用来源如下：\n{source_context}\n\n请给出答案，并在每个关键结论后标注来源编号。",
            }
        )
        return messages, citations

    def _trim_history(self, history: list[dict[str, str | None]]) -> list[dict[str, str]]:
        trimmed: list[dict[str, str]] = []
        for item in history[-self.settings.history_turns * 2 :]:
            role = str(item.get("role") or "")
            content = str(item.get("content") or "")
            if role in {"user", "assistant", "system"} and content:
                trimmed.append({"role": role, "content": content})
        return trimmed

    @staticmethod
    def _trim_excerpt(text: str, limit: int = 650) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    def _local_fallback_answer(self, question: str, retrieved: list[SearchResult], citations: list[SourceCitation]) -> str:
        lines: list[str] = []
        books = self.list_books()
        if books:
            primary_book = books[0]
            lines.append(f"当前知识库中《{primary_book['book_name']}》已入库 {primary_book['source_count']} 个章节文件。")

        chapter_number = self._extract_chapter_number(question)
        if chapter_number is not None:
            chapter_document = self._find_document_by_chapter_number(chapter_number)
            if chapter_document is not None:
                chapter_info = derive_book_info(chapter_document.rel_path, chapter_document.file_name)
                lines.append(f"第{chapter_number}章是《{chapter_info.chapter_name}》。")
                excerpt = self._chapter_excerpt(chapter_document.abs_path)
                if excerpt:
                    lines.append(f"开头节选：{excerpt}")

        if retrieved:
            lines.append("相关检索依据：")
            for index, result in enumerate(retrieved[:3], start=1):
                info = derive_book_info(result.rel_path, result.file_name)
                lines.append(f"{index}. 《{info.book_name}》{info.chapter_name}：{self._trim_excerpt(result.content, 180)}")

        if citations and not retrieved:
            lines.append("我已经保存了会话来源，但当前回答由本地回退逻辑生成。")

        if not lines:
            return "当前模型暂不可用，且没有检索到足够的本地依据。请稍后重试。"

        lines.append("当前回答基于本地知识库回退生成，稍后模型恢复后可获得更完整回答。")
        return "\n".join(lines)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 24) -> Iterator[str]:
        normalized = text or ""
        for index in range(0, len(normalized), chunk_size):
            yield normalized[index : index + chunk_size]

    @staticmethod
    def _sse_event(event: str, payload: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _extract_chapter_number(self, question: str) -> int | None:
        arabic_match = re.search(r"第\s*(\d+)\s*章", question)
        if arabic_match:
            return int(arabic_match.group(1))

        chinese_match = re.search(r"第\s*([一二三四五六七八九十百零两]+)\s*章", question)
        if chinese_match:
            return self._parse_chinese_number(chinese_match.group(1))
        return None

    @staticmethod
    def _parse_chinese_number(value: str) -> int | None:
        mapping = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if value in mapping:
            return mapping[value]
        if value == "十":
            return 10
        if value.startswith("十") and len(value) == 2:
            tail = mapping.get(value[1])
            return 10 + tail if tail is not None else None
        if value.endswith("十") and len(value) == 2:
            head = mapping.get(value[0])
            return head * 10 if head is not None else None
        if len(value) == 3 and value[1] == "十":
            head = mapping.get(value[0])
            tail = mapping.get(value[2])
            if head is None or tail is None:
                return None
            return head * 10 + tail
        return None

    def _find_document_by_chapter_number(self, chapter_number: int):
        for document in self.store.list_documents():
            file_match = re.match(r"^(\d+)", document.file_name)
            if file_match and int(file_match.group(1)) == chapter_number:
                return document
            if f"第{chapter_number}章" in document.file_name or f"第{chapter_number}回" in document.file_name:
                return document
        return None

    def _chapter_excerpt(self, abs_path: str, limit: int = 220) -> str:
        try:
            loaded = load_document(Path(abs_path))
        except Exception:
            logger.warning("local chapter excerpt load failed for %s", abs_path, exc_info=True)
            return ""
        normalized = " ".join(loaded.text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."
