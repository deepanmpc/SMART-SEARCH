"""
Gemini multimodal embedding — supports text, images, audio, video, PDF bytes.
"""

import os
import hashlib
from pathlib import Path

# Load .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

from google import genai
from google.genai import types

_client = None
EMBEDDING_MODEL = "gemini-embedding-2-preview"


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def embed_unit(unit: dict) -> list[float] | None:
    """
    Embed a single unit (text string or raw bytes).
    Returns a flat list of floats, or None on failure.
    """
    try:
        if unit["type"] == "text":
            part = unit["data"]
        else:
            part = types.Part.from_bytes(data=unit["data"], mime_type=unit["mime_type"])

        result = _get_client().models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[part],
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"  Embedding failed: {e}")
        return None


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    result = _get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[query],
    )
    return result.embeddings[0].values


def make_file_id(path: str, chunk_index: int) -> str:
    """Stable unique ID for a file chunk."""
    return hashlib.md5(f"{path}::{chunk_index}".encode()).hexdigest()
