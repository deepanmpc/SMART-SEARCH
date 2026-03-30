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
DEFAULT_DIMENSION = 768


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client


def embed_unit(unit: dict, max_retries=3) -> list[float] | None:
    """
    Embed a single unit (text string or raw bytes) with dimensionality scaling.
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
                config=types.EmbedContentConfig(output_dimensionality=DEFAULT_DIMENSION)
            )
            return result.embeddings[0].values
        except Exception as e:
            if _handle_api_error(e, attempt, max_retries): continue
            print(f"  Embedding failed: {e}")
            return None
    return None

def embed_batch(units: list[dict], max_retries=3) -> list[list[float]]:
    """
    Embed multiple units in a single batch request using dimensionality scaling.
    """
    if not units: return []
    for attempt in range(max_retries):
        try:
            parts = []
            for u in units:
                if u["type"] == "text": parts.append(u["data"])
                else: parts.append(types.Part.from_bytes(data=u["data"], mime_type=u["mime_type"]))

            result = _get_client().models.embed_content(
                model=EMBEDDING_MODEL,
                contents=parts,
                config=types.EmbedContentConfig(output_dimensionality=DEFAULT_DIMENSION)
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            if _handle_api_error(e, attempt, max_retries): continue
            print(f"  Batch embedding failed: {e}")
            return []
    return []

def embed_query(query: str, max_retries=3) -> list[float]:
    """Embed a single query string with dimensionality scaling."""
    for attempt in range(max_retries):
        try:
            result = _get_client().models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[query],
                config=types.EmbedContentConfig(output_dimensionality=DEFAULT_DIMENSION)
            )
            return result.embeddings[0].values
        except Exception as e:
            if _handle_api_error(e, attempt, max_retries): continue
            raise e
    raise RuntimeError(f"Embedding query failed after {max_retries} attempts.")

def _handle_api_error(e: Exception, attempt: int, max_retries: int) -> bool:
    """Helper to handle retries for common API errors."""
    err_str = str(e).lower()
    if any(code in err_str for code in ["429", "quota", "rate limit", "503"]):
        if attempt < max_retries - 1:
            sleep_time = (attempt + 1) * 5
            print(f"  [API limit hit, retrying in {sleep_time}s...]")
            time.sleep(sleep_time)
            return True
    return False


def make_file_id(path: str, chunk_index: int) -> str:
    """Stable unique ID for a file chunk."""
    return hashlib.md5(f"{path}::{chunk_index}".encode()).hexdigest()
