"""
SQLite metadata store — maps vector IDs to document metadata.
"""

import sqlite3
from typing import List, Dict, Any, Optional


DB_PATH = "metadata.db"


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Create the metadata database and chunks table."""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        vector_id INTEGER PRIMARY KEY,
        document_name TEXT,
        document_path TEXT,
        chunk_index INTEGER,
        chunk_text TEXT,
        page_number INTEGER
    )
    """)

    conn.commit()
    return conn


def insert_chunk(
    conn: sqlite3.Connection,
    vector_id: int,
    document_name: str,
    document_path: str,
    chunk_index: int,
    chunk_text: str,
    page_number: int = 0,
):
    """Insert a single chunk's metadata."""

    conn.execute(
        """
        INSERT OR REPLACE INTO chunks
            (vector_id, document_name, document_path, chunk_index, chunk_text, page_number)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (vector_id, document_name, document_path, chunk_index, chunk_text, page_number),
    )
    conn.commit()


def get_by_vector_ids(conn: sqlite3.Connection, vector_ids: List[int]) -> List[Dict[str, Any]]:
    """Fetch metadata for a list of vector IDs."""

    if not vector_ids:
        return []

    placeholders = ",".join("?" for _ in vector_ids)
    rows = conn.execute(
        f"SELECT * FROM chunks WHERE vector_id IN ({placeholders})",
        vector_ids,
    ).fetchall()

    return [dict(row) for row in rows]


def clear_document(conn: sqlite3.Connection, document_path: str):
    """Remove all chunks for a given document (before re-indexing)."""

    conn.execute("DELETE FROM chunks WHERE document_path = ?", (document_path,))
    conn.commit()


def get_all_vector_ids(conn: sqlite3.Connection) -> List[int]:
    """Get all existing vector IDs."""

    rows = conn.execute("SELECT vector_id FROM chunks").fetchall()
    return [row[0] for row in rows]
