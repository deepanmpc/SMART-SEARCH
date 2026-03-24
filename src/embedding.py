"""
Embedding pipeline using Gemini Embedding 2.

Reads text chunks from the local SQLite database,
generates embeddings via the Gemini API, and stores
the vectors back into the database.

Usage:
    python embedding.py              # embed all un-embedded chunks
    python embedding.py --force      # re-embed everything
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

# Load .env file from the same directory as this script
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

from google import genai

from FileName import init_db, update_embedding


# =========================
# CONFIG
# =========================

MODEL = "gemini-embedding-2-preview"
BATCH_SIZE = 100   # Gemini allows up to 100 texts per embed call


# =========================
# EMBED
# =========================

def get_unembedded_chunks(conn, force: bool = False):
    """Fetch chunks that still need embeddings."""

    if force:
        query = "SELECT id, content FROM files"
    else:
        query = "SELECT id, content FROM files WHERE embedding IS NULL"

    return conn.execute(query).fetchall()


def embed_chunks(chunks: list[str], client) -> list[list[float]]:
    """Call Gemini Embedding 2 for a batch of text chunks."""

    result = client.models.embed_content(
        model=MODEL,
        contents=chunks,
    )

    return [e.values for e in result.embeddings]


def run_embedding(force: bool = False):
    """Main pipeline: read chunks → embed → store."""

    conn = init_db()
    client = genai.Client()

    rows = get_unembedded_chunks(conn, force=force)

    if not rows:
        print("All chunks are already embedded.")
        return

    print(f"Embedding {len(rows)} chunks using {MODEL}...")

    # Process in batches
    for i in range(0, len(rows), BATCH_SIZE):

        batch = rows[i : i + BATCH_SIZE]
        ids = [row[0] for row in batch]
        texts = [row[1] for row in batch]

        embeddings = embed_chunks(texts, client)

        for row_id, embedding in zip(ids, embeddings):
            update_embedding(conn, row_id, embedding)

        print(f"  Batch {i // BATCH_SIZE + 1}: embedded {len(batch)} chunks ({len(embeddings[0])} dimensions)")

    print("Embedding complete.")


# =========================
# CLI
# =========================

if __name__ == "__main__":
    force = "--force" in sys.argv
    run_embedding(force=force)