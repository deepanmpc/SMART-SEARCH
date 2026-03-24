import sqlite3
import json

def init_db():
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        path TEXT,
        filename TEXT,
        chunk_index INTEGER,
        content TEXT,
        type TEXT,
        modified REAL,
        embedding TEXT
    )
    """)

    # Add embedding column to existing tables that don't have it
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN embedding TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.commit()
    return conn

def update_embedding(conn, row_id: int, embedding: list):
    """Store embedding vector as JSON text for a given row."""
    conn.cursor().execute(
        "UPDATE files SET embedding = ? WHERE id = ?",
        (json.dumps(embedding), row_id)
    )
    conn.commit()

def delete_file(conn, path: str):
    """Remove all existing chunks for a file before re-indexing it."""
    conn.cursor().execute("DELETE FROM files WHERE path = ?", (path,))
    conn.commit()

def insert_chunk(conn, file_data, chunk_index: int):
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO files (
        path, filename, chunk_index, content, type, modified
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        file_data.get("path"),
        file_data.get("filename"),
        chunk_index,
        file_data.get("content", ""),
        file_data.get("type"),
        file_data.get("modified"),
    ))

    conn.commit()

# Keep backwards-compatible alias
def insert_file(conn, file_data):
    insert_chunk(conn, file_data, chunk_index=file_data.get("chunk_index", 0))