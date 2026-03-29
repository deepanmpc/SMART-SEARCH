import os
import mimetypes
import time
import psutil
from pathlib import Path
from collections import Counter
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from google.genai.errors import ClientError

# Import local modules
from api_models import SearchRequest, SearchResponse, SearchResult, IndexRequest, IndexResponse, StatsResponse, AskRequest, AskResponse, IndexStatusResponse
from main import _crawl, _vector_count, INDEX_PATH, DB_PATH
from search.query_engine import search as semantic_search

from ingestion.document_parser import parse_document
from chunking.chunker import chunk_text
from embedding.gemini_embedder import embed_batch, make_file_id, _get_client
from contextlib import asynccontextmanager
import threading
from vector_store.faiss_index import FaissIndex
from database.metadata_store import init_db, insert_chunk, clear_document, is_document_indexed, add_watched_folder, get_all_watched_folders
from file_watcher import start_watcher

# Global lock for FAISS index and DB operations to prevent race conditions during auto-indexing
INDEXING_LOCK = threading.Lock()
WATCHER_OBSERVER = None

def watcher_callback(to_index, to_delete):
    if to_delete:
        with INDEXING_LOCK:
            conn = init_db(DB_PATH)
            for path in to_delete:
                clear_document(conn, path)
    
    if to_index:
        # Re-use run_indexing logic but with specific files
        # We start it in a separate thread to not block the watcher's thread
        threading.Thread(target=run_indexing, args=(to_index, True)).start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global WATCHER_OBSERVER
    # Start watcher on startup
    WATCHER_OBSERVER = start_watcher(DB_PATH, watcher_callback)
    yield
    # Stop watcher on shutdown
    if WATCHER_OBSERVER:
        WATCHER_OBSERVER.stop()
        WATCHER_OBSERVER.join()

app = FastAPI(title="SMART SEARCH API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(ClientError)
async def genai_exception_handler(request, exc: ClientError):
    if exc.status_code == 429:
        return JSONResponse(
            status_code=429,
            content={"detail": "Gemini API Quota Exceeded (1000 requests/day). Please wait a few hours or check your billing."}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Gemini API Error: {exc}"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later or check your backend logs."}
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
    "is_paused": False,
    "current_file": "",
    "total_files": 0,
    "processed_files": 0,
    "start_time": 0,
    "percentage": 0.0,
    "eta_seconds": 0.0
}
STOP_INDEXING_EVENT = threading.Event()
PAUSE_INDEXING_EVENT = threading.Event()

@app.post("/index/stop")
def stop_indexing():
    global INDEX_PROGRESS
    if INDEX_PROGRESS["is_indexing"]:
        STOP_INDEXING_EVENT.set()
        return {"success": True, "message": "Stopping indexing..."}
    return {"success": False, "message": "No indexing in progress."}

@app.post("/index/pause")
def pause_indexing():
    global INDEX_PROGRESS
    if INDEX_PROGRESS["is_indexing"]:
        if PAUSE_INDEXING_EVENT.is_set():
            PAUSE_INDEXING_EVENT.clear()
            INDEX_PROGRESS["is_paused"] = False
            return {"success": True, "message": "Indexing resumed."}
        else:
            PAUSE_INDEXING_EVENT.set()
            INDEX_PROGRESS["is_paused"] = True
            return {"success": True, "message": "Indexing paused."}
    return {"success": False, "message": "No indexing in progress."}

# Memory tracking state for smoothing
PEAK_RAM_USAGE = 0.0

