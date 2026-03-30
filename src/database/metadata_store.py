"""
SQLite metadata store — maps vector IDs to file metadata.
"""

import sqlite3
import os
from typing import List, Dict, Any

from pathlib import Path
_ROOT = Path(__file__).parent.parent.parent
_DATA_DIR_ENV = os.environ.get("SMART_SEARCH_DATA_DIR")
if _DATA_DIR_ENV:
    try:
        _DATA_ROOT = Path(_DATA_DIR_ENV).expanduser().resolve()
        _DATA_ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        _DATA_ROOT = _ROOT
else:
    _DATA_ROOT = _ROOT
_DATA_ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = str(_DATA_ROOT / "metadata.db")


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    
    # Performance pragmas
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=10000;")
    conn.execute("PRAGMA busy_timeout=30000;")
    
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            path TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    return conn

def add_watched_folder(conn, folder_path: str):
    conn.execute("INSERT OR IGNORE INTO folders (path) VALUES (?)", (folder_path,))
    conn.commit()

def remove_watched_folder(conn, folder_path: str):
    conn.execute("DELETE FROM folders WHERE path = ?", (folder_path,))
    conn.commit()

def get_all_watched_folders(conn) -> List[str]:
    rows = conn.execute("SELECT path FROM folders").fetchall()
    return [row["path"] for row in rows]


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


def get_all_chunks(conn) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT vector_id, chunk_text, document_path FROM chunks").fetchall()
    return [dict(row) for row in rows]

def clear_document(conn, document_path: str):
    conn.execute("DELETE FROM chunks WHERE document_path = ?", (document_path,))
    conn.commit()


def is_document_indexed(conn, document_path: str) -> bool:
    """Check if any chunks exist for the given document path."""
    row = conn.execute("SELECT 1 FROM chunks WHERE document_path = ? LIMIT 1", (document_path,)).fetchone()
    return row is not None

def search_filenames(conn, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """SQL-based filename search as a fallback/bonus."""
    # We use a distinct to get one representative chunk per matching file
    query_param = f"%{query}%"
    rows = conn.execute("""
        SELECT * FROM chunks 
        WHERE document_name LIKE ? 
        GROUP BY document_path
        LIMIT ?
    """, (query_param, limit)).fetchall()
    return [dict(row) for row in rows]
