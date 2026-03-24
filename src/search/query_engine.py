"""
Query engine — semantic search over indexed documents.

Pipeline: embed query → FAISS similarity search → fetch metadata → return results.
"""

from typing import List, Dict, Any

from embedding.gemini_embedder import embed_query
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, get_by_vector_ids


def search(query: str, top_k: int = 5, index_path: str = "index.faiss", db_path: str = "metadata.db") -> List[Dict[str, Any]]:
    """
    Semantic search: find the most relevant chunks for a query.

    Returns a list of dicts:
        [{"score": float, "vector_id": int, "document_name": str,
          "chunk_text": str, "chunk_index": int, "page_number": int}, ...]
    """

    # 1. Embed the query
    query_vector = embed_query(query)

    # 2. Search FAISS
    faiss_idx = FaissIndex(dimension=len(query_vector))
    if not faiss_idx.load(index_path):
        print("Error: No FAISS index found. Run main.py first to build the index.")
        return []

    results = faiss_idx.search(query_vector, top_k=top_k)

    if not results:
        return []

    # 3. Fetch metadata from SQLite
    vector_ids = [vid for vid, _ in results]
    scores = {vid: score for vid, score in results}

    conn = init_db(db_path)
    metadata = get_by_vector_ids(conn, vector_ids)

    # 4. Merge scores with metadata and sort
    output = []
    for row in metadata:
        row["score"] = scores.get(row["vector_id"], 0.0)
        output.append(row)

    output.sort(key=lambda x: x["score"], reverse=True)

    return output


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m search.query_engine \"your search query\"")
        exit()

    query_text = " ".join(sys.argv[1:])
    print(f"Searching for: \"{query_text}\"\n")

    results = search(query_text)

    if not results:
        print("No results found.")
    else:
        for i, r in enumerate(results, 1):
            print(f"{'='*60}")
            print(f"Result {i} | Score: {r['score']:.4f}")
            print(f"Document: {r['document_name']} | Chunk: {r['chunk_index']}")
            print(f"{'-'*60}")
            print(r["chunk_text"][:300])
            print()
