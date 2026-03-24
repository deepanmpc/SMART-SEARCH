"""
Gemini Embedding 2 client — text embedding via Google GenAI.
"""

import os
from pathlib import Path
from typing import List

# Load .env from src/ directory
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

from google import genai

MODEL = "gemini-embedding-2-preview"
BATCH_SIZE = 100  # Gemini allows up to 100 texts per call

# Shared client instance
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts using Gemini Embedding 2.
    Handles batching automatically.

    Returns a list of embedding vectors (list of floats).
    """

    client = _get_client()
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]

        result = client.models.embed_content(
            model=MODEL,
            contents=batch,
        )

        all_embeddings.extend([e.values for e in result.embeddings])

    return all_embeddings


def embed_query(query: str) -> List[float]:
    """Embed a single query string. Returns one embedding vector."""

    result = _get_client().models.embed_content(
        model=MODEL,
        contents=[query],
    )

    return result.embeddings[0].values
