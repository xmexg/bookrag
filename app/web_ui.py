from __future__ import annotations

import json
from html import escape

from .config import Settings


def build_dashboard_html(settings: Settings) -> str:
  api_docs = [
    {
      "key": "status",
      "title": "状态查询",
      "method": "GET",
      "path": "/status",
      "summary": "返回服务运行状态、图书数、文档数、最近扫描时间和下次扫描时间。",
      "requestItems": [],
      "curlExamples": [
        {"title": "基础调用", "code": "curl http://127.0.0.1:8092/status"},
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "{\n  \"server_time\": \"2026-05-26T08:00:00Z\",\n  \"books_dir\": \"D:/qit/25_2/毕业设计/wyj/RAG/books\",\n  \"scan_interval\": 300,\n  \"last_scan_at\": \"2026-05-26T07:55:00Z\",\n  \"next_scan_at\": \"2026-05-26T08:00:00Z\",\n  \"latest_update_at\": \"2026-05-26T07:55:00Z\",\n  \"document_count\": 12,\n  \"active_document_count\": 12,\n  \"book_count\": 3,\n  \"conversation_count\": 5,\n  \"last_scan_stats\": {\n    \"current_files\": 12,\n    \"new_documents\": 0,\n    \"updated_documents\": 0,\n    \"deleted_documents\": 0,\n    \"added_chunks\": 0,\n    \"removed_chunks\": 0\n  }\n}",
        },
      ],
    },
    {
      "key": "books",
      "title": "图书列表",
      "method": "GET",
      "path": "/books",
      "summary": "按图书聚合章节，返回每本书的章节数、活跃章节数和更新时间。",
      "requestItems": [],
      "curlExamples": [
        {"title": "基础调用", "code": "curl http://127.0.0.1:8092/books"},
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "[\n  {\n    \"book_name\": \"西游记\",\n    \"book_path\": \"西游记\",\n    \"source_count\": 4,\n    \"active_source_count\": 4,\n    \"latest_update_at\": \"2026-05-26T07:55:00Z\",\n    \"files\": [\n      {\n        \"file_name\": \"001 灵根育孕源流出.txt\",\n        \"chapter_name\": \"第1回\",\n        \"rel_path\": \"西游记/001 灵根育孕源流出.txt\",\n        \"content_hash\": \"...\",\n        \"file_size\": 20480,\n        \"mtime\": 1716700000.0,\n        \"is_active\": true,\n        \"updated_at\": \"2026-05-26T07:55:00Z\"\n      }\n    ]\n  }\n]",
        },
      ],
    },
    {
      "key": "bookContent",
      "title": "内容预览",
      "method": "GET",
      "path": "/books/content",
      "summary": "按相对路径读取图书正文预览，可限制返回字符数。",
      "requestItems": [
        {
          "name": "path",
          "location": "query",
          "required": True,
          "type": "string",
          "description": "图书相对路径，例如 books/西游记/001 灵根育孕源流出.txt。",
          "example": "books/xiyouji_txt/001 灵根育孕源流出.txt",
        },
        {
          "name": "preview_chars",
          "location": "query",
          "required": False,
          "type": "integer",
          "description": "返回的预览字符数，范围 200~50000，默认 8000。",
          "example": "12000",
        },
      ],
      "curlExamples": [
        {
          "title": "基础调用",
          "code": "curl \"http://127.0.0.1:8092/books/content?path=books/xiyouji_txt/001%20%E7%81%B5%E6%A0%B9%E8%82%B2%E5%AD%95%E6%BA%90%E6%B5%81%E5%87%BA.txt&preview_chars=12000\"",
        },
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "{\n  \"file_name\": \"001 灵根育孕源流出.txt\",\n  \"rel_path\": \"西游记/001 灵根育孕源流出.txt\",\n  \"book_name\": \"西游记\",\n  \"chapter_name\": \"第1回\",\n  \"source_type\": \"text\",\n  \"content_length\": 24567,\n  \"truncated\": true,\n  \"content\": \"...\"\n}",
        },
      ],
    },
    {
      "key": "logs",
      "title": "日志查询",
      "method": "GET",
      "path": "/logs",
      "summary": "返回最近的日志行，便于排查扫描和聊天问题。",
      "requestItems": [
        {
          "name": "limit",
          "location": "query",
          "required": False,
          "type": "integer",
          "description": "返回日志行数，范围 1~500，默认 100。",
          "example": "80",
        },
      ],
      "curlExamples": [
        {"title": "基础调用", "code": "curl \"http://127.0.0.1:8092/logs?limit=80\""},
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "{\n  \"log_path\": \"D:/qit/25_2/毕业设计/wyj/RAG/rag.log\",\n  \"count\": 80,\n  \"lines\": [\n    \"2026-05-26 07:55:00 INFO scan finished: ...\"\n  ]\n}",
        },
      ],
    },
    {
      "key": "health",
      "title": "健康检查",
      "method": "GET",
      "path": "/health",
      "summary": "返回简单的服务健康状态和当前数据量。",
      "requestItems": [],
      "curlExamples": [
        {"title": "基础调用", "code": "curl http://127.0.0.1:8092/health"},
      ],
      "responseExamples": [
        {"title": "响应示例", "code": "{\n  \"status\": \"ok\",\n  \"documents\": 12,\n  \"conversations\": 5\n}"},
      ],
    },
    {
      "key": "chat",
      "title": "AI 对话",
      "method": "POST",
      "path": "/chat",
      "summary": "提交问题，后端会先检索知识库，再调用外部模型回答。stream=true 时返回 SSE。",
      "requestItems": [
        {
          "name": "question",
          "location": "body",
          "required": True,
          "type": "string",
          "description": "用户问题，不能为空。",
          "example": "第3章讲了什么？",
        },
        {
          "name": "conversation_id",
          "location": "body",
          "required": False,
          "type": "string",
          "description": "会话 ID，不传则自动生成。",
          "example": "550e8400-e29b-41d4-a716-446655440000",
        },
        {
          "name": "stream",
          "location": "body",
          "required": False,
          "type": "boolean",
          "description": "是否启用流式响应；false 返回 JSON，true 返回 SSE。",
          "example": "true",
        },
      ],
      "curlExamples": [
        {
          "title": "非流式 JSON",
          "code": "curl -X POST http://127.0.0.1:8092/chat -H \"Content-Type: application/json\" -d \"{\\\"question\\\":\\\"西游记第3章是什么\\\",\\\"stream\\\":false}\"",
        },
        {
          "title": "流式 SSE",
          "code": "curl -N -X POST http://127.0.0.1:8092/chat -H \"Content-Type: application/json\" -H \"Accept: text/event-stream\" -d \"{\\\"question\\\":\\\"西游记第3章是什么\\\",\\\"stream\\\":true}\"",
        },
      ],
      "responseExamples": [
        {
          "title": "非流式响应",
          "code": "{\n  \"conversation_id\": \"550e8400-e29b-41d4-a716-446655440000\",\n  \"answer\": \"...\",\n  \"sources\": [\n    {\n      \"source_index\": 1,\n      \"file_name\": \"001 灵根育孕源流出.txt\",\n      \"rel_path\": \"西游记/001 灵根育孕源流出.txt\",\n      \"book_name\": \"西游记\",\n      \"chapter_name\": \"第1回\",\n      \"chunk_index\": 0,\n      \"score\": 0.91,\n      \"excerpt\": \"...\",\n      \"content_hash\": \"...\"\n    }\n  ],\n  \"source_count\": 1\n}",
        },
        {
          "title": "流式事件",
          "code": "event: meta\ndata: {\"conversation_id\":\"...\",\"stream\":true}\n\nevent: token\ndata: {\"content\":\"正在生成...\"}\n\nevent: done\ndata: {\"conversation_id\":\"...\",\"answer\":\"...\",\"source_count\":1}",
        },
      ],
    },
    {
      "key": "reindex",
      "title": "重建索引",
      "method": "POST",
      "path": "/reindex",
      "summary": "立即重新构建向量索引，不需要请求体。",
      "requestItems": [],
      "curlExamples": [
        {"title": "基础调用", "code": "curl -X POST http://127.0.0.1:8092/reindex"},
      ],
      "responseExamples": [
        {"title": "响应示例", "code": "{\n  \"documents\": 12,\n  \"chunks\": 286\n}"},
      ],
    },
    {
      "key": "scan",
      "title": "扫描更新",
      "method": "POST",
      "path": "/scan",
      "summary": "扫描 books 目录并同步新增、更新、删除的文档。",
      "requestItems": [],
      "curlExamples": [
        {"title": "基础调用", "code": "curl -X POST http://127.0.0.1:8092/scan"},
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "{\n  \"current_files\": 12,\n  \"new_documents\": 0,\n  \"updated_documents\": 0,\n  \"deleted_documents\": 0,\n  \"added_chunks\": 0,\n  \"removed_chunks\": 0,\n  \"documents\": 12,\n  \"chunks\": 286\n}",
        },
      ],
    },
    {
      "key": "upload",
      "title": "上传文件",
      "method": "POST",
      "path": "/upload",
      "summary": "接收 multipart/form-data 文件并触发增量扫描更新。",
      "requestItems": [
        {
          "name": "files",
          "location": "form-data",
          "required": True,
          "type": "file[]",
          "description": "至少一个图书文件，可一次上传多个文件。",
          "example": "@books/xiyouji_txt/001 灵根育孕源流出.txt",
        },
        {
          "name": "book_name",
          "location": "form-data",
          "required": False,
          "type": "string",
          "description": "单文件上传时可指定书名，自动保存到 books/书名/文件名。",
          "example": "西游记",
        },
      ],
      "curlExamples": [
        {
          "title": "基础调用",
          "code": "curl -X POST http://127.0.0.1:8092/upload -F \"files=@books/xiyouji_txt/001 灵根育孕源流出.txt\" -F \"book_name=西游记\"",
        },
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "{\n  \"saved_files\": 1,\n  \"scan_stats\": {\n    \"current_files\": 13,\n    \"new_documents\": 1,\n    \"updated_documents\": 0,\n    \"deleted_documents\": 0,\n    \"added_chunks\": 12,\n    \"removed_chunks\": 0,\n    \"documents\": 13,\n    \"chunks\": 298\n  }\n}",
        },
      ],
    },
    {
      "key": "documents",
      "title": "文档列表",
      "method": "GET",
      "path": "/documents",
      "summary": "返回原始文档清单，包含文件状态、路径和章节信息。",
      "requestItems": [],
      "curlExamples": [
        {"title": "基础调用", "code": "curl http://127.0.0.1:8092/documents"},
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "[\n  {\n    \"id\": 1,\n    \"file_name\": \"001 灵根育孕源流出.txt\",\n    \"rel_path\": \"西游记/001 灵根育孕源流出.txt\",\n    \"abs_path\": \"D:/qit/25_2/毕业设计/wyj/RAG/books/西游记/001 灵根育孕源流出.txt\",\n    \"content_hash\": \"...\",\n    \"file_size\": 20480,\n    \"mtime\": 1716700000.0,\n    \"is_active\": true,\n    \"created_at\": \"2026-05-26T07:55:00Z\",\n    \"updated_at\": \"2026-05-26T07:55:00Z\",\n    \"book_name\": \"西游记\",\n    \"chapter_name\": \"第1回\",\n    \"display_path\": \"西游记/001 灵根育孕源流出.txt\"\n  }\n]",
        },
      ],
    },
    {
      "key": "conversations",
      "title": "会话列表",
      "method": "GET",
      "path": "/conversations",
      "summary": "返回所有会话的标题和更新时间。",
      "requestItems": [],
      "curlExamples": [
        {"title": "基础调用", "code": "curl http://127.0.0.1:8092/conversations"},
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "[\n  {\n    \"id\": \"550e8400-e29b-41d4-a716-446655440000\",\n    \"title\": \"图书对话\",\n    \"created_at\": \"2026-05-26T07:50:00Z\",\n    \"updated_at\": \"2026-05-26T07:55:00Z\"\n  }\n]",
        },
      ],
    },
    {
      "key": "conversationDetail",
      "title": "会话详情",
      "method": "GET",
      "path": "/conversations/{conversation_id}",
      "summary": "按会话 ID 返回完整消息记录，便于回放对话。",
      "requestItems": [
        {
          "name": "conversation_id",
          "location": "path",
          "required": True,
          "type": "string",
          "description": "会话 ID，必须与 /chat 返回的 conversation_id 一致。",
          "example": "550e8400-e29b-41d4-a716-446655440000",
        },
      ],
      "curlExamples": [
        {"title": "基础调用", "code": "curl http://127.0.0.1:8092/conversations/550e8400-e29b-41d4-a716-446655440000"},
      ],
      "responseExamples": [
        {
          "title": "响应示例",
          "code": "{\n  \"conversation_id\": \"550e8400-e29b-41d4-a716-446655440000\",\n  \"messages\": [\n    {\n      \"role\": \"user\",\n      \"content\": \"第3章讲了什么？\",\n      \"sources_json\": null,\n      \"created_at\": \"2026-05-26T07:55:00Z\"\n    },\n    {\n      \"role\": \"assistant\",\n      \"content\": \"...\",\n      \"sources_json\": \"[...]\",\n      \"created_at\": \"2026-05-26T07:55:15Z\"\n    }\n  ]\n}",
        },
      ],
    },
  ]

  config = {
      "booksDir": str(settings.books_dir),
      "scanInterval": settings.recheck_interval,
      "api": {
          "status": "/status",
          "books": "/books",
          "bookContent": "/books/content",
          "logs": "/logs",
          "documents": "/documents",
          "conversations": "/conversations",
          "conversationDetail": "/conversations/{conversation_id}",
          "chat": "/chat",
          "upload": "/upload",
          "scan": "/scan",
          "reindex": "/reindex",
      },
      "apiDocs": api_docs,
  }
  config_json = json.dumps(config, ensure_ascii=False)
  return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>图书RAG知识库</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07111f;
      --bg-2: #0d1728;
      --panel: rgba(14, 24, 43, 0.92);
      --line: rgba(148, 163, 184, 0.18);
      --text: #e8f0fb;
      --muted: #96a7c6;
      --accent: #66e3c4;
      --accent-2: #8ec6ff;
      --good: #37d399;
      --bad: #fc7c8b;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
      --radius: 22px;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(102, 227, 196, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(142, 198, 255, 0.15), transparent 28%),
        linear-gradient(160deg, var(--bg), var(--bg-2));
      color: var(--text);
    }}
    .app-shell {{
      max-width: 1700px;
      margin: 0 auto;
      padding: 20px;
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      gap: 18px;
      min-height: 100vh;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      border-radius: var(--radius);
      backdrop-filter: blur(16px);
    }}
    .sidebar {{
      position: sticky;
      top: 20px;
      height: calc(100vh - 40px);
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      overflow: auto;
    }}
    .brand {{
      display: grid;
      gap: 8px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .eyebrow {{
      display: inline-flex; align-items: center; gap: 8px;
      font-size: 12px; letter-spacing: .18em; text-transform: uppercase;
      color: var(--accent);
    }}
    .brand h1 {{ margin: 0; font-size: 24px; line-height: 1.1; }}
    .brand p {{ margin: 0; color: var(--muted); line-height: 1.6; font-size: 13px; }}
    .nav {{ display: grid; gap: 10px; }}
    .nav-button {{
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.04);
      color: var(--text);
      border-radius: 16px;
      padding: 12px 14px;
      text-align: left;
      cursor: pointer;
      transition: .2s ease;
      font-size: 14px;
    }}
    .nav-button:hover {{ transform: translateY(-1px); border-color: rgba(102, 227, 196, .45); }}
    .nav-button.active {{
      background: linear-gradient(135deg, rgba(102, 227, 196, .18), rgba(142, 198, 255, .16));
      border-color: rgba(102, 227, 196, .35);
    }}
    .sidebar-card {{
      padding: 14px 15px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .meta-label {{ color: var(--muted); font-size: 12px; margin-bottom: 8px; letter-spacing: .06em; text-transform: uppercase; }}
    .meta-value {{ font-size: 15px; font-weight: 700; line-height: 1.5; word-break: break-all; }}
    .sidebar-foot {{ color: var(--muted); font-size: 12px; line-height: 1.6; margin-top: auto; }}
    .main {{ display: grid; gap: 18px; align-content: start; }}
    .view {{ display: none; gap: 18px; animation: lift 0.45s ease both; }}
    .view.active {{ display: grid; }}
    .hero {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 18px; }}
    .hero-main {{ padding: 28px; }}
    .hero-main h2 {{ margin: 12px 0 10px; font-size: clamp(28px, 4vw, 54px); line-height: 1.05; }}
    .lead {{ color: var(--muted); max-width: 68ch; line-height: 1.7; margin: 0; }}
    .hero-meta {{ display: grid; gap: 12px; padding: 20px; }}
    .meta-card {{
      padding: 16px 18px; border-radius: 18px; background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
    }}
    .grid {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 18px; }}
    .section {{ padding: 22px; }}
    h3 {{ margin:0;min-width: fit-content; }}
    .section h3 {{ margin: 0 0 14px; font-size: 18px; }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }}
    .button {{
      border: 1px solid var(--line); background: rgba(255,255,255,0.04); color: var(--text);
      border-radius: 14px; padding: 11px 16px; cursor: pointer; transition: .2s ease;
    }}
    .button:hover {{ transform: translateY(-1px); border-color: rgba(102,227,196,.45); }}
    .button.primary {{ background: linear-gradient(135deg, rgba(102,227,196,.18), rgba(142,198,255,.18)); }}
    .button.good {{ background: rgba(55, 211, 153, 0.12); }}
    .field, textarea {{
      width: 100%; background: rgba(255,255,255,0.04); color: var(--text);
      border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px; outline: none;
    }}
    textarea {{ min-height: 118px; resize: vertical; line-height: 1.6; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .summary-card {{
      padding: 16px 18px; border-radius: 18px; background: rgba(255,255,255,0.035);
      border: 1px solid rgba(255,255,255,0.06);
    }}
    .summary-card .value {{ font-size: 22px; font-weight: 800; margin-top: 6px; }}
    .small {{ color: var(--muted); font-size: 13px; line-height: 1.6; word-break: break-all; }}
    .books-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 12px; }}
    .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 999px; font-size: 12px; background: rgba(255,255,255,0.06); color: var(--text); }}
    .badge.active {{ background: rgba(55, 211, 153, 0.15); color: #9ef4cc; }}
    .badge.inactive {{ background: rgba(252, 124, 139, 0.14); color: #fec0ca; }}
    .books {{ display: grid; gap: 12px; max-height: 560px; overflow: auto; padding-right: 4px; }}
    .book {{ padding: 16px; border-radius: 18px; background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.06); }}
    .book-top {{ display: flex; justify-content: space-between; gap: 12px; align-items: start; }}
    .book-title {{ font-weight: 800; margin-bottom: 6px; word-break: break-all; }}
    .book-meta {{ color: var(--muted); font-size: 13px; line-height: 1.6; word-break: break-all; }}
    .uploader {{
      margin-top: 14px; border: 1px dashed rgba(102,227,196,.35); border-radius: 18px; padding: 16px; background: rgba(255,255,255,0.03);
    }}
    .dropzone {{
      border: 1px dashed rgba(142,198,255,.45); border-radius: 18px; padding: 18px; text-align: center; color: var(--muted);
      background: rgba(255,255,255,0.02); cursor: pointer;
    }}
    .dropzone.dragging {{ border-color: var(--accent); background: rgba(102, 227, 196, 0.08); color: var(--text); }}
    .chat-log {{ display: grid; gap: 12px; max-height: 560px; overflow: auto; padding-right: 4px; }}
    .msg {{ padding: 14px 16px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.07); background: rgba(255,255,255,0.03); }}
    .msg.user {{ background: rgba(102, 227, 196, 0.09); }}
    .msg.assistant {{ background: rgba(142, 198, 255, 0.08); }}
    .msg .role {{ font-size: 12px; color: var(--accent); margin-bottom: 8px; letter-spacing: .12em; text-transform: uppercase; }}
    .msg .content {{ white-space: pre-wrap; line-height: 1.75; }}
    .sources {{ margin-top: 10px; display: grid; gap: 8px; }}
    .source {{ padding: 10px 12px; border-radius: 14px; background: rgba(255,255,255,0.04); color: var(--muted); font-size: 13px; line-height: 1.6; }}
    .mini-button {{ border: 1px solid rgba(148,163,184,0.22); background: rgba(255,255,255,0.04); color: var(--text); border-radius: 999px; padding: 5px 10px; cursor: pointer; font-size: 12px; }}
    .mini-button:hover {{ border-color: rgba(102,227,196,.45); }}
    .log-list {{ display: grid; gap: 8px; max-height: 280px; overflow: auto; }}
    .log-line {{ padding: 9px 10px; border-radius: 12px; background: rgba(255,255,255,0.04); color: var(--muted); font-size: 12px; line-height: 1.55; white-space: pre-wrap; word-break: break-all; }}
    .preview-pane {{ margin-top: 14px; padding: 14px; border-radius: 18px; background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.06); }}
    .preview-content {{ white-space: pre-wrap; line-height: 1.75; max-height: 360px; overflow: auto; color: var(--text); min-height: 93%;}}
    .endpoint-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .endpoint {{ padding: 16px; border-radius: 18px; background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.06); }}
    .endpoint-head {{ display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 8px; }}
    .endpoint-card {{ padding: 16px; border-radius: 18px; background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.06); display: grid; gap: 10px; }}
    .endpoint-card .endpoint-head {{ display: flex; justify-content: space-between; gap: 10px; align-items: start; margin-bottom: 0; }}
    .endpoint-title {{ display: grid; gap: 6px; }}
    .endpoint-path {{ font-size: 13px; color: var(--muted); word-break: break-all; }}
    .endpoint-summary {{ color: var(--text); line-height: 1.6; font-size: 13px; }}
    .api-detail-actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .api-modal {{ position: fixed; inset: 0; z-index: 40; display: none; align-items: center; justify-content: center; padding: 18px; background: rgba(2, 6, 23, 0.64); backdrop-filter: blur(10px); }}
    .api-modal.visible {{ display: flex; }}
    .api-modal-card {{ width: min(1080px, 100%); max-height: min(88vh, 920px); overflow: auto; border-radius: 24px; padding: 22px; background: rgba(8, 16, 30, 0.98); border: 1px solid rgba(102,227,196,.18); box-shadow: 0 30px 100px rgba(0,0,0,.42); }}
    .api-modal-head {{ display: flex; justify-content: space-between; gap: 14px; align-items: start; margin-bottom: 18px; }}
    .api-modal-title {{ font-size: 22px; font-weight: 800; line-height: 1.2; }}
    .api-modal-subtitle {{ color: var(--muted); font-size: 13px; margin-top: 6px; line-height: 1.6; }}
    .api-detail-grid {{ display: grid; gap: 14px; }}
    .api-detail-block {{ padding: 14px 16px; border-radius: 18px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); }}
    .api-detail-block h4 {{ margin: 0 0 10px; font-size: 14px; letter-spacing: .04em; color: var(--accent-2); text-transform: uppercase; }}
    .api-param-list {{ display: grid; gap: 10px; }}
    .api-param {{ padding: 12px 14px; border-radius: 16px; background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.06); }}
    .api-param-top {{ display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 6px; }}
    .api-param-name {{ font-weight: 800; }}
    .api-param-meta {{ color: var(--muted); font-size: 12px; line-height: 1.6; }}
    .api-example-list {{ display: grid; gap: 12px; }}
    .api-example-title {{ margin: 0 0 8px; font-size: 13px; color: var(--accent); letter-spacing: .04em; text-transform: uppercase; }}
    .method {{ font-size: 12px; padding: 4px 10px; border-radius: 999px; background: rgba(102,227,196,0.14); color: #aaf4e7; }}
    .code {{
      margin: 12px 0 0; padding: 14px 16px; border-radius: 16px; background: rgba(0,0,0,0.28);
      border: 1px solid rgba(255,255,255,0.07); white-space: pre-wrap; overflow: auto; line-height: 1.7;
    }}
    .footer-note {{ margin-top: 12px; color: var(--muted); font-size: 13px; }}
    .hidden {{ display: none; }}
    @keyframes lift {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @media (max-width: 1240px) {{
      .app-shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; }}
      .hero, .grid, .endpoint-grid, .summary-grid {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (max-width: 820px) {{
      .hero, .grid, .endpoint-grid, .summary-grid {{ grid-template-columns: 1fr; }}
      .app-shell {{ padding: 14px; }}
      .section, .hero-main, .hero-meta {{ padding: 18px; }}
    }}
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="panel sidebar">
      <div class="brand">
        <div class="eyebrow">Local Book RAG</div>
        <h1>图书知识库</h1>
        <p>侧边栏切换首页、状态日志、图书检阅、AI 对话和 API 使用说明。</p>
      </div>

      <nav class="nav" aria-label="页面导航">
        <button class="nav-button active" data-nav="home" onclick="switchView('home')">首页</button>
        <button class="nav-button" data-nav="status" onclick="switchView('status')">状态和日志</button>
        <button class="nav-button" data-nav="books" onclick="switchView('books')">图书检阅和上传</button>
        <button class="nav-button" data-nav="chat" onclick="switchView('chat')">AI 对话</button>
        <button class="nav-button" data-nav="api" onclick="switchView('api')">API 使用说明</button>
      </nav>

      <div class="sidebar-card">
        <div class="meta-label">当前图书目录</div>
        <div class="meta-value" id="sidebarBooksDir">{escape(str(settings.books_dir))}</div>
      </div>
      <div class="sidebar-card">
        <div class="meta-label">扫描间隔</div>
        <div class="meta-value" id="sidebarScanInterval">{settings.recheck_interval} 秒</div>
      </div>
      <div class="sidebar-card">
        <div class="meta-label">书本 / 文档</div>
        <div class="meta-value"><span id="sidebarBookCount">0</span> 本，<span id="sidebarDocumentCount">0</span> 份</div>
      </div>
      <div class="sidebar-foot">上传新文件后会自动增量扫描并刷新索引。若外部模型暂时不可用，聊天会回退到本地检索结果。</div>
    </aside>

    <main class="main">
      <section class="view active" data-view="home">
        <div class="panel hero">
          <div class="panel hero-main">
            <div class="eyebrow">Dashboard</div>
            <h2>图书检索、增量更新与 AI 对话</h2>
            <p class="lead">支持本地图书目录自动扫描、hash 去重、SQLite 持久化、FAISS 检索，以及带来源引用的 AI 对话。上传新书后会自动触发增量入库，页面会实时刷新状态与日志。</p>
            <div class="toolbar" style="margin-top:18px;">
              <button class="button primary" onclick="switchView('status')">查看状态</button>
              <button class="button" onclick="switchView('books')">浏览图书</button>
              <button class="button good" onclick="switchView('chat')">开始对话</button>
            </div>
          </div>
          <div class="panel hero-meta">
            <div class="meta-card">
              <div class="meta-label">最近更新时间</div>
              <div class="meta-value" id="homeLastScanAt">加载中...</div>
            </div>
            <div class="meta-card">
              <div class="meta-label">下次更新图书时间</div>
              <div class="meta-value" id="homeNextScanAt">加载中...</div>
            </div>
            <div class="meta-card">
              <div class="meta-label">扫描结果</div>
              <div class="meta-value" id="homeScanStats">加载中...</div>
            </div>
          </div>
        </div>

        <div class="panel section">
          <h3>概览</h3>
          <div class="summary-grid">
            <div class="summary-card">
              <div class="meta-label">图书数</div>
              <div class="value" id="homeBookCount">0</div>
            </div>
            <div class="summary-card">
              <div class="meta-label">文档数</div>
              <div class="value" id="homeDocumentCount">0</div>
            </div>
            <div class="summary-card">
              <div class="meta-label">会话数</div>
              <div class="value" id="homeConversationCount">0</div>
            </div>
            <div class="summary-card">
              <div class="meta-label">活跃文档</div>
              <div class="value" id="homeActiveDocumentCount">0</div>
            </div>
          </div>
        </div>
      </section>

      <section class="view" data-view="status">
        <div class="panel section">
          <h3>状态</h3>
          <div class="summary-grid">
            <div class="summary-card">
              <div class="meta-label">图书数</div>
              <div class="value" id="statusBookCount">0</div>
            </div>
            <div class="summary-card">
              <div class="meta-label">文档数</div>
              <div class="value" id="statusDocumentCount">0</div>
            </div>
            <div class="summary-card">
              <div class="meta-label">最近更新时间</div>
              <div class="value" id="statusLastScanAt">暂无</div>
            </div>
            <div class="summary-card">
              <div class="meta-label">下次更新图书时间</div>
              <div class="value" id="statusNextScanAt">暂无</div>
            </div>
          </div>
          <div class="preview-pane">
            <div class="meta-label">最近扫描统计</div>
            <div class="preview-content" id="scanStats">暂无</div>
          </div>
        </div>

        <div class="panel section">
          <div class="books-head" style="display:flex;justify-content:space-between;gap:12px;align-items:center;">
            <h3 style="margin:0;">日志</h3>
            <button class="button" onclick="refreshLogs()">刷新日志</button>
          </div>
          <div class="log-list" id="logList"></div>
        </div>
      </section>

      <section class="view" data-view="books">
        <div class="grid" style="height: 97vh;">
          <div class="panel section">
            <div class="books-head">
              <div>
                <h3>图书检阅和上传</h3>
                <div class="small" id="booksSummary">加载中...</div>
              </div>
              <div class="badge" id="docCountBadge">0 本</div>
            </div>
            <div class="uploader">
              <div class="dropzone" id="dropzone">拖拽图书到这里，或点击选择文件</div>
              <input class="hidden" id="fileInput" type="file" multiple accept=".txt,.md,.markdown,.pdf,.docx" />
              <input class="hidden" id="folderInput" type="file" multiple webkitdirectory accept=".txt,.md,.markdown,.pdf,.docx" />
              <div class="toolbar" style="margin-top:12px;">
                <input class="field" id="bookNameInput" placeholder="可选：单文件或多文件同书时填写书名" />
              </div>
              <div class="toolbar">
                <button class="button primary" onclick="document.getElementById('fileInput').click()">选择文件</button>
                <button class="button" onclick="document.getElementById('folderInput').click()">选择文件夹</button>
                <button class="button good" onclick="uploadFiles()">上传并更新</button>
              </div>
              <div class="small">支持 txt、md、markdown、pdf、docx。选择文件夹时会保留目录层级；选择单文件时可填写书名，自动保存到 books/书名/文件名。</div>
            </div>
            <div class="books" id="booksList" style="margin-top:14px;"></div>
          </div>

          <div class="panel section">
            <div class="books-head">
              <h3 style="margin:0;">内容预览</h3>
              <div class="small" id="previewMeta">点击左侧文件查看内容</div>
            </div>
            <div class="preview-content" id="bookPreview">这里会显示 books 目录中文件的内容预览。</div>
          </div>
        </div>
      </section>

      <section class="view" data-view="chat">
        <div class="panel section">
          <h3>AI 对话框</h3>
          <div class="toolbar">
            <input class="field" id="conversationId" placeholder="会话ID，留空则自动新建" />
            <button class="button" onclick="startNewConversation()">新会话</button>
          </div>
          <textarea id="question" placeholder="输入问题，AI 会结合图书知识库作答并标注来源..."></textarea>
          <div class="toolbar" style="margin-top:12px;">
            <button class="button primary" id="sendButton" onclick="sendMessage()">发送</button>
            <button class="button" onclick="clearChat()">清空</button>
          </div>
          <label class="small" style="display:flex;align-items:center;gap:8px;margin-top:8px;">
            <input id="streamToggle" type="checkbox" checked />
            流式响应
          </label>
          <div class="footer-note">会话历史会保存在本地服务中，刷新页面后仍然可追踪。若外部模型响应缓慢，页面会先显示“正在思考”。</div>
          <div class="chat-log" id="chatLog" style="margin-top:16px;"></div>
        </div>
      </section>

      <section class="view" data-view="api">
        <div class="panel section">
          <div class="books-head">
            <div>
              <h3 style="margin:0;">API 使用说明</h3>
              <div class="small">当前后端公开接口共 <span id="apiDocCount">0</span> 个，和 app/main.py 保持一致。点击接口卡片可显示/隐藏悬浮窗，查看参数、curl 和响应示例。</div>
            </div>
            <div class="badge" id="apiCountBadge">0 个接口</div>
          </div>
          <div class="endpoint-grid" id="apiDocsGrid"></div>
          <div class="preview-pane">
            <div class="meta-label">使用提示</div>
            <div class="preview-content" id="apiOverview">点击任一接口卡片的“显示详情”按钮，打开浮窗查看详细参数说明、curl 请求示例和响应示例。流式对话支持 stream=true/false 两种模式。</div>
          </div>
        </div>
        <div class="api-modal hidden" id="apiDetailOverlay" aria-hidden="true">
          <div class="api-modal-card" id="apiDetailCard">
            <div class="api-modal-head">
              <div>
                <div class="api-modal-title" id="apiDetailTitle">接口详情</div>
                <div class="api-modal-subtitle" id="apiDetailSubtitle">选择一个接口后会显示请求参数、curl 示例和响应示例。</div>
              </div>
              <button class="button" id="closeApiDetailBtn" type="button">关闭</button>
            </div>
            <div class="api-detail-grid" id="apiDetailBody"></div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script>
    const APP = {{ config: {config_json} }};
    const state = {{ conversationId: localStorage.getItem('rag_conversation_id') || '', activeView: 'home' }};
    let pendingUploadFiles = [];
    const apiDocs = APP.config.apiDocs || [];
    let activeApiDetailIndex = null;

    const fmt = (value) => value ? new Date(value).toLocaleString('zh-CN') : '暂无';

    function escapeHtml(value) {{
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }}

    function setConversationId(id) {{
      state.conversationId = id || '';
      localStorage.setItem('rag_conversation_id', state.conversationId);
      const input = document.getElementById('conversationId');
      if (input) {{
        input.value = state.conversationId;
      }}
    }}

    function setText(id, value) {{
      const element = document.getElementById(id);
      if (element) {{
        element.textContent = value;
      }}
    }}

    function setMessageContent(messageElement, value) {{
      const content = messageElement.querySelector('.content');
      if (content) {{
        content.textContent = value;
      }}
    }}

    async function fetchJson(url, options = {{}}) {{
      const response = await fetch(url, options);
      if (!response.ok) {{
        const text = await response.text();
        throw new Error(text || response.statusText || `HTTP ${{response.status}}`);
      }}
      return response.json();
    }}

    function parseSseBlock(block) {{
      let eventName = 'message';
      const dataLines = [];
      for (const rawLine of block.split(String.fromCharCode(10))) {{
        const line = rawLine.replaceAll(String.fromCharCode(13), '');
        if (line.startsWith('event:')) {{
          eventName = line.slice(6).trim();
        }} else if (line.startsWith('data:')) {{
          dataLines.push(line.slice(5).trimStart());
        }}
      }}
      if (!dataLines.length) {{
        return null;
      }}
      const dataText = dataLines.join(String.fromCharCode(10));
      try {{
        return {{ eventName, payload: JSON.parse(dataText) }};
      }} catch {{
        return {{ eventName, payload: dataText }};
      }}
    }}

    function switchView(viewName) {{
      state.activeView = viewName;
      document.querySelectorAll('.view').forEach((section) => {{
        section.classList.toggle('active', section.dataset.view === viewName);
      }});
      document.querySelectorAll('.nav-button').forEach((button) => {{
        button.classList.toggle('active', button.dataset.nav === viewName);
      }});
      if (viewName === 'api') {{
        renderApiDocs();
      }}
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function renderApiDocs() {{
      const grid = document.getElementById('apiDocsGrid');
      if (!grid) {{
        return;
      }}
      setText('apiDocCount', String(apiDocs.length));
      setText('apiCountBadge', `${{apiDocs.length}} 个接口`);
      grid.innerHTML = apiDocs.map((doc, index) => `
        <article class="endpoint-card">
          <div class="endpoint-head">
            <div class="endpoint-title">
              <strong>${{escapeHtml(doc.title)}}</strong>
              <div class="endpoint-path">${{escapeHtml(doc.method)}} ${{escapeHtml(doc.path)}}</div>
            </div>
            <span class="method">${{escapeHtml(doc.method)}}</span>
          </div>
          <div class="endpoint-summary">${{escapeHtml(doc.summary)}}</div>
          <div class="code">${{escapeHtml(doc.method)}} ${{escapeHtml(doc.path)}}</div>
          <div class="api-detail-actions">
            <button class="button primary" type="button" onclick="toggleApiDetail(${{index}})">${{activeApiDetailIndex === index ? '隐藏详情' : '显示详情'}}</button>
          </div>
        </article>
      `).join('');
    }}

    function toggleApiDetail(index) {{
      if (activeApiDetailIndex === index) {{
        closeApiDetail();
        return;
      }}
      openApiDetail(index);
    }}

    function openApiDetail(index) {{
      const doc = apiDocs[index];
      if (!doc) {{
        return;
      }}
      activeApiDetailIndex = index;
      const overlay = document.getElementById('apiDetailOverlay');
      const title = document.getElementById('apiDetailTitle');
      const subtitle = document.getElementById('apiDetailSubtitle');
      const body = document.getElementById('apiDetailBody');
      if (!overlay || !title || !subtitle || !body) {{
        return;
      }}
      title.textContent = `${{doc.title}} · ${{doc.method}} ${{doc.path}}`;
      subtitle.textContent = doc.summary;

      const requestItems = (doc.requestItems || []).map((item) => `
        <div class="api-param">
          <div class="api-param-top">
            <div class="api-param-name">${{escapeHtml(item.name)}}</div>
            <span class="badge">${{escapeHtml(item.location)}} · ${{item.required ? '必填' : '可选'}}</span>
          </div>
          <div class="api-param-meta">类型：${{escapeHtml(item.type || 'string')}}<br/>说明：${{escapeHtml(item.description || '暂无')}}<br/>示例：${{escapeHtml(item.example || '无')}}</div>
        </div>
      `).join('') || '<div class="small">该接口没有额外参数。</div>';

      const curlExamples = (doc.curlExamples || []).map((example) => `
        <div>
          <div class="api-example-title">${{escapeHtml(example.title || 'curl 示例')}}</div>
          <div class="code">${{escapeHtml(example.code || '')}}</div>
        </div>
      `).join('');

      const responseExamples = (doc.responseExamples || []).map((example) => `
        <div>
          <div class="api-example-title">${{escapeHtml(example.title || '响应示例')}}</div>
          <div class="code">${{escapeHtml(example.code || '')}}</div>
        </div>
      `).join('');

      body.innerHTML = `
        <div class="api-detail-block">
          <h4>请求说明</h4>
          <div class="small">接口路径：${{escapeHtml(doc.path)}}<br/>请求方式：${{escapeHtml(doc.method)}}<br/>说明：${{escapeHtml(doc.summary)}}</div>
        </div>
        <div class="api-detail-block">
          <h4>参数说明</h4>
          <div class="api-param-list">${{requestItems}}</div>
        </div>
        <div class="api-detail-block">
          <h4>curl 示例</h4>
          <div class="api-example-list">${{curlExamples}}</div>
        </div>
        <div class="api-detail-block">
          <h4>响应示例</h4>
          <div class="api-example-list">${{responseExamples}}</div>
        </div>
      `;

      overlay.classList.add('visible');
      overlay.classList.remove('hidden');
      overlay.setAttribute('aria-hidden', 'false');
      renderApiDocs();
    }}

    function closeApiDetail() {{
      activeApiDetailIndex = null;
      const overlay = document.getElementById('apiDetailOverlay');
      if (overlay) {{
        overlay.classList.remove('visible');
        overlay.classList.add('hidden');
        overlay.setAttribute('aria-hidden', 'true');
      }}
      renderApiDocs();
    }}

    function updateStatusCards(status) {{
      const bookCount = status.book_count ?? 0;
      const documentCount = status.document_count ?? 0;
      const conversationCount = status.conversation_count ?? 0;
      const activeDocumentCount = status.active_document_count ?? 0;
      const nextScanAt = fmt(status.next_scan_at);
      const lastScanAt = fmt(status.last_scan_at);
      const scanStats = status.last_scan_stats ? JSON.stringify(status.last_scan_stats, null, 2) : '暂无扫描记录';

      ['homeBookCount', 'statusBookCount', 'sidebarBookCount'].forEach((id) => setText(id, String(bookCount)));
      ['homeDocumentCount', 'statusDocumentCount', 'sidebarDocumentCount'].forEach((id) => setText(id, String(documentCount)));
      setText('homeConversationCount', String(conversationCount));
      setText('homeActiveDocumentCount', String(activeDocumentCount));
      setText('homeNextScanAt', nextScanAt);
      setText('homeLastScanAt', lastScanAt);
      setText('homeScanStats', scanStats);
      setText('statusNextScanAt', nextScanAt);
      setText('statusLastScanAt', lastScanAt);
      setText('scanStats', scanStats);
    }}

    function bookCard(book) {{
      const status = book.active_source_count > 0 ? 'active' : 'inactive';
      const label = `${{book.active_source_count}} / ${{book.source_count}}`;
      const fileRows = (book.files || []).map((file) => `
        <div class="source" style="margin-top:8px;">
          <strong>${{escapeHtml(file.chapter_name)}}</strong><br/>
          路径：${{escapeHtml(file.rel_path)}}<br/>
          Hash：${{escapeHtml(file.content_hash)}}<br/>
          更新时间：${{escapeHtml(fmt(file.updated_at))}}
          <div style="margin-top:8px;">
            <button class="mini-button" onclick='loadBookContent(${{JSON.stringify(file.rel_path)}})'>查看内容</button>
          </div>
        </div>
      `).join('');
      return `
        <div class="book">
          <div class="book-top">
            <div>
              <div class="book-title">${{escapeHtml(book.book_name)}}</div>
              <div class="book-meta">书本路径：${{escapeHtml(book.book_path)}}</div>
              <div class="book-meta">章节数：${{book.source_count}}，活跃章节：${{book.active_source_count}}</div>
            </div>
            <span class="badge ${{status}}">${{label}}</span>
          </div>
          <div class="small" style="margin-top:10px;">最后更新：${{escapeHtml(fmt(book.latest_update_at))}}</div>
          <div>${{fileRows}}</div>
        </div>`;
    }}

    async function refreshStatus() {{
      try {{
        const status = await fetchJson(APP.config.api.status);
        updateStatusCards(status);
      }} catch (error) {{
        const message = `状态加载失败：${{error.message}}`;
        ['homeLastScanAt', 'statusLastScanAt', 'homeNextScanAt', 'statusNextScanAt'].forEach((id) => setText(id, message));
        setText('homeScanStats', message);
        setText('scanStats', message);
      }}
    }}

    async function refreshBooks() {{
      try {{
        const books = await fetchJson(APP.config.api.books);
        const container = document.getElementById('booksList');
        if (container) {{
          container.innerHTML = books.length ? books.map(bookCard).join('') : '<div class="small">当前没有图书，请先上传。</div>';
        }}
        setText('docCountBadge', `${{books.length}} 本`);
        setText('booksSummary', books.length ? `当前共 ${{books.length}} 本图书，点击章节卡片即可查看内容预览。` : '当前没有图书，请先上传。');
      }} catch (error) {{
        setText('booksList', '图书列表加载失败：' + error.message);
        setText('booksSummary', '图书列表加载失败：' + error.message);
      }}
    }}

    async function refreshLogs() {{
      try {{
        const result = await fetchJson(`${{APP.config.api.logs}}?limit=80`);
        const lines = result.lines || [];
        const container = document.getElementById('logList');
        if (container) {{
          container.innerHTML = lines.length ? lines.map((line) => `<div class="log-line">${{escapeHtml(line)}}</div>`).join('') : '<div class="small">暂无日志。</div>';
        }}
      }} catch (error) {{
        setText('logList', '日志加载失败：' + error.message);
      }}
    }}

    async function loadBookContent(path) {{
      try {{
        const result = await fetchJson(`${{APP.config.api.bookContent}}?path=${{encodeURIComponent(path)}}&preview_chars=12000`);
        setText('previewMeta', `${{result.book_name}} / ${{result.chapter_name}} / ${{result.rel_path}}`);
        const preview = document.getElementById('bookPreview');
        if (preview) {{
          preview.textContent = result.content || '空内容';
        }}
        switchView('books');
      }} catch (error) {{
        setText('previewMeta', '预览加载失败');
        setText('bookPreview', '内容预览失败：' + error.message);
      }}
    }}

    async function refreshAll() {{
      await Promise.allSettled([refreshStatus(), refreshBooks(), refreshLogs()]);
    }}

    async function triggerScan() {{
      await fetchJson(APP.config.api.scan, {{ method: 'POST' }});
      await refreshAll();
    }}

    async function triggerReindex() {{
      await fetchJson(APP.config.api.reindex, {{ method: 'POST' }});
      await refreshAll();
    }}

    async function uploadFiles() {{
      const fileInput = document.getElementById('fileInput');
      const folderInput = document.getElementById('folderInput');
      const files = pendingUploadFiles.length ? pendingUploadFiles : [
        ...(fileInput.files ? Array.from(fileInput.files) : []),
        ...(folderInput.files ? Array.from(folderInput.files) : []),
      ];
      if (!files.length) {{
        alert('请选择要上传的图书文件');
        return;
      }}
      const formData = new FormData();
      const bookName = document.getElementById('bookNameInput').value.trim();
      if (bookName) {{
        formData.append('book_name', bookName);
      }}
      for (const file of files) {{
        const relativeName = file.webkitRelativePath || file.relativePath || file.name;
        formData.append('files', file, relativeName);
      }}
      const response = await fetch(APP.config.api.upload, {{ method: 'POST', body: formData }});
      if (!response.ok) {{
        const text = await response.text();
        alert(text || '上传失败');
        return;
      }}
      fileInput.value = '';
      folderInput.value = '';
      document.getElementById('bookNameInput').value = '';
      pendingUploadFiles = [];
      await refreshAll();
      switchView('books');
    }}

    function renderSources(sources) {{
      if (!sources || !sources.length) {{
        return '';
      }}
      return `<div class="sources">${{sources.map((item) => `<div class="source">来源${{item.source_index}} | ${{escapeHtml(item.file_name)}} | 第${{item.chunk_index + 1}}块<br/>${{escapeHtml(item.excerpt)}}</div>`).join('')}}</div>`;
    }}

    function createMessage(role, content, sources = []) {{
      const item = document.createElement('div');
      item.className = `msg ${{role}}`;
      item.innerHTML = `<div class="role">${{role === 'user' ? '你' : 'AI'}}</div><div class="content">${{escapeHtml(content)}}</div>${{renderSources(sources)}}`;
      return item;
    }}

    function appendMessage(role, content, sources = []) {{
      const log = document.getElementById('chatLog');
      const item = createMessage(role, content, sources);
      log.appendChild(item);
      log.scrollTop = log.scrollHeight;
      return item;
    }}

    async function sendMessage() {{
      const questionInput = document.getElementById('question');
      const question = questionInput.value.trim();
      if (!question) {{
        alert('请输入问题');
        return;
      }}
      const streamEnabled = document.getElementById('streamToggle').checked;
      localStorage.setItem('rag_stream_enabled', streamEnabled ? 'true' : 'false');
      if (!state.conversationId) {{
        setConversationId(crypto.randomUUID());
      }}
      const sendButton = document.getElementById('sendButton');
      sendButton.disabled = true;
      appendMessage('user', question);
      questionInput.value = '';
      const pending = appendMessage('assistant', streamEnabled ? 'AI 正在流式响应...' : 'AI 正在思考...');
      try {{
        const requestBody = {{ question, conversation_id: state.conversationId, stream: streamEnabled }};
        if (!streamEnabled) {{
          const result = await fetchJson(APP.config.api.chat, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(requestBody)
          }});
          setConversationId(result.conversation_id);
          pending.replaceWith(createMessage('assistant', result.answer || '没有返回内容', result.sources || []));
          return;
        }}

        const response = await fetch(APP.config.api.chat, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json', 'Accept': 'text/event-stream' }},
          body: JSON.stringify(requestBody)
        }});
        if (!response.ok) {{
          const text = await response.text();
          throw new Error(text || response.statusText || `HTTP ${{response.status}}`);
        }}
        if (!response.body) {{
          throw new Error('当前浏览器不支持流式读取');
        }}

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let answerText = '';
        let finalPayload = null;

        while (true) {{
          const {{ value, done }} = await reader.read();
          if (done) {{
            break;
          }}
          buffer += decoder.decode(value, {{ stream: true }});
            const blockSeparator = String.fromCharCode(10) + String.fromCharCode(10);
            const blocks = buffer.split(blockSeparator);
          buffer = blocks.pop() || '';
          for (const block of blocks) {{
            const event = parseSseBlock(block);
            if (!event) {{
              continue;
            }}
            const payload = event.payload;
            if (event.eventName === 'meta' && payload && typeof payload === 'object' && payload.conversation_id) {{
              setConversationId(payload.conversation_id);
              continue;
            }}
            if (event.eventName === 'token' && payload && typeof payload === 'object' && typeof payload.content === 'string') {{
              answerText += payload.content;
              setMessageContent(pending, answerText || 'AI 正在流式响应...');
              continue;
            }}
            if (event.eventName === 'done' && payload && typeof payload === 'object') {{
              finalPayload = payload;
            }}
          }}
        }}

        buffer += decoder.decode();
        if (buffer.trim()) {{
          const event = parseSseBlock(buffer);
          if (event && event.eventName === 'token' && event.payload && typeof event.payload === 'object' && typeof event.payload.content === 'string') {{
            answerText += event.payload.content;
            setMessageContent(pending, answerText || 'AI 正在流式响应...');
          }} else if (event && event.eventName === 'done' && event.payload && typeof event.payload === 'object') {{
            finalPayload = event.payload;
          }}
        }}

        if (finalPayload) {{
          if (finalPayload.conversation_id) {{
            setConversationId(finalPayload.conversation_id);
          }}
          pending.replaceWith(createMessage('assistant', finalPayload.answer || answerText || '没有返回内容', finalPayload.sources || []));
        }} else {{
          pending.replaceWith(createMessage('assistant', answerText || '没有返回内容'));
        }}
      }} catch (error) {{
        pending.replaceWith(createMessage('assistant', `AI 回复失败：${{error.message}}。你可以稍后重试，或先切到“状态和日志”查看后端日志。`));
      }} finally {{
        sendButton.disabled = false;
      }}
    }}

    function startNewConversation() {{
      setConversationId(crypto.randomUUID());
      document.getElementById('chatLog').innerHTML = '';
    }}

    function clearChat() {{
      document.getElementById('chatLog').innerHTML = '';
    }}

    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    fileInput.addEventListener('change', () => {{ pendingUploadFiles = Array.from(fileInput.files || []); }});
    folderInput.addEventListener('change', () => {{ pendingUploadFiles = Array.from(folderInput.files || []); }});
    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (event) => {{ event.preventDefault(); dropzone.classList.add('dragging'); }});
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragging'));
    dropzone.addEventListener('drop', (event) => {{
      event.preventDefault();
      dropzone.classList.remove('dragging');
      pendingUploadFiles = Array.from(event.dataTransfer.files || []);
    }});

    document.getElementById('conversationId').value = state.conversationId;
    const streamToggle = document.getElementById('streamToggle');
    const savedStreamEnabled = localStorage.getItem('rag_stream_enabled');
    streamToggle.checked = savedStreamEnabled === null ? true : savedStreamEnabled === 'true';
    streamToggle.addEventListener('change', () => {{
      localStorage.setItem('rag_stream_enabled', streamToggle.checked ? 'true' : 'false');
    }});
    const apiDetailOverlay = document.getElementById('apiDetailOverlay');
    const closeApiDetailBtn = document.getElementById('closeApiDetailBtn');
    if (closeApiDetailBtn) {{
      closeApiDetailBtn.addEventListener('click', closeApiDetail);
    }}
    if (apiDetailOverlay) {{
      apiDetailOverlay.addEventListener('click', (event) => {{
        if (event.target === apiDetailOverlay) {{
          closeApiDetail();
        }}
      }});
    }}
    renderApiDocs();
    refreshAll();
    setInterval(refreshStatus, 5000);
    setInterval(refreshLogs, 10000);
  </script>
</body>
</html>"""