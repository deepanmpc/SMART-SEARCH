import os
import mimetypes
import time
from pathlib import Path
from collections import Counter
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import local modules
from api_models import SearchRequest, SearchResponse, SearchResult, IndexRequest, IndexResponse, StatsResponse, AskRequest, AskResponse, IndexStatusResponse
from main import _crawl, _vector_count, INDEX_PATH, DB_PATH
from search.query_engine import search as semantic_search

from ingestion.document_parser import parse_document
from chunking.chunker import chunk_text
from embedding.gemini_embedder import embed_batch, make_file_id, _get_client
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, insert_chunk, clear_document, is_document_indexed

app = FastAPI(title="SMART SEARCH API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock subscription
CURRENT_PLAN = "Free"
PLAN_LIMITS = {
    "Free": 50000,
    "Plus": 500000,
    "Pro": 999999999
}

# Global progress state
INDEX_PROGRESS = {
    "is_indexing": False,
    "current_file": "",
    "total_files": 0,
    "processed_files": 0,
    "start_time": 0,
    "percentage": 0.0,
    "eta_seconds": 0.0
}

@app.get("/stats", response_model=StatsResponse)
def get_stats():
    total_vectors = _vector_count()
    limit = PLAN_LIMITS.get(CURRENT_PLAN, 50000)
    return StatsResponse(
        total_chunks=total_vectors,
        plan=CURRENT_PLAN,
        plan_limit=limit,
        usage_percent=round((total_vectors / limit) * 100, 2)
    )

@app.post("/search", response_model=SearchResponse)
def search_endpoint(req: SearchRequest):
    # Increase top_k internally to allow for filtering (e.g. 8 * 25 = 200)
    search_k = req.top_k * 25 if req.file_type and req.file_type != "all" else req.top_k
    
    results = semantic_search(req.query, top_k=search_k, index_path=INDEX_PATH, db_path=DB_PATH)
    
    # Mapping friendly categories to database types
    TYPE_MAP = {
        "text": ["text", "pdf", "docx", "pptx"],
        "image": ["image"],
        "video": ["video"],
        "audio": ["audio"]
    }
    
    out = []
    for r in results:
        r_type = r.get("file_type", "")
        
        # Apply filter
        if req.file_type and req.file_type != "all":
            allowed = TYPE_MAP.get(req.file_type.lower(), [req.file_type.lower()])
            if r_type not in allowed:
                continue
                
        out.append(SearchResult(
            document_name=r.get("document_name", ""),
            file_path=r.get("file_path", ""),
            file_type=r_type,
            chunk_text=r.get("chunk_text", ""),
            score=r.get("score", 0.0)
        ))
        
        # Stop if we reached top_k results
        if len(out) >= req.top_k:
            break
            
    return SearchResponse(results=out)

@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    # Mapping for filtering
    TYPE_MAP = {
        "text": ["text", "pdf", "docx", "pptx"],
        "image": ["image"],
        "video": ["video"],
        "audio": ["audio"]
    }
    
    # Increase k for filtering
    search_k = req.top_k * 3 if req.file_type and req.file_type != "all" else req.top_k
    
    # 1. Search for context
    results = semantic_search(req.question, top_k=search_k, index_path=INDEX_PATH, db_path=DB_PATH)
    
    # Filter results
    filtered_results = []
    for r in results:
        r_type = r.get("file_type", "")
        if req.file_type and req.file_type != "all":
            allowed = TYPE_MAP.get(req.file_type.lower(), [req.file_type.lower()])
            if r_type not in allowed:
                continue
        filtered_results.append(r)
        if len(filtered_results) >= req.top_k:
            break

    # 2. Build context
    context_parts = []
    sources = []
    for i, r in enumerate(filtered_results, 1):
        text = r.get("chunk_text", "")
        file_path = r.get("file_path", "Unknown")
        context_parts.append(f"[Source {i}: {file_path}]\n{text}\n")
        sources.append(SearchResult(
            document_name=r.get("document_name", ""),
            file_path=file_path,
            file_type=r.get("file_type", ""),
            chunk_text=text,
            score=r.get("score", 0.0)
        ))
    
    context_str = "\n".join(context_parts)
    prompt = f"""You are a helpful AI assistant. Answer the user's question using ONLY the context provided below. 
If the answer is not contained in the context, say "I don't have enough information in your indexed files to answer this."

Context:
{context_str}

Question:
{req.question}
"""
    
    # 3. Generate answer
    try:
        client = _get_client()
        # using the generic generator model
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        answer = response.text
    except Exception as e:
        answer = f"Error generating answer: {e}"

    return AskResponse(answer=answer, sources=sources)

@app.get("/index/status", response_model=IndexStatusResponse)
def get_index_status():
    global INDEX_PROGRESS
    if INDEX_PROGRESS["is_indexing"]:
        # Update ETA
        elapsed = time.time() - INDEX_PROGRESS["start_time"]
        if INDEX_PROGRESS["processed_files"] > 0:
            time_per_file = elapsed / INDEX_PROGRESS["processed_files"]
            remaining = INDEX_PROGRESS["total_files"] - INDEX_PROGRESS["processed_files"]
            INDEX_PROGRESS["eta_seconds"] = round(time_per_file * remaining, 1)
        
        INDEX_PROGRESS["percentage"] = round((INDEX_PROGRESS["processed_files"] / INDEX_PROGRESS["total_files"]) * 100, 1) if INDEX_PROGRESS["total_files"] > 0 else 0
        
    return IndexStatusResponse(**INDEX_PROGRESS)

def run_indexing(folder_path: str):
    global INDEX_PROGRESS
    import time as time_mod
    
    try:
        folder = os.path.expanduser(folder_path)
        all_found = _crawl(folder)
        if not all_found:
            INDEX_PROGRESS["is_indexing"] = False
            return
            
        INDEX_PROGRESS["total_files"] = len(all_found)
        INDEX_PROGRESS["processed_files"] = 0
        INDEX_PROGRESS["start_time"] = time_mod.time()
        INDEX_PROGRESS["is_indexing"] = True
        
        conn = init_db(DB_PATH)
        faiss_idx = FaissIndex()
        if Path(INDEX_PATH).exists():
            faiss_idx.load(INDEX_PATH)
        
        limit = PLAN_LIMITS.get(CURRENT_PLAN, 50000)
        total_chunks_added = 0
        from ingestion.media_parser import chunk_image, chunk_video

        for i, fm in enumerate(all_found):
            INDEX_PROGRESS["current_file"] = fm["filename"]
            INDEX_PROGRESS["processed_files"] = i
            
            # Check limit
            if (faiss_idx.total_vectors + total_chunks_added) >= limit:
                break
                
            if is_document_indexed(conn, fm["path"]):
                continue

            clear_document(conn, fm["path"])
            indexed = 0

            # Media / Text ingestion logic
            if fm["type"] in ("image", "audio", "video"):
                try:
                    media_chunks = []
                    if fm["type"] == "image":
                        with open(fm["path"], "rb") as bf: img_bytes = bf.read()
                        media_chunks = chunk_image(img_bytes)
                    elif fm["type"] == "video":
                        media_chunks = chunk_video(fm["path"])
                    elif fm["type"] == "audio":
                        with open(fm["path"], "rb") as bf: data = bf.read()
                        mime_type, _ = mimetypes.guess_type(fm["path"])
                        if not mime_type: mime_type = f"audio/{fm['ext'][1:]}"
                        media_chunks = [{"type": "audio", "data": data, "mime_type": mime_type, "suffix": "full"}]

                    if not media_chunks: continue

                    batch_size = 16
                    for b_idx in range(0, len(media_chunks), batch_size):
                        batch = media_chunks[b_idx : b_idx + batch_size]
                        units = []
                        for c in batch:
                            if fm["type"] == "audio": units.append({"type": "audio", "data": c["data"], "mime_type": c["mime_type"]})
                            else: units.append({"type": "image", "data": c["data"], "mime_type": "image/jpeg"})
                        
                        vecs = embed_batch(units) or []
                        for idx_in_batch, (c, vec) in enumerate(zip(batch, vecs)):
                            idx = b_idx + idx_in_batch
                            if vec is not None:
                                if faiss_idx.total_vectors == 0 and faiss_idx.dimension != len(vec):
                                    faiss_idx = FaissIndex(dimension=len(vec))
                                vector_ids = faiss_idx.add([vec])
                                file_id = make_file_id(fm["path"], idx)
                                desc = f"[{fm['type'].capitalize()}: {c.get('suffix', 'chunk')}]"
                                insert_chunk(conn, vector_ids[0], file_id, fm, idx, desc)
                                indexed += 1
                                total_chunks_added += 1
                except Exception as e:
                    print(f"Failed media {fm['path']}: {e}")
            else:
                try:
                    result = parse_document(fm["path"])
                    if not result["success"]: continue
                    chunks = chunk_text(result["text"])
                    if not chunks: continue

                    batch_size = 50 
                    for b_idx in range(0, len(chunks), batch_size):
                        batch = chunks[b_idx : b_idx + batch_size]
                        units = [{"type": "text", "data": c} for c in batch]
                        vecs = embed_batch(units) or []
                        for idx_in_batch, (chunk_text_content, vec) in enumerate(zip(batch, vecs)):
                            idx = b_idx + idx_in_batch
                            if vec is not None:
                                if faiss_idx.total_vectors == 0 and faiss_idx.dimension != len(vec):
                                    faiss_idx = FaissIndex(dimension=len(vec))
                                vector_ids = faiss_idx.add([vec])
                                file_id = make_file_id(fm["path"], idx)
                                insert_chunk(conn, vector_ids[0], file_id, fm, idx, chunk_text_content)
                                indexed += 1
                                total_chunks_added += 1
                except Exception as e:
                    print(f"Failed text {fm['path']}: {e}")

            # Yield CPU to the OS to prevent kernel_task CPU spikes
            time_mod.sleep(0.01)

        faiss_idx.save(INDEX_PATH)
        INDEX_PROGRESS["processed_files"] = INDEX_PROGRESS["total_files"]
        INDEX_PROGRESS["percentage"] = 100.0
        INDEX_PROGRESS["eta_seconds"] = 0.0
        time_mod.sleep(2)
        INDEX_PROGRESS["is_indexing"] = False
    except Exception as e:
        print(f"Error in background indexing: {e}")
        INDEX_PROGRESS["is_indexing"] = False

@app.post("/index", response_model=IndexResponse)
def index_endpoint(req: IndexRequest, background_tasks: BackgroundTasks):
    global INDEX_PROGRESS
    if INDEX_PROGRESS["is_indexing"]:
        return IndexResponse(success=False, message="Indexing already in progress", files_indexed=0, chunks_indexed=0)
    
    # Pre-check folder
    folder = os.path.expanduser(req.folder_path)
    if not Path(folder).exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {folder}")

    background_tasks.add_task(run_indexing, req.folder_path)
    return IndexResponse(success=True, message="Indexing started in background", files_indexed=0, chunks_indexed=0)

@app.delete("/index", response_model=IndexResponse)
def delete_index_endpoint():
    global INDEX_PROGRESS
    if INDEX_PROGRESS["is_indexing"]:
        raise HTTPException(status_code=400, detail="Cannot delete index while indexing is in progress.")
    
    try:
        # 1. Reset progress
        INDEX_PROGRESS = {
            "is_indexing": False,
            "current_file": "",
            "total_files": 0,
            "processed_files": 0,
            "start_time": 0,
            "percentage": 0.0,
            "eta_seconds": 0.0
        }
        
        # 2. Delete files
        if Path(INDEX_PATH).exists():
            os.remove(INDEX_PATH)
        if Path(DB_PATH).exists():
            os.remove(DB_PATH)
            
        # 3. Re-initialize DB
        init_db(DB_PATH)
        
        return IndexResponse(success=True, message="Index deleted successfully", files_indexed=0, chunks_indexed=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete index: {e}")
