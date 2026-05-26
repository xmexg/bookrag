from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator, Sequence

import requests


@dataclass
class SiliconFlowClient:
    api_root: str
    token: str
    chat_model: str
    embedding_model: str
    reranking_model: str
    proxy: str | None
    timeout: int

    def __post_init__(self) -> None:
        self.session = requests.Session()
        if self.proxy:
            self.session.proxies.update({"http": self.proxy, "https": self.proxy})

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        payload = {
            "model": self.embedding_model,
            "input": list(texts),
            "encoding_format": "float",
        }
        data = self._post("/embeddings", payload)
        items = data.get("data", [])
        embeddings: list[list[float]] = []
        for item in items:
            vector = item.get("embedding")
            if vector is None:
                continue
            embeddings.append([float(value) for value in vector])
        if len(embeddings) != len(texts):
            raise RuntimeError("嵌入接口返回数量与输入不一致")
        return embeddings

    def chat(self, messages: Sequence[dict[str, str]], temperature: float = 0.2) -> str:
        payload = {
            "model": self.chat_model,
            "messages": list(messages),
            "temperature": temperature,
            "stream": False,
        }
        data = self._post("/chat/completions", payload)
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("聊天接口没有返回 choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("聊天接口返回内容格式异常")
        return content.strip()

    def chat_stream(self, messages: Sequence[dict[str, str]], temperature: float = 0.2) -> Iterator[str]:
        payload = {
            "model": self.chat_model,
            "messages": list(messages),
            "temperature": temperature,
            "stream": True,
        }
        response = self.session.post(
            f"{self.api_root.rstrip('/')}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=(10, max(self.timeout, 120)),
            stream=True,
        )
        try:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                if isinstance(raw_line, bytes):
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                else:
                    line = str(raw_line).strip()
                if not line.startswith("data:"):
                    continue
                data_text = line[5:].strip()
                if data_text == "[DONE]":
                    break
                try:
                    data = json.loads(data_text)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if isinstance(content, str) and content:
                    yield content
        finally:
            response.close()

    def rerank(self, query: str, documents: Sequence[str]) -> list[int]:
        payload = {
            "model": self.reranking_model,
            "query": query,
            "documents": list(documents),
        }
        data = self._post("/rerank", payload)
        if isinstance(data.get("results"), list):
            ranked: list[tuple[int, float]] = []
            for item in data["results"]:
                index = item.get("index")
                score = item.get("relevance_score", item.get("score", 0.0))
                if index is None:
                    continue
                ranked.append((int(index), float(score)))
            ranked.sort(key=lambda pair: pair[1], reverse=True)
            return [index for index, _ in ranked]
        if isinstance(data.get("data"), list):
            ranked = []
            for item in data["data"]:
                index = item.get("index")
                score = item.get("score", 0.0)
                if index is None:
                    continue
                ranked.append((int(index), float(score)))
            ranked.sort(key=lambda pair: pair[1], reverse=True)
            return [index for index, _ in ranked]
        return list(range(len(documents)))

    def _post(self, endpoint: str, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        response = self.session.post(
            f"{self.api_root.rstrip('/')}{endpoint}",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("接口返回了非 JSON 对象")
        return data
