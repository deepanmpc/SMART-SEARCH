"""
OmniSearch CLI (FAISS edition)
------------------------------
python main.py          → interactive menu
python main.py index    → index a folder
python main.py search   → search
python main.py clear    → wipe the index
python main.py status   → stats
"""

import sys
import os
import shutil
import time
import hashlib
from pathlib import Path
from collections import Counter

# ── ANSI colours ─────────────────────────────────────────────────────────────
RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
GREEN = "\033[32m"; CYAN = "\033[36m"; YELLOW = "\033[33m"
RED   = "\033[31m"; MAGENTA = "\033[35m"

def c(col, t): return f"{col}{t}{RESET}"
def bold(t):   return c(BOLD, t)
def dim(t):    return c(DIM, t)
def ok(t):     return c(GREEN, t)
def warn(t):   return c(YELLOW, t)
def err(t):    return c(RED, t)
def info(t):   return c(CYAN, t)
def hi(t):     return c(MAGENTA, t)

# ── layout ────────────────────────────────────────────────────────────────────
def tw():   return shutil.get_terminal_size((80, 24)).columns
def rule(ch="─"): print(dim(ch * tw()))

def header():
    os.system("cls" if os.name == "nt" else "clear")
    print()
    print(bold(c(CYAN, "  OmniSearch")))
    print(dim("  semantic file search  ·  FAISS"))
    rule()
    print()

# ── spinner ───────────────────────────────────────────────────────────────────
class Spinner:
    F = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    def __init__(self, label=""): self.label = label; self._i = 0
    def tick(self):
        print(f"\r{c(CYAN, self.F[self._i % len(self.F)])}  {self.label}",
              end="", flush=True)
        self._i += 1; time.sleep(0.08)
    def done(self, msg=""):
        print(f"\r{ok('✓')}  {msg or self.label}" + " " * 20)

# ── constants ─────────────────────────────────────────────────────────────────
SUPPORTED   = {".pdf": "pdf", ".docx": "docx", ".doc": "docx", ".txt": "text"}
SKIP_DIRS   = {".git", ".venv", "__pycache__", "node_modules", ".DS_Store"}
INDEX_PATH  = "index.faiss"
DB_PATH     = "metadata.db"
CHUNK_WORDS = 100
OVERLAP     = 25

# ── lazy imports from our modules ─────────────────────────────────────────────
def _faiss_index():
    from vector_store.faiss_index import FaissIndex
    idx = FaissIndex()
    idx.load(INDEX_PATH)
    return idx

def _db_conn():
    from database.metadata_store import init_db
    return init_db(DB_PATH)

def _vector_count() -> int:
    try:
        idx = _faiss_index()
        return idx.total_vectors
    except Exception:
        return 0

def _crawl(folder: str) -> list[dict]:
    files = []
    for path in Path(folder).rglob("*"):
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            stat = path.stat()
            files.append({
                "filename": path.name,
                "path":     str(path),
                "type":     SUPPORTED[path.suffix.lower()],
                "ext":      path.suffix.lower(),
                "modified": stat.st_mtime,
            })
    return files

def _chunk_id(path: str, i: int) -> str:
    return hashlib.md5(f"{path}::{i}".encode()).hexdigest()

# ─────────────────────────────────────────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

