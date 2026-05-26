from __future__ import annotations

from dataclasses import dataclass

from .models import SplitChunk


def normalize_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in cleaned.split("\n")]
    return "\n".join(lines).strip()


def split_text(text: str, chunk_size: int, overlap: int) -> list[SplitChunk]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []

    if len(cleaned) <= chunk_size:
        return [SplitChunk(chunk_index=0, content=cleaned, start_char=0, end_char=len(cleaned))]

    chunks: list[SplitChunk] = []
    start = 0
    chunk_index = 0
    text_length = len(cleaned)

    while start < text_length:
        end = min(text_length, start + chunk_size)
        if end < text_length:
            paragraph_cut = cleaned.rfind("\n\n", start, end)
            line_cut = cleaned.rfind("\n", start, end)
            best_cut = max(paragraph_cut, line_cut)
            if best_cut > start + max(120, chunk_size // 2):
                end = best_cut

        snippet = cleaned[start:end].strip()
        if snippet:
            chunks.append(SplitChunk(chunk_index=chunk_index, content=snippet, start_char=start, end_char=end))
            chunk_index += 1

        if end >= text_length:
            break

        next_start = end - overlap if overlap > 0 else end
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks
