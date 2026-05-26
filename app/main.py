from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import load_settings
from .book_paths import derive_book_info, normalize_uploaded_rel_path
from .loaders import load_document
from .rag_service import RAGService
from .runtime_logging import configure_logging, tail_log
from .web_ui import build_dashboard_html


settings = load_settings()
settings.books_dir.mkdir(parents=True, exist_ok=True)
settings.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
settings.index_path.parent.mkdir(parents=True, exist_ok=True)
log_path = configure_logging(settings.project_root / "rag.log")
logger = logging.getLogger("rag")
service = RAGService(settings)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, description="用户问题")
    conversation_id: str | None = Field(default=None, description="会话ID，不传则自动生成")
    stream: bool = Field(default=False, description="是否启用流式响应")


class ScanResponse(BaseModel):
    current_files: int | None = None
    new_documents: int | None = None
    updated_documents: int | None = None
    deleted_documents: int | None = None
    added_chunks: int | None = None
    removed_chunks: int | None = None
    documents: int | None = None
    chunks: int | None = None


class UploadResponse(BaseModel):
    saved_files: int
    scan_stats: dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.initial_sync()
    service.start_background_scanner()
    yield
    service.stop_background_scanner()


app = FastAPI(title="图书RAG检索与对话知识库", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    return HTMLResponse(build_dashboard_html(settings))


@app.get("/status")
def status() -> dict:
    return service.get_dashboard_status()


@app.get("/books")
def books() -> list[dict]:
    return service.list_books()


@app.get("/books/content")
def book_content(path: str, preview_chars: int = 8000) -> dict:
    if not path.strip():
        raise HTTPException(status_code=400, detail="path 不能为空")

    preview_chars = max(200, min(preview_chars, 50000))
    base_dir = settings.books_dir.resolve()
    target = (settings.books_dir / Path(path)).resolve()
    if target != base_dir and base_dir not in target.parents:
        raise HTTPException(status_code=400, detail="非法路径")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    loaded = load_document(target)
    rel_path = str(target.relative_to(base_dir).as_posix())
    info = derive_book_info(rel_path, target.name)
    logger.info("book content fetched: path=%s source_type=%s", rel_path, loaded.source_type)
    return {
        "file_name": target.name,
        "rel_path": rel_path,
        "book_name": info.book_name,
        "chapter_name": info.chapter_name,
        "source_type": loaded.source_type,
        "content_length": len(loaded.text),
        "truncated": len(loaded.text) > preview_chars,
        "content": loaded.text[:preview_chars],
    }


@app.get("/logs")
def logs(limit: int = 100) -> dict:
    limit = max(1, min(limit, 500))
    lines = tail_log(log_path, limit)
    return {
        "log_path": str(log_path),
        "count": len(lines),
        "lines": lines,
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "documents": len(service.list_documents()),
        "conversations": len(service.list_conversations()),
    }


@app.post("/chat", response_model=None)
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question 不能为空")
    try:
        if request.stream:
            conversation_id, event_stream = service.chat_stream(request.question.strip(), request.conversation_id)
            return StreamingResponse(
                event_stream,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "X-Conversation-Id": conversation_id,
                },
            )
        return service.chat(request.question.strip(), request.conversation_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/reindex", response_model=ScanResponse)
def reindex() -> dict:
    try:
        stats = service.rebuild_index()
        return stats
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/scan", response_model=ScanResponse)
def scan() -> dict:
    try:
        stats = service.scan_and_update()
        return stats
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload", response_model=UploadResponse)
async def upload(files: list[UploadFile] = File(...), book_name: str | None = Form(None)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="请至少选择一个文件")

    saved_files = 0
    settings.books_dir.mkdir(parents=True, exist_ok=True)
    for upload_file in files:
        if not upload_file.filename:
            continue
        relative_path = normalize_uploaded_rel_path(upload_file.filename, book_name=book_name)
        target_path = settings.books_dir / Path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = await upload_file.read()
        target_path.write_bytes(content)
        saved_files += 1

    try:
        scan_stats = service.scan_and_update()
        logger.info("uploaded %s files, scan stats: %s", saved_files, scan_stats)
        return {"saved_files": saved_files, "scan_stats": scan_stats}
    except Exception as exc:
        logger.exception("upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/documents")
def documents() -> list[dict]:
    return service.list_documents()


@app.get("/conversations")
def conversations() -> list[dict]:
    return service.list_conversations()


@app.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: str) -> dict:
    return service.get_conversation(conversation_id)


def create_app() -> FastAPI:
    return app