def cmd_index(folder: str | None = None):
    header()
    print(bold("Index a folder"))
    print(dim("Crawls files, extracts text, chunks, embeds and stores vectors.\n"))

    if not folder:
        folder = input(f"  {info('Folder path')} › ").strip()
    if not folder:
        print(warn("No folder given.")); return

    folder = os.path.expanduser(folder)
    if not Path(folder).exists():
        print(err(f"Path not found: {folder}")); return

    # crawl
    spin = Spinner("Crawling…")
    spin.tick()
    files = _crawl(folder)
    spin.done(f"Found {bold(str(len(files)))} files")

    if not files:
        print(warn("No supported files (.pdf .docx .doc .txt)")); return

    for t, n in Counter(f["type"] for f in files).items():
        print(f"  {dim('·')} {n:4d}  {t}")
    print()

    if len(files) > 50:
        go = input(f"  {warn(f'Index all {len(files)} files?')} (y/n) › ").strip().lower()
        if go != "y": return
        print()

    from ingestion.pdf_parser import parse_document
    from chunking.chunker import chunk_text
    from embedding.gemini_embedder import embed_unit, make_file_id
    from vector_store.faiss_index import FaissIndex
    from database.metadata_store import init_db, insert_chunk, clear_document

    conn = init_db(DB_PATH)
    faiss_idx = FaissIndex()
    faiss_idx.load(INDEX_PATH)

    total_chunks = skipped = 0
    rule("·")

    for i, fm in enumerate(files):
        label = f"[{i+1}/{len(files)}] {fm['filename']}"

        result = parse_document(fm["path"])
        if not result["success"]:
            print(f"  {dim('–')} {dim(label)} {warn('(skipped)')}")
            skipped += 1
            continue

        chunks = chunk_text(result["text"])
        if not chunks:
            print(f"  {dim('–')} {dim(label)} {warn('(no text)')}")
            skipped += 1
            continue

        clear_document(conn, fm["path"])

        indexed = 0
        for ci, chunk in enumerate(chunks):
            unit = {"type": "text", "data": chunk}
            vec = embed_unit(unit)
            if vec is None:
                continue

            if faiss_idx.total_vectors == 0 and faiss_idx.dimension != len(vec):
                faiss_idx = FaissIndex(dimension=len(vec))

            vector_ids = faiss_idx.add([vec])
            file_id = make_file_id(fm["path"], ci)
            insert_chunk(conn, vector_ids[0], file_id, fm, ci, chunk)
            indexed += 1
            total_chunks += 1

        print(f"  {ok('✓')} {label} {dim(f'({indexed} chunks)')}")

    faiss_idx.save(INDEX_PATH)

    print()
    rule()
    print(f"\n  {ok('Done.')}  {bold(str(total_chunks))} chunks indexed  ·  {skipped} skipped\n")
    input(dim("  Press Enter to return…"))


def cmd_search(query: str | None = None):
    header()
    print(bold("Search"))
    print(dim("Natural language query across all indexed files.\n"))

    total = _vector_count()
    if total == 0:
        print(warn("Nothing indexed yet. Run 'index' first.\n"))
        input(dim("  Press Enter to return…")); return

    print(dim(f"  {total} chunks in index\n"))

    from embedding.gemini_embedder import embed_query
    from vector_store.faiss_index import FaissIndex
    from database.metadata_store import init_db, get_by_vector_ids

    while True:
        if not query:
            query = input(f"  {info('Query')} › ").strip()
        if not query:
            print(warn("Empty query.")); return

        n_str = input(f"  {info('Results')} [{dim('5')}] › ").strip()
        n     = int(n_str) if n_str.isdigit() else 5

        print()
        spin = Spinner("Searching…")
        for _ in range(8): spin.tick()

        vec = embed_query(query)
        faiss_idx = FaissIndex(dimension=len(vec))
        faiss_idx.load(INDEX_PATH)

        results = faiss_idx.search(vec, top_k=n)
        spin.done("Done")

        print()
        rule()
        print(f"\n  {bold('Results for:')} {hi(query)}\n")

        if not results:
            print(warn("  No results found."))
        else:
            conn = init_db(DB_PATH)
            vector_ids = [vid for vid, _ in results]
            scores = {vid: score for vid, score in results}
            metadata = get_by_vector_ids(conn, vector_ids)

            for rank, row in enumerate(sorted(metadata, key=lambda r: scores.get(r["vector_id"], 0), reverse=True), 1):
                score  = scores.get(row["vector_id"], 0)
                filled = int(score * 14)
                bar    = ok("█" * filled) + dim("░" * (14 - filled))
                pct    = f"{int(score*100)}%"

                print(f"  {bold(str(rank)+'.')}  {bar}  {bold(pct)}")
                print(f"       {c(CYAN, row['document_name'])}  "
                      f"{dim(row.get('file_type', ''))}  "
                      f"{dim('chunk ' + str(row['chunk_index']))}")
                chunk_preview = (row.get("chunk_text") or "")[:120]
                if chunk_preview:
                    print(f"       {dim(chunk_preview)}…")
                print()

        rule()
        print()
        again = input(f"  {dim('Search again? (y/n)')} › ").strip().lower()
        if again != "y":
            input(dim("  Press Enter to return…")); return
        query = None
        print()


