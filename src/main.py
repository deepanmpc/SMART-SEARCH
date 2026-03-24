"""
SMART SEARCH — main pipeline orchestrator.

Pipeline: crawl → parse → chunk (120 words) → embed → FAISS + SQLite
Each chunk = one row in SQLite + one vector in FAISS.
"""

import sys
from crawler import crawl_directory
from ingestion.pdf_parser import parse_document
from chunking.chunker import chunk_text
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

    total_chunks = 0

    for file_meta in files:
        path = file_meta["path"]
        filename = file_meta["filename"]
        print(f"Processing: {filename}")

        # 1. Parse → raw text
        result = parse_document(path)
        if not result["success"]:
            print(f"  ✗ {result['error']}")
            continue

        # 2. Chunk → 120-word segments
        chunks = chunk_text(result["text"])
        print(f"  → {len(chunks)} chunks")

        # 3. Clear old data
        clear_document(conn, path)

        # 4. Embed each chunk and store
        for i, chunk in enumerate(chunks):
            unit = {"type": "text", "data": chunk}
            embedding = embed_unit(unit)
            if embedding is None:
                continue

            if faiss_idx.total_vectors == 0 and faiss_idx.dimension != len(embedding):
                faiss_idx = FaissIndex(dimension=len(embedding))

            vector_ids = faiss_idx.add([embedding])
            file_id = make_file_id(path, i)
            insert_chunk(conn, vector_ids[0], file_id, file_meta, i, chunk)
            total_chunks += 1

        print(f"  ✓ {len(chunks)} chunks indexed")

    faiss_idx.save(INDEX_PATH)

    print(f"\n{'='*50}")
    print(f"Indexing complete!")
    print(f"  Total chunks: {total_chunks}")
    print(f"  FAISS vectors: {faiss_idx.total_vectors}")
    print(f"  SQLite DB:     {DB_PATH}")


if __name__ == "__main__":
    folder_to_index = sys.argv[1] if len(sys.argv) > 1 else FOLDER
    run_pipeline(folder_to_index)