from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np


try:  # pragma: no cover - optional dependency path
    import faiss  # type: ignore
except Exception:  # pragma: no cover - fallback is tested via normal Python execution
    faiss = None


class VectorIndex:
    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._dimension: int | None = None
        self._ids: np.ndarray | None = None
        self._vectors: np.ndarray | None = None
        self._faiss_index = None

    @property
    def is_faiss_available(self) -> bool:
        return faiss is not None

    def load(self) -> None:
        fallback_vectors = self.index_path.with_suffix(".vectors.npz")
        if fallback_vectors.exists():
            data = np.load(fallback_vectors, allow_pickle=False)
            self._ids = data["ids"].astype(np.int64)
            self._vectors = data["vectors"].astype(np.float32)
            if self._vectors.size:
                self._dimension = int(self._vectors.shape[1])
                if faiss is not None:
                    self._faiss_index = self._new_index(self._dimension)
                    self._faiss_index.add_with_ids(self._vectors, self._ids)

    def save(self) -> None:
        if self._ids is None or self._vectors is None:
            return
        np.savez_compressed(self.index_path.with_suffix(".vectors.npz"), ids=self._ids, vectors=self._vectors)

    def rebuild(self, chunk_ids: Sequence[int], embeddings: Sequence[bytes]) -> None:
        vectors = self._decode_embeddings(embeddings)
        ids = np.asarray(chunk_ids, dtype=np.int64)
        if vectors.size == 0:
            self._dimension = None
            self._ids = np.asarray([], dtype=np.int64)
            self._vectors = np.asarray([], dtype=np.float32).reshape(0, 0)
            self._faiss_index = None
            self.save()
            return

        self._dimension = int(vectors.shape[1])
        if faiss is not None:
            index = self._new_index(self._dimension)
            index.add_with_ids(vectors, ids)
            self._faiss_index = index
        else:
            self._faiss_index = None
        self._ids = ids
        self._vectors = vectors
        self.save()

    def add(self, chunk_ids: Sequence[int], embeddings: Sequence[bytes]) -> None:
        if not chunk_ids:
            return
        vectors = self._decode_embeddings(embeddings)
        ids = np.asarray(chunk_ids, dtype=np.int64)
        if vectors.size == 0:
            return

        self._dimension = int(vectors.shape[1])
        if faiss is not None:
            if self._faiss_index is None:
                self._faiss_index = self._new_index(self._dimension)
            self._faiss_index.add_with_ids(vectors, ids)
        else:
            self._faiss_index = None

        if self._ids is None or self._vectors is None or self._vectors.size == 0:
            self._ids = ids
            self._vectors = vectors
        else:
            self._ids = np.concatenate([self._ids, ids])
            self._vectors = np.vstack([self._vectors, vectors])
        self.save()

    def remove(self, chunk_ids: Sequence[int]) -> None:
        if not chunk_ids:
            return
        ids = np.asarray(chunk_ids, dtype=np.int64)
        if faiss is not None:
            if self._faiss_index is None:
                self._faiss_index = self._new_index(self._dimension or 0)
            selector = faiss.IDSelectorBatch(ids.size, faiss.swig_ptr(ids))
            self._faiss_index.remove_ids(selector)
        if self._ids is None or self._vectors is None or self._ids.size == 0:
            return
        keep_mask = ~np.isin(self._ids, ids)
        self._ids = self._ids[keep_mask]
        self._vectors = self._vectors[keep_mask]
        self.save()

    def search(self, query_embedding: Sequence[float] | np.ndarray, top_k: int) -> list[tuple[int, float]]:
        if top_k <= 0:
            return []
        vector = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        vector = self._normalize(vector)
        if vector.size == 0:
            return []

        if faiss is not None:
            if self._faiss_index is None or self._faiss_index.ntotal == 0:
                return []
            scores, ids = self._faiss_index.search(vector, top_k)
            results: list[tuple[int, float]] = []
            for chunk_id, score in zip(ids[0], scores[0]):
                if int(chunk_id) < 0:
                    continue
                results.append((int(chunk_id), float(score)))
            return results

        if self._ids is None or self._vectors is None or self._vectors.size == 0:
            return []
        scores = self._vectors @ vector.T
        scores = scores.reshape(-1)
        if scores.size == 0:
            return []
        order = np.argsort(-scores)[:top_k]
        return [(int(self._ids[idx]), float(scores[idx])) for idx in order]

    def has_index(self) -> bool:
        if faiss is not None:
            return self._faiss_index is not None and self._faiss_index.ntotal > 0
        return self._vectors is not None and self._vectors.size > 0

    def _new_index(self, dimension: int):
        if faiss is None:
            return None
        base = faiss.IndexFlatIP(dimension)
        return faiss.IndexIDMap2(base)

    def _decode_embeddings(self, embeddings: Sequence[bytes]) -> np.ndarray:
        vectors = [np.frombuffer(blob, dtype=np.float32) for blob in embeddings]
        if not vectors:
            return np.asarray([], dtype=np.float32).reshape(0, 0)
        matrix = np.vstack(vectors).astype(np.float32)
        if self._dimension is not None and matrix.shape[1] != self._dimension:
            raise ValueError("向量维度不一致，可能是嵌入模型发生了变化")
        if matrix.ndim != 2:
            raise ValueError("embedding 维度错误")
        matrix = self._normalize(matrix)
        return matrix

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        if matrix.size == 0:
            return matrix.astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (matrix / norms).astype(np.float32)