@app.get("/stats", response_model=StatsResponse)
def get_stats():
    global PEAK_RAM_USAGE
    total_vectors = _vector_count()
    limit = PLAN_LIMITS.get(CURRENT_PLAN, 50000)
    
    # Get RAM usage of current process AND its children (like Tika/Java)
    try:
        current_process = psutil.Process(os.getpid())
        mem = current_process.memory_info().rss
        for child in current_process.children(recursive=True):
            try:
                mem += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        ram_usage = mem / (1024 * 1024)  # Convert to MB
        
        # Implementation of "Proper" increasing:
        # We only update if it goes UP, keeping the peak persistent 
        # so the user doesn't see sudden drops when Java/GC finishes.
        if ram_usage > PEAK_RAM_USAGE:
            PEAK_RAM_USAGE = ram_usage
            
        reported_ram = PEAK_RAM_USAGE
    except Exception:
        reported_ram = 0.0
        
    ram_limit = 500.0  # From PRODUCT_FIXES.md target
    
    return StatsResponse(
        total_chunks=total_vectors,
        plan=CURRENT_PLAN,
        plan_limit=limit,
        usage_percent=round((total_vectors / limit) * 100, 2),
        ram_usage_mb=round(reported_ram, 2),
        ram_limit_mb=ram_limit
    )

from functools import lru_cache

@lru_cache(maxsize=50)
def _cached_semantic_search(query: str, top_k: int, index_path: str, db_path: str):
    return semantic_search(query, top_k=top_k, index_path=index_path, db_path=db_path)

@app.post("/search", response_model=SearchResponse)
def search_endpoint(req: SearchRequest):
    # Optimize: Increase fetching multiplier for all queries to ensure images surface,
    # even when text scores highly.
    multiplier = 50 if req.file_type == "image" else 5
    search_k = req.top_k * multiplier

    results = _cached_semantic_search(req.query, search_k, INDEX_PATH, DB_PATH)    
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
            file_path=r.get("document_path", ""),
            file_type=r_type,
            content_type="image" if r_type == "image" else "video" if r_type == "video" else "audio" if r_type == "audio" else "text",
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
        # Bug 1: Use document_path instead of file_path
        file_path = r.get("document_path", "Unknown")
        context_parts.append(f"[Source {i}: {file_path}]\n{text}\n")
        sources.append(SearchResult(
            document_name=r.get("document_name", ""),
            file_path=file_path,
            file_type=r.get("file_type", ""),
            content_type="image" if r.get("file_type") == "image" else "video" if r.get("file_type") == "video" else "audio" if r.get("file_type") == "audio" else "text",
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

from concurrent.futures import ThreadPoolExecutor

def run_indexing(paths: List[str], is_update: bool = False):
    global INDEX_PROGRESS, WATCHER_OBSERVER
    import time as time_mod
    
    if not is_update:
        STOP_INDEXING_EVENT.clear()
        PAUSE_INDEXING_EVENT.clear()
        INDEX_PROGRESS["is_indexing"] = True
        INDEX_PROGRESS["is_paused"] = False
        INDEX_PROGRESS["processed_files"] = 0
        INDEX_PROGRESS["percentage"] = 0.0
    
    try:
        all_found = []
        if not is_update:
            for p in paths:
                if STOP_INDEXING_EVENT.is_set(): break
                folder = os.path.expanduser(p)
                all_found.extend(_crawl(folder, stop_event=STOP_INDEXING_EVENT))
        else:
            from crawler import SUPPORTED_EXTENSIONS
            for p in paths:
                if STOP_INDEXING_EVENT.is_set(): break
                if os.path.isfile(p):
                    ext = os.path.splitext(p)[1].lower()
                    fm_type = SUPPORTED_EXTENSIONS.get(ext, "text")
                    all_found.append({"path": p, "filename": os.path.basename(p), "type": fm_type, "ext": ext})

        if not all_found or (not is_update and STOP_INDEXING_EVENT.is_set()):
            if not is_update: INDEX_PROGRESS["is_indexing"] = False
            STOP_INDEXING_EVENT.clear()
            PAUSE_INDEXING_EVENT.clear()
            return
            
        if not is_update:
            INDEX_PROGRESS["total_files"] = len(all_found)
            INDEX_PROGRESS["processed_files"] = 0
            INDEX_PROGRESS["start_time"] = time_mod.time()
        
        limit = PLAN_LIMITS.get(CURRENT_PLAN, 50000)
        from ingestion.media_parser import chunk_image, chunk_video
        
        def process_file(index_and_file):
            i, fm = index_and_file
            
            # PAUSE/STOP check
            while not is_update and PAUSE_INDEXING_EVENT.is_set() and not STOP_INDEXING_EVENT.is_set():
                time_mod.sleep(0.5)
            if not is_update and STOP_INDEXING_EVENT.is_set(): 
                return
                
            if not is_update:
                INDEX_PROGRESS["current_file"] = fm["filename"]
                # Processed files incremented at end of this function

            with INDEXING_LOCK:
                faiss_idx = FaissIndex()
                if Path(INDEX_PATH).exists(): faiss_idx.load(INDEX_PATH)
                if faiss_idx.total_vectors >= limit: return
                    
                conn = init_db(DB_PATH)
                if is_document_indexed(conn, fm["path"]):
                    if is_update: clear_document(conn, fm["path"])
                    else: return

            try:
                if fm["type"] in ("image", "audio", "video"):
                    media_chunks = []
                    if fm["type"] == "image":
                        with open(fm["path"], "rb") as bf: img_bytes = bf.read()
                        media_chunks = chunk_image(img_bytes, stop_event=STOP_INDEXING_EVENT if not is_update else None)
                    elif fm["type"] == "video":
                        media_chunks = chunk_video(fm["path"], stop_event=STOP_INDEXING_EVENT if not is_update else None)
                    elif fm["type"] == "audio":
                        with open(fm["path"], "rb") as bf: data = bf.read()
                        mime_type, _ = mimetypes.guess_type(fm["path"])
                        if not mime_type: mime_type = f"audio/{fm['ext'][1:]}"
                        media_chunks = [{"type": "audio", "data": data, "mime_type": mime_type, "suffix": "full"}]

                    if media_chunks:
                        batch_size = 16
                        for b_idx in range(0, len(media_chunks), batch_size):
                            while not is_update and PAUSE_INDEXING_EVENT.is_set() and not STOP_INDEXING_EVENT.is_set(): time_mod.sleep(0.5)
                            if not is_update and STOP_INDEXING_EVENT.is_set(): break
                            
                            batch = media_chunks[b_idx : b_idx + batch_size]
                            units = [{"type": "audio" if fm["type"] == "audio" else "image", "data": c["data"], "mime_type": c.get("mime_type", "image/jpeg")} for c in batch]
                            vecs = embed_batch(units) or []
                            
                            with INDEXING_LOCK:
                                faiss_idx = FaissIndex()
                                if Path(INDEX_PATH).exists(): faiss_idx.load(INDEX_PATH)
                                conn = init_db(DB_PATH)
                                for idx_in_batch, (c, vec) in enumerate(zip(batch, vecs)):
                                    if vec is not None:
                                        v_ids = faiss_idx.add([vec])
                                        f_id = make_file_id(fm["path"], b_idx + idx_in_batch)
                                        desc = f"[{fm['type'].capitalize()} Content]"
                                        insert_chunk(conn, v_ids[0], f_id, fm, b_idx + idx_in_batch, desc)
                                faiss_idx.save(INDEX_PATH)
                else:
                    result = parse_document(fm["path"])
                    if result["success"]:
                        chunks = chunk_text(result["text"])
                        if chunks:
                            batch_size = 50
                            for b_idx in range(0, len(chunks), batch_size):
                                while not is_update and PAUSE_INDEXING_EVENT.is_set() and not STOP_INDEXING_EVENT.is_set(): time_mod.sleep(0.5)
                                if not is_update and STOP_INDEXING_EVENT.is_set(): break
                                batch = chunks[b_idx : b_idx + batch_size]
                                units = [{"type": "text", "data": c} for c in batch]
                                vecs = embed_batch(units) or []
                                with INDEXING_LOCK:
                                    faiss_idx = FaissIndex()
                                    if Path(INDEX_PATH).exists(): faiss_idx.load(INDEX_PATH)
                                    conn = init_db(DB_PATH)
                                    for idx_in_batch, (txt, vec) in enumerate(zip(batch, vecs)):
                                        if vec is not None:
                                            v_ids = faiss_idx.add([vec])
                                            f_id = make_file_id(fm["path"], b_idx + idx_in_batch)
                                            insert_chunk(conn, v_ids[0], f_id, fm, b_idx + idx_in_batch, txt)
                                    faiss_idx.save(INDEX_PATH)
            except Exception as e:
                print(f"Error processing {fm['path']}: {e}")
            
            if not is_update:
                INDEX_PROGRESS["processed_files"] += 1
                INDEX_PROGRESS["percentage"] = round((INDEX_PROGRESS["processed_files"] / INDEX_PROGRESS["total_files"]) * 100, 1)

        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(os.cpu_count() or 4, 8) # Cap workers to avoid overwhelming API or SQLite
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(process_file, enumerate(all_found))

        if not is_update:
            INDEX_PROGRESS["percentage"] = 100.0
            INDEX_PROGRESS["eta_seconds"] = 0.0
            INDEX_PROGRESS["is_indexing"] = False
            STOP_INDEXING_EVENT.clear()
            PAUSE_INDEXING_EVENT.clear()
    except Exception as e:
        print(f"Error in background indexing: {e}")
        if not is_update:
            INDEX_PROGRESS["is_indexing"] = False
            STOP_INDEXING_EVENT.clear()
            PAUSE_INDEXING_EVENT.clear()

    except Exception as e:
        print(f"Error in background indexing: {e}")
        if not is_update:
            INDEX_PROGRESS["is_indexing"] = False
            STOP_INDEXING_EVENT.clear()
            PAUSE_INDEXING_EVENT.clear()


from preview_service import generate_preview

class PreviewRequest(BaseModel):
    file_path: str

@app.post("/preview")
def preview_endpoint(req: PreviewRequest):
    return generate_preview(req.file_path)

@app.post("/index", response_model=IndexResponse)
def index_endpoint(req: IndexRequest, background_tasks: BackgroundTasks):
    global INDEX_PROGRESS, WATCHER_OBSERVER
    if INDEX_PROGRESS["is_indexing"]:
        return IndexResponse(success=False, message="Indexing already in progress", files_indexed=0, chunks_indexed=0)
    
    # Pre-check paths
    conn = init_db(DB_PATH)
    for p in req.paths:
        path = os.path.expanduser(p)
        if not Path(path).exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        # Add to watched folders
        if os.path.isdir(path):
            add_watched_folder(conn, path)

    # Restart watcher to pick up new folders
    if WATCHER_OBSERVER:
        print("API: Restarting file watcher...")
        WATCHER_OBSERVER.stop()
        # We don't join() here to avoid blocking the request, 
        # but we start a new one. The old one will die in background.
    
    WATCHER_OBSERVER = start_watcher(DB_PATH, watcher_callback)

    background_tasks.add_task(run_indexing, req.paths)
    return IndexResponse(success=True, message="Indexing started in background", files_indexed=0, chunks_indexed=0)

@app.delete("/index", response_model=IndexResponse)
def delete_index_endpoint():
    global INDEX_PROGRESS, WATCHER_OBSERVER
    if INDEX_PROGRESS["is_indexing"]:
        raise HTTPException(status_code=400, detail="Cannot delete index while indexing is in progress.")
    
    try:
        # 1. Reset progress
        INDEX_PROGRESS = {
            "is_indexing": False,
            "is_paused": False,
            "current_file": "",
            "total_files": 0,
            "processed_files": 0,
            "start_time": 0,
            "percentage": 0.0,
            "eta_seconds": 0.0
        }
        
        # 2. Stop Watcher
        if WATCHER_OBSERVER:
            WATCHER_OBSERVER.stop()
            WATCHER_OBSERVER = None

        # 3. Delete files
        if Path(INDEX_PATH).exists():
            os.remove(INDEX_PATH)
        if Path(DB_PATH).exists():
            os.remove(DB_PATH)
            
        # 4. Re-initialize DB
        init_db(DB_PATH)
        
        return IndexResponse(success=True, message="Index deleted successfully", files_indexed=0, chunks_indexed=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete index: {e}")
