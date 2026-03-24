"""
SMART SEARCH — main pipeline orchestrator.

Pipeline: crawl → parse → chunk → embed → FAISS index → SQLite store
"""

import sys
from pathlib import Path

from ingestion.pdf_parser import parse_document
from chunking.chunker import chunk_text
from embedding.gemini_embedder import embed_texts
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, insert_chunk, clear_document


# =========================
# CONFIG
# =========================

FOLDER = "/Users/deepandee/Desktop/od_alms"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
INDEX_PATH = "index.faiss"
DB_PATH = "metadata.db"


# =========================
# CRAWL
# =========================

def crawl_directory(folder_path: str) -> list[dict]:
    """Find all supported files in a directory."""

    files = []
    for path in Path(folder_path).rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append({
                "filename": path.name,
                "path": str(path),
                "type": path.suffix.lower(),
            })
    return files


# =========================
# PIPELINE
# =========================

def run_pipeline(folder: str):
    """Full indexing pipeline: crawl → parse → chunk → embed → store."""

    # Initialize stores
    conn = init_db(DB_PATH)
    faiss_idx = FaissIndex()
    faiss_idx.load(INDEX_PATH)  # load existing index if available

    # Crawl
    files = crawl_directory(folder)
    print(f"Found {len(files)} files\n")

    all_chunks = []       # (doc_name, doc_path, chunk_index, chunk_text)
    all_texts = []        # just the text for embedding

    for file_meta in files:
        file_path = file_meta["path"]
        filename = file_meta["filename"]

        print(f"Processing: {filename}")

        # Parse
        result = parse_document(file_path)
        if not result["success"]:
            print(f"  ✗ Extraction failed: {result['error']}")
            continue

        # Chunk
        chunks = chunk_text(result["text"])
        print(f"  ✓ {len(chunks)} chunks")

        # Clear old data for this document
        clear_document(conn, file_path)

        for i, chunk in enumerate(chunks):
            all_chunks.append((filename, file_path, i, chunk))
            all_texts.append(chunk)

    if not all_texts:
        print("\nNo text to embed.")
        return

    # Embed all chunks in one batch
    print(f"\nEmbedding {len(all_texts)} chunks...")
    embeddings = embed_texts(all_texts)
    print(f"  ✓ {len(embeddings)} embeddings ({len(embeddings[0])} dimensions)")

    # Store in FAISS and SQLite
    vector_ids = faiss_idx.add(embeddings)

    for vid, (doc_name, doc_path, chunk_idx, chunk) in zip(vector_ids, all_chunks):
        insert_chunk(conn, vid, doc_name, doc_path, chunk_idx, chunk)

    # Save FAISS index to disk
    faiss_idx.save(INDEX_PATH)

    print(f"\n{'='*50}")
    print(f"Indexing complete!")
    print(f"  FAISS vectors: {faiss_idx.total_vectors}")
    print(f"  SQLite DB:     {DB_PATH}")
    print(f"  FAISS index:   {INDEX_PATH}")


if __name__ == "__main__":
    folder_to_index = sys.argv[1] if len(sys.argv) > 1 else FOLDER
    run_pipeline(folder_to_index)