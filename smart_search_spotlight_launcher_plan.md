# SMART SEARCH --- Spotlight-Style AI Launcher Implementation Guide

This document is a **build prompt + architecture plan** to implement a
**Spotlight‑like AI search launcher** for the SMART-SEARCH project.

The goal is to create a **macOS glass-style floating search window**
similar to Spotlight, connected to your **AI vector search backend**.

------------------------------------------------------------------------

# 1. Final Product Vision

The application behaves like **macOS Spotlight**, but powered by **AI
semantic search**.

User presses a shortcut → launcher appears.

Capabilities:

-   Search files like Spotlight
-   Semantic AI search across indexed data
-   Index new folders/files
-   Open files instantly
-   Ask AI about files
-   Subscription + storage limits
-   Memory usage meter like Claude

------------------------------------------------------------------------

# 2. User Experience Flow

Keyboard Shortcut:

CMD + SHIFT + SPACE

Launcher appears in the center of screen.

User can type:

    search transformer architecture

or

    index ~/Documents

or

    ask summarize my machine learning notes

Results appear instantly.

User presses ENTER → file opens.

------------------------------------------------------------------------

# 3. UI Requirements

Floating window design:

-   Centered
-   Glassmorphism blur
-   Rounded corners
-   Always on top
-   No title bar
-   Spotlight style

Window size:

    width: 720px
    height: 140px

Expanded results mode:

    width: 720px
    height: 420px

------------------------------------------------------------------------

# 4. macOS Glass UI Design

Use Electron + CSS backdrop blur.

Example style:

    backdrop-filter: blur(30px);
    background: rgba(255,255,255,0.1);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.2);

Search field:

    font-size: 24px
    padding: 16px

------------------------------------------------------------------------

# 5. Global Shortcut

Electron implementation:

    globalShortcut.register("CommandOrControl+Shift+Space", () => {
      showSearchWindow()
    })

------------------------------------------------------------------------

# 6. Command Parser

Commands supported:

    search <query>
    index <folder>
    ask <question>
    reindex
    stats

Example:

    search attention mechanism

------------------------------------------------------------------------

# 7. Indexing Flow

User selects folder.

Process:

    folder
    ↓
    file detection
    ↓
    text extraction
    ↓
    chunking
    ↓
    embedding generation
    ↓
    vector index update
    ↓
    metadata stored

Supported formats:

-   PDF
-   TXT
-   DOCX
-   Images
-   Audio
-   Video

------------------------------------------------------------------------

# 8. File Opening (Spotlight Behavior)

When a result is selected:

    open /path/to/file

macOS command:

    open file_path

------------------------------------------------------------------------

# 9. Vector Storage System

Architecture:

    FAISS vector index
    +
    SQLite metadata database

Metadata table:

    id
    file_name
    file_path
    chunk_text
    vector_id
    content_type
    timestamp

------------------------------------------------------------------------

# 10. Subscription Model

Plan tiers:

### Free

    max indexed files: 500
    vector limit: 50k
    storage: 500MB

### Plus

    max indexed files: 5000
    vector limit: 500k
    storage: 5GB

### Pro

    max indexed files: unlimited
    vector limit: unlimited
    storage: 50GB

------------------------------------------------------------------------

# 11. Memory Usage Indicator

Display usage similar to Claude.

Example UI:

    Memory Usage
    ████████░░░░░░░░ 45%

Displayed in launcher footer.

Computation:

    used_vectors / max_vectors * 100

------------------------------------------------------------------------

# 12. Index Limit Enforcement

Before indexing:

    if vectors_used + new_vectors > plan_limit:
        block_indexing()

Show message:

    Memory limit reached.
    Upgrade to Plus or Pro.

------------------------------------------------------------------------

# 13. Backend API

Use FastAPI.

Endpoints:

    POST /search
    POST /index
    GET /stats
    POST /ask

Example search request:

    {
     "query": "transformer attention"
    }

Response:

    [
     {
       "file": "attention.pdf",
       "snippet": "...self attention mechanism...",
       "score": 0.91
     }
    ]

------------------------------------------------------------------------

# 14. Search Pipeline

    user query
    ↓
    embedding generation
    ↓
    vector search
    ↓
    top results
    ↓
    metadata retrieval
    ↓
    return results

------------------------------------------------------------------------

# 15. Result UI

Each result shows:

-   file icon
-   file name
-   snippet
-   similarity score

Example:

    📄 attention.pdf
    Self attention allows the model to focus...

------------------------------------------------------------------------

# 16. AI Answer Mode

Command:

    ask <question>

Pipeline:

    query
    ↓
    vector search
    ↓
    retrieve top chunks
    ↓
    LLM answer

------------------------------------------------------------------------

# 17. Real-Time Indexing (Optional)

Watch folders using:

    watchdog (python)

Flow:

    new file detected
    ↓
    auto extract
    ↓
    embed
    ↓
    update vector index

------------------------------------------------------------------------

# 18. Full System Architecture

    SMART SEARCH

    ⌨ global shortcut
    ↓
    launcher window
    ↓
    command parser

    index / search / ask

    ↓
    FastAPI backend
    ↓
    vector search engine
    ↓
    FAISS index
    ↓
    SQLite metadata

------------------------------------------------------------------------

# 19. Advanced Features (Future)

Possible improvements:

-   hybrid search (BM25 + vectors)
-   cross encoder reranking
-   code search
-   image similarity search
-   local LLM integration

------------------------------------------------------------------------

# 20. Goal

The finished product becomes:

    AI powered Spotlight
    +
    local AI search engine
    +
    semantic file retrieval
