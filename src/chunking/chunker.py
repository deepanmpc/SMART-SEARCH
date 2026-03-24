"""
Text chunker — recursive character splitting with normalization.
"""

import re
from typing import List


def normalize_text(text: str) -> str:
    """
    Clean raw extracted text before chunking.

    Fixes:
    - Hyphenated line-breaks  ("detec-\\ntion" → "detection")
    - Tabs / non-breaking spaces → regular space
    - Soft-wrap newlines → space (preserves paragraph breaks)
    - Multiple blank lines → single blank line
    - Page marker noise
    """

    text = re.sub(r"-\n(\S)", r"\1", text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"-{2,}\s*Page\s*\d+\s*-{2,}", "", text, flags=re.IGNORECASE)

    return text.strip()


def chunk_text(text: str, chunk_size: int = 120, overlap: int = 30) -> List[str]:
    """
    Recursive character chunker for semantic search.

    Strategy (coarsest → finest):
      1. Paragraph breaks (double newlines)
      2. Sentence endings (. ? !)
      3. Sliding-window over words (fallback)

    Chunks smaller than 30 characters are dropped.
    """

    text = normalize_text(text)

    def _word_count(s: str) -> int:
        return len(s.split())

    def _sliding_window(t: str) -> List[str]:
        words = t.split()
        result = []
        start = 0
        while start < len(words):
            chunk = " ".join(words[start : start + chunk_size])
            if len(chunk.strip()) > 30:
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
            part_words = _word_count(part)

            if part_words > chunk_size:
                if current:
                    merged = " ".join(current)
                    if len(merged.strip()) > 30:
                        chunks.append(merged)
                    current, current_words = [], 0
                chunks.extend(_split_and_merge(part, rest))
                continue

            if current_words + part_words > chunk_size and current:
                merged = " ".join(current)
                if len(merged.strip()) > 30:
                    chunks.append(merged)
                overlap_words = " ".join(current).split()[-overlap:]
                current = overlap_words + [part]
                current_words = len(current)
            else:
                current.append(part)
                current_words += part_words

        if current:
            merged = " ".join(current)
            if len(merged.strip()) > 30:
                chunks.append(merged)

        return chunks

    separators = [
        r"\n\n+",
        r"(?<=[.?!])\s+",
    ]

    return _split_and_merge(text, separators)
