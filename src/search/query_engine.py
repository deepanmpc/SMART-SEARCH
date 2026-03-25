"""
Semantic search — embed query → FAISS search → return results with metadata.
"""

from typing import List, Dict, Any

from embedding.gemini_embedder import embed_query
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, get_by_vector_ids, search_filenames


def search(query: str, top_k: int = 5, index_path: str = "index.faiss", db_path: str = "metadata.db") -> List[Dict[str, Any]]:
    """Find unique files using hybrid search (SQL filename + FAISS semantic)."""
    conn = init_db(db_path)
    
    # We will use a dict to keep the 'best' chunk for each unique document path
    best_results: Dict[str, Dict[str, Any]] = {}
    query_lower = query.lower()

    # 1. SQL Filename Match (Highest priority)
    sql_hits = search_filenames(conn, query, limit=top_k * 2)
    for r in sql_hits:
        path = r["document_path"]
        r["score"] = 1.2  # Base bonus for filename match
        # Extra bonus for exact filename match
        if query_lower == r["document_name"].lower().split(".")[0]:
            r["score"] = 1.5
        best_results[path] = r

    # 2. Semantic FAISS Match
    query_vector = embed_query(query)
    faiss_idx = FaissIndex(dimension=len(query_vector))
    if faiss_idx.load(index_path):
        f_hits = faiss_idx.search(query_vector, top_k=top_k * 10)
        if f_hits:
            vector_ids = [vid for vid, _ in f_hits]
            scores = {vid: score for vid, score in f_hits}
            semantic_rows = get_by_vector_ids(conn, vector_ids)
            for r in semantic_rows:
                path = r["document_path"]
                score = scores.get(r["vector_id"], 0.0)
                
                # Boost if query is in filename but SQL query missed it
                if query_lower in r["document_name"].lower():
                    score = min(1.0, score + 0.3)
                
                # Only keep this chunk if it's better than what we already have for this file
                if path not in best_results or score > best_results[path]["score"]:
                    r["score"] = score
                    best_results[path] = r

    # 3. Sort and limit
    final_list = list(best_results.values())
    final_list.sort(key=lambda x: x["score"], reverse=True)
    return final_list[:top_k]


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "CNN object detection"
    print(f"Searching for: \"{q}\"\n")
    for r in search(q):
        print(f"[{r['score']:.3f}] {r['file_type']:6s}  {r['document_name']}")
        if r.get("chunk_text"):
            print(f"        {r['chunk_text'][:120]}")
        print()
