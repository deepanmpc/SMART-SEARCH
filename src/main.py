"""
SMART SEARCH — main pipeline orchestrator.

Pipeline: crawl → route → embed → FAISS index → SQLite metadata
"""

import sys
from pathlib import Path

from crawler import crawl_directory
from ingestion.pdf_parser import prepare_for_embedding
from embedding.gemini_embedder import embed_unit, make_file_id
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, insert_chunk, clear_document

FOLDER = "/Users/deepandee/Desktop/od_alms"
INDEX_PATH = "index.faiss"
DB_PATH = "metadata.db"


def run_pipeline(folder: str):
    conn = init_db(DB_PATH)
    faiss_idx = FaissIndex()
    faiss_idx.load(INDEX_PATH)

    files = crawl_directory(folder)
    print(f"Found {len(files)} files\n")

    for file_meta in files:
        path = file_meta["path"]
        print(f"Processing: {file_meta['filename']}  [{file_meta['type']}]")

        units = prepare_for_embedding(file_meta)
        if not units:
            print(f"  ✗ Skipped (no embeddable units)")
            continue

        clear_document(conn, path)

        embedded = 0
        for i, unit in enumerate(units):
            embedding = embed_unit(unit)
            if embedding is None:
                continue

            # Update FAISS dimension on first embedding
            if faiss_idx.total_vectors == 0 and faiss_idx.dimension != len(embedding):
                faiss_idx = FaissIndex(dimension=len(embedding))

            vector_ids = faiss_idx.add([embedding])
            file_id = make_file_id(path, i)
            chunk_text = unit["data"] if unit["type"] == "text" else ""
            insert_chunk(conn, vector_ids[0], file_id, file_meta, i, chunk_text)
            embedded += 1

        print(f"  ✓ Indexed {embedded}/{len(units)} chunk(s)")

    faiss_idx.save(INDEX_PATH)

    print(f"\n{'='*50}")
    print(f"Indexing complete!")
    print(f"  FAISS vectors: {faiss_idx.total_vectors}")
    print(f"  SQLite DB:     {DB_PATH}")
    print(f"  FAISS index:   {INDEX_PATH}")


if __name__ == "__main__":
    folder_to_index = sys.argv[1] if len(sys.argv) > 1 else FOLDER
    run_pipeline(folder_to_index)