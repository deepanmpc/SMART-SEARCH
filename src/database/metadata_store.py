"""
SQLite metadata store — maps vector IDs to file metadata.
"""

import sqlite3
from typing import List, Dict, Any

DB_PATH = "metadata.db"


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            vector_id INTEGER PRIMARY KEY,
            file_id TEXT,
            document_name TEXT,
            document_path TEXT,
            file_type TEXT,
            chunk_index INTEGER,
            chunk_text TEXT
        )
    """)
    conn.commit()
    return conn


def insert_chunk(conn, vector_id: int, file_id: str, file_meta: dict, chunk_index: int, chunk_text: str = ""):
    conn.execute("""
        INSERT OR REPLACE INTO chunks
            (vector_id, file_id, document_name, document_path, file_type, chunk_index, chunk_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (vector_id, file_id, file_meta["filename"], file_meta["path"],
          file_meta["type"], chunk_index, chunk_text))
    conn.commit()


def get_by_vector_ids(conn, vector_ids: List[int]) -> List[Dict[str, Any]]:
    if not vector_ids:
        return []
    placeholders = ",".join("?" for _ in vector_ids)
    rows = conn.execute(
        f"SELECT * FROM chunks WHERE vector_id IN ({placeholders})", vector_ids
    ).fetchall()
    return [dict(row) for row in rows]


def clear_document(conn, document_path: str):
    conn.execute("DELETE FROM chunks WHERE document_path = ?", (document_path,))
    conn.commit()
