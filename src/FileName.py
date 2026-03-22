import sqlite3

def init_db():
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        name TEXT,
        path TEXT UNIQUE,
        abs_path TEXT,
        content TEXT,
        type TEXT,
        size INTEGER,
        modified REAL,
        created REAL,
        accessed REAL,
        parent TEXT
    )
    """)

    conn.commit()
    return conn

def insert_file(conn, file_data):
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO files (
        name, path, abs_path, content, type, size, modified, created, accessed, parent
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_data.get("name"),
        file_data.get("path"),
        file_data.get("abs_path"),
        file_data.get("content", ""), # Default empty if not extracted yet
        file_data.get("type"),
        file_data.get("size"),
        file_data.get("modified"),
        file_data.get("created"),
        file_data.get("accessed"),
        file_data.get("parent"),
    ))

    conn.commit()