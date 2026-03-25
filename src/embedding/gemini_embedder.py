"""
Gemini multimodal embedding — supports text, images, audio, video, PDF bytes.
"""

import os
import hashlib
import time
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


def embed_unit(unit: dict, max_retries=3) -> list[float] | None:
    """
    Embed a single unit (text string or raw bytes) with retry logic for API limits.
    Returns a flat list of floats, or None on failure.
    """
    for attempt in range(max_retries):
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
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "rate limit" in err_str or "503" in err_str:
                if attempt < max_retries - 1:
                    sleep_time = (attempt + 1) * 5
                    print(f"  [API limit hit, retrying in {sleep_time}s...]")
                    time.sleep(sleep_time)
                    continue
            print(f"  Embedding failed: {e}")
            return None
    return None


def embed_query(query: str, max_retries=3) -> list[float]:
    """Embed a single query string with retries."""
    for attempt in range(max_retries):
        try:
            result = _get_client().models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[query],
            )
            return result.embeddings[0].values
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "rate limit" in err_str or "503" in err_str:
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
            raise e
    raise RuntimeError(f"Embedding query failed after {max_retries} attempts.")


def make_file_id(path: str, chunk_index: int) -> str:
    """Stable unique ID for a file chunk."""
    return hashlib.md5(f"{path}::{chunk_index}".encode()).hexdigest()
