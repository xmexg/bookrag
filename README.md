# 说明
一个垃圾项目，同学的毕设要有RAG，以此帮他毕业

# 图书RAG检索与并发对话知识库

这是一个基于 Python + SQLite + FAISS + 硅基流动的本地图书 RAG 服务，支持：

- 目录周期性扫描
- 新文件增量入库
- 文件内容哈希去重
- 同名不同 hash 视为修改
- 不同名同 hash 视为改名
- SQLite 持久化
- FAISS 向量检索
- 多会话对话历史
- FastAPI 接口，支持全量 CORS
- 检索答案附带书名、文件名和片段来源

## 启动

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动服务

```bash
python main.py
```

默认会读取根目录下的 `.env`。
服务会监听 `0.0.0.0:8092`，浏览器可直接访问 `http://127.0.0.1:8092` 或局域网 IP。

## 主要接口

- `GET /health`
- `POST /scan`
- `POST /reindex`
- `POST /chat`
- `GET /documents`
- `GET /books`
- `GET /books/content?path=...`
- `GET /conversations`
- `GET /conversations/{conversation_id}`
- `GET /logs`

## 注意

- 默认会优先使用 FAISS；如果本机环境暂时没有安装 FAISS，代码会退回到纯 NumPy 索引实现，功能仍可用，但建议最终还是安装 FAISS。
- 如果要处理 PDF 或 DOCX，请安装对应依赖。
