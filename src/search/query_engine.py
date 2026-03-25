"""
Semantic search — embed query → FAISS search → return results with metadata.
"""

from typing import List, Dict, Any

from embedding.gemini_embedder import embed_query
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, get_by_vector_ids, search_filenames


def search(query: str, top_k: int = 5, index_path: str = "index.faiss", db_path: str = "metadata.db") -> List[Dict[str, Any]]:
    """Find the most relevant chunks using both semantics (FAISS) and filename (SQL)."""
    conn = init_db(db_path)
    
    # 1. Filename match (Exact/Partial)
    sql_results = search_filenames(conn, query, limit=top_k)
    for r in sql_results:
        # Give a perfect score to exact string matches in filename
        r["score"] = 1.1  # Special "super score" for direct filename hits
    
    # 2. Semantic match
    query_vector = embed_query(query)
    faiss_idx = FaissIndex(dimension=len(query_vector))
    semantic_results = []
    if faiss_idx.load(index_path):
        f_hits = faiss_idx.search(query_vector, top_k=top_k * 2)
        if f_hits:
            vector_ids = [vid for vid, _ in f_hits]
            scores = {vid: score for vid, score in f_hits}
            semantic_results = get_by_vector_ids(conn, vector_ids)
            for r in semantic_results:
                r["score"] = scores.get(r["vector_id"], 0.0)

    # 3. Merge & Deduplicate
    seen_paths = set()
    merged = []
    # Filename hits first
    for r in sql_results:
        if r["document_path"] not in seen_paths:
            merged.append(r)
            seen_paths.add(r["document_path"])
    
    # Then semantic hits
    for r in semantic_results:
        if r["document_path"] not in seen_paths:
            merged.append(r)
            seen_paths.add(r["document_path"])
            
    # Sort merged list by score
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:top_k]


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "CNN object detection"
    print(f"Searching for: \"{q}\"\n")
    for r in search(q):
        print(f"[{r['score']:.3f}] {r['file_type']:6s}  {r['document_name']}")
        if r.get("chunk_text"):
            print(f"        {r['chunk_text'][:120]}")
        print()
