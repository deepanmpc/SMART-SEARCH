"""
Semantic search — embed query → FAISS search → return results with metadata.
"""

from typing import List, Dict, Any

from embedding.gemini_embedder import embed_query
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, get_by_vector_ids


def search(query: str, top_k: int = 5, index_path: str = "index.faiss", db_path: str = "metadata.db") -> List[Dict[str, Any]]:
    """Find the most relevant chunks for a query."""

    query_vector = embed_query(query)

    faiss_idx = FaissIndex(dimension=len(query_vector))
    if not faiss_idx.load(index_path):
        print("Error: No FAISS index found. Run main.py first.")
        return []

    results = faiss_idx.search(query_vector, top_k=top_k)
    if not results:
        return []

    vector_ids = [vid for vid, _ in results]
    scores = {vid: score for vid, score in results}

    conn = init_db(db_path)
    metadata = get_by_vector_ids(conn, vector_ids)

    for row in metadata:
        row["score"] = scores.get(row["vector_id"], 0.0)

    metadata.sort(key=lambda x: x["score"], reverse=True)
    return metadata


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "CNN object detection"
    print(f"Searching for: \"{q}\"\n")
    for r in search(q):
        print(f"[{r['score']:.3f}] {r['file_type']:6s}  {r['document_name']}")
        if r.get("chunk_text"):
            print(f"        {r['chunk_text'][:120]}")
        print()
