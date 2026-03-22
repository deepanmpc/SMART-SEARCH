import sqlite3

def init_db():
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE,
        filename TEXT,
        content TEXT,
        type TEXT,
        modified REAL
    )
    """)

    conn.commit()
    return conn

def insert_file(conn, file_data):
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO files (
        path, filename, content, type, modified
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        file_data.get("path"),
        file_data.get("filename"),
        file_data.get("content", ""),
        file_data.get("type"),
        file_data.get("modified"),
    ))

    conn.commit()