def cmd_clear():
    header()
    print(bold("Clear index"))
    print(dim("Deletes all vectors and metadata. Your files are never touched.\n"))

    total = _vector_count()
    print(f"  Chunks currently stored: {bold(str(total))}\n")

    if total == 0:
        print(dim("  Index is already empty.\n"))
        input(dim("  Press Enter to return…")); return

    confirm = input(f"  {warn('Type YES to confirm')} › ").strip()
    if confirm != "YES":
        print(dim("\n  Cancelled.")); time.sleep(0.8); return

    try:
        if Path(INDEX_PATH).exists():
            os.remove(INDEX_PATH)
        if Path(DB_PATH).exists():
            os.remove(DB_PATH)
        print(f"\n  {ok('Index cleared.')}")
    except Exception as e:
        print(err(f"\n  Failed: {e}"))

    print()
    input(dim("  Press Enter to return…"))


def cmd_status():
    header()
    print(bold("Status\n"))

    total = _vector_count()
    index_file = Path(INDEX_PATH)
    db_file = Path(DB_PATH)
    index_size = index_file.stat().st_size if index_file.exists() else 0
    db_size = db_file.stat().st_size if db_file.exists() else 0
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    rows = [
        ("Chunks indexed",  bold(str(total))),
        ("FAISS index",     bold(f"{round(index_size/1_000_000, 2)} MB") + dim(f"  ({INDEX_PATH})")),
        ("SQLite DB",       bold(f"{round(db_size/1_000_000, 2)} MB") + dim(f"  ({DB_PATH})")),
        ("Embed model",     dim("gemini-embedding-2-preview")),
        ("Chunk size",      dim(f"{CHUNK_WORDS} words / {OVERLAP}w overlap")),
        ("GOOGLE_API_KEY",  ok("set") if api_key else err("NOT SET")),
    ]
    for label, val in rows:
        print(f"  {dim(label):<32}{val}")

    print()
    rule()
    print()

    if not api_key:
        print(warn("  Set your key:  export GOOGLE_API_KEY=your_key_here\n"))

    input(dim("  Press Enter to return…"))


def cmd_help():
    header()
    print(bold("Commands\n"))
    lines = [
        ("python main.py",           "interactive menu"),
        ("python main.py index",     "index a folder (prompts for path)"),
        ("python main.py index /p",  "index a specific folder"),
        ("python main.py search",    "search (prompts for query)"),
        ('python main.py search "q"',"search with inline query"),
        ("python main.py clear",     "wipe the vector index"),
        ("python main.py status",    "show stats and config"),
        ("python main.py help",      "this screen"),
    ]
    for cmd, desc in lines:
        print(f"  {c(CYAN, cmd):<42}{dim(desc)}")
    print()
    rule()
    print()
    input(dim("  Press Enter to return…"))


# ─────────────────────────────────────────────────────────────────────────────
# MENU
# ─────────────────────────────────────────────────────────────────────────────

MENU = [
    ("i", "Index a folder",  cmd_index),
    ("s", "Search",          cmd_search),
    ("c", "Clear index",     cmd_clear),
    ("t", "Status",          cmd_status),
    ("h", "Help",            cmd_help),
    ("q", "Quit",            None),
]

def menu_loop():
    while True:
        header()
        print(f"  {dim('Chunks indexed:')} {bold(str(_vector_count()))}\n")
        for key, label, _ in MENU:
            print(f"  {c(CYAN, bold(key))}  {label}")
        print()
        choice = input(f"  {dim('›')} ").strip().lower()
        print()
        if choice == "q":
            print(dim("  bye.\n")); break
        fn = next((f for k, _, f in MENU if k == choice), None)
        if fn: fn()
        else:
            print(warn("  Unknown option.")); time.sleep(0.5)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        menu_loop(); return

    dispatch = {
        "index":  lambda: cmd_index(" ".join(args[1:]) or None),
        "search": lambda: cmd_search(" ".join(args[1:]) or None),
        "clear":  cmd_clear,
        "status": cmd_status,
        "help":   cmd_help,
    }

    fn = dispatch.get(args[0].lower())
    if fn: fn()
    else:
        print(err(f"\n  Unknown command: {args[0]}"))
        print(dim("  Run: python main.py help\n"))
        sys.exit(1)


if __name__ == "__main__":
    main()
