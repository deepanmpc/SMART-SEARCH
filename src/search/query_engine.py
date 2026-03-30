"""
Semantic search — embed query → FAISS search → return results with metadata.
"""

from typing import List, Dict, Any

from embedding.gemini_embedder import embed_query
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, get_by_vector_ids, search_filenames, get_all_chunks
from rank_bm25 import BM25Okapi

from pathlib import Path
import os

ROOT = Path(__file__).parent.parent.parent
DATA_DIR_ENV = os.environ.get("SMART_SEARCH_DATA_DIR")
if DATA_DIR_ENV:
    try:
        DATA_ROOT = Path(DATA_DIR_ENV).expanduser().resolve()
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        DATA_ROOT = ROOT
else:
    DATA_ROOT = ROOT
DATA_ROOT.mkdir(parents=True, exist_ok=True)
DEFAULT_INDEX = str(DATA_ROOT / "index.faiss")
DEFAULT_DB = str(DATA_ROOT / "metadata.db")

def tokenize(text: str) -> List[str]:
    return text.lower().split()

def search(query: str, top_k: int = 5, index_path: str = DEFAULT_INDEX, db_path: str = DEFAULT_DB) -> List[Dict[str, Any]]:
    """Find unique files using hybrid search (SQL filename + FAISS semantic + BM25 keyword)."""
    conn = init_db(db_path)
    try:
        # We will use a dict to keep the 'best' chunk for each unique document path
        best_results: Dict[str, Dict[str, Any]] = {}
        query_lower = query.lower()

        # 1. SQL Filename Match (Highest priority)
        sql_hits = search_filenames(conn, query, limit=top_k * 2)
        for r in sql_hits:
            path = r["document_path"]
            r["score"] = 0.85 # High base bonus for filename match
            if query_lower == r["document_name"].lower().split(".")[0]:
                r["score"] = 0.95
            best_results[path] = r

        # 2. Semantic FAISS Match
        query_vector = embed_query(query)
        faiss_idx = FaissIndex(dimension=len(query_vector))
        vector_hits = {}
        if faiss_idx.load(index_path):
            f_hits = faiss_idx.search(query_vector, top_k=top_k * 20)
            if f_hits:
                vector_hits = {vid: score for vid, score in f_hits}

        # 3. BM25 Keyword Match
        all_chunks = get_all_chunks(conn)
        if all_chunks:
            corpus = [tokenize(c["chunk_text"] or "") for c in all_chunks]
            bm25 = BM25Okapi(corpus)
            bm25_scores = bm25.get_scores(tokenize(query))
            
            # Max-normalize BM25 scores
            max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 else 0
            
            # 4. Combine Scores
            # We need to map vector scores and bm25 scores to chunks
            combined_chunk_scores = {}
            for i, chunk in enumerate(all_chunks):
                vid = chunk["vector_id"]
                v_score = vector_hits.get(vid, 0.0)
                b_score = bm25_scores[i] / max_bm25 if max_bm25 > 0 else 0
                
                # Weighted hybrid score: 60% Vector, 40% BM25
                hybrid_score = (0.6 * v_score) + (0.4 * b_score)
                
                if hybrid_score > 0:
                    combined_chunk_scores[vid] = hybrid_score

            # 5. Get Metadata for top combined chunks
            if combined_chunk_scores:
                top_vids = sorted(combined_chunk_scores.keys(), key=lambda x: combined_chunk_scores[x], reverse=True)[:top_k * 5]
                semantic_rows = get_by_vector_ids(conn, top_vids)
                for r in semantic_rows:
                    path = r["document_path"]
                    score = combined_chunk_scores.get(r["vector_id"], 0.0)
                    
                    # Boost if query is in filename but SQL query missed it
                    if query_lower in r["document_name"].lower():
                        score = min(1.0, score + 0.2)
                    
                    if path not in best_results or score > best_results[path]["score"]:
                        r["score"] = score
                        best_results[path] = r

        # 6. Sort and limit
        final_list = list(best_results.values())
        final_list.sort(key=lambda x: x["score"], reverse=True)
        return final_list[:top_k]
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "CNN object detection"
    print(f"Searching for: \"{q}\"\n")
    for r in search(q):
        print(f"[{r['score']:.3f}] {r['file_type']:6s}  {r['document_name']}")
        if r.get("chunk_text"):
            print(f"        {r['chunk_text'][:120]}")
        print()
