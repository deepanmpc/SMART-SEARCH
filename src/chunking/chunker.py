"""
Text chunker — normalize + recursive splitting at 120 words, 30 word overlap.
"""

import re
from typing import List


def normalize_text(text: str) -> str:
    """Clean raw extracted text before chunking."""
    text = re.sub(r"-\n(\S)", r"\1", text)           # rejoin hyphenated line breaks
    text = re.sub(r"[ \t\xa0]+", " ", text)           # collapse whitespace
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)      # join soft-wrap newlines
    text = re.sub(r"\n{3,}", "\n\n", text)            # collapse excess blank lines
    text = re.sub(r"-{2,}\s*Page\s*\d+\s*-{2,}", "", text, flags=re.IGNORECASE)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 100, overlap: int = 25) -> List[str]:
    """
    Recursive character chunker.
    Strategy: paragraph breaks → sentence endings → sliding window.
    Returns ~120-word chunks with 30-word overlap.
    """
    text = normalize_text(text)

    def _sliding_window(t: str) -> List[str]:
        words = t.split()
        result = []
        start = 0
        while start < len(words):
            chunk = " ".join(words[start:start + chunk_size])
            if len(chunk.strip()) > 5:
                result.append(chunk)
            start += chunk_size - overlap
        return result

    def _split_and_merge(t: str, separators: List[str]) -> List[str]:
        if not separators:
            return _sliding_window(t)

        sep, *rest = separators
        parts = [p.strip() for p in re.split(sep, t) if p.strip()]

        if len(parts) <= 1:
            return _split_and_merge(t, rest)

        chunks: List[str] = []
        current: List[str] = []
        current_words = 0

        for part in parts:
            pw = len(part.split())

            if pw > chunk_size:
                if current:
                    merged = " ".join(current)
                    if len(merged.strip()) > 5:
                        chunks.append(merged)
                    current, current_words = [], 0
                chunks.extend(_split_and_merge(part, rest))
                continue

            if current_words + pw > chunk_size and current:
                merged = " ".join(current)
                if len(merged.strip()) > 5:
                    chunks.append(merged)
                overlap_words = " ".join(current).split()[-overlap:]
                current = overlap_words + [part]
                current_words = len(current)
            else:
                current.append(part)
                current_words += pw

        if current:
            merged = " ".join(current)
            if len(merged.strip()) > 5:
                chunks.append(merged)

        return chunks

    return _split_and_merge(text, [r"\n\n+", r"(?<=[.?!])\s+"])
