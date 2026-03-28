# 02_CORE_FEATURES_TO_ADD.md

SMART SEARCH --- Core Features That Make The Product Stand Out

Author: Deepan Chandrasekaran

This document describes **three major features** that significantly
increase the power and marketability of SMART SEARCH.

Without these features the product remains a **good tool**.

With them it becomes a **category-defining AI search product**.

------------------------------------------------------------------------

# 1. Real-Time File Watching (Auto Indexing)

Currently indexing requires manual action.

Users expect behavior similar to **Spotlight** where new files
automatically become searchable.

### Goal

When a user adds a new file to an indexed folder:

    file created
    ↓
    auto detect
    ↓
    extract content
    ↓
    generate embeddings
    ↓
    update vector index

No user action required.

------------------------------------------------------------------------

## Technology

Use the Python library:

    watchdog

Install:

    pip install watchdog

------------------------------------------------------------------------

## Watcher Architecture

    indexed folders
    ↓
    filesystem watcher
    ↓
    detect changes
    ↓
    queue indexing task
    ↓
    update FAISS index

------------------------------------------------------------------------

## Events To Watch

    FileCreatedEvent
    FileModifiedEvent
    FileDeletedEvent
    FileMovedEvent

------------------------------------------------------------------------

## Implementation Strategy

Create:

    src/file_watcher.py

Responsibilities:

    watch indexed folders
    enqueue indexing tasks
    handle deletions

------------------------------------------------------------------------

## Optimization

To avoid heavy indexing storms:

Use debounce strategy.

Example:

    delay indexing by 5 seconds
    group file events
    batch process

------------------------------------------------------------------------

# 2. Hybrid Search (BM25 + Vector Search)

Vector search alone sometimes misses keyword matches.

Example:

    search: "invoice 2023"

Keyword search may perform better.

### Hybrid approach

    query
    ↓
    vector search
    ↓
    BM25 keyword search
    ↓
    merge results
    ↓
    rerank

------------------------------------------------------------------------

## Benefits

    semantic understanding
    +
    exact keyword precision

This improves recall and accuracy.

------------------------------------------------------------------------

## BM25 Engine

Use:

    rank-bm25

Install:

    pip install rank-bm25

------------------------------------------------------------------------

## Indexing Strategy

During indexing store:

    cleaned text tokens

For BM25 corpus.

Example:

    self.bm25 = BM25Okapi(tokenized_documents)

------------------------------------------------------------------------

## Score Merging

Combine scores:

    final_score = (0.6 * vector_score) + (0.4 * bm25_score)

Weights can be tuned.

------------------------------------------------------------------------

# 3. Instant File Preview System

Users should preview files before opening them.

Preview improves productivity.

------------------------------------------------------------------------

## Preview Triggers

    Space key
    Hover preview
    Top result preview

------------------------------------------------------------------------

## Supported Previews

### Images

    thumbnail preview

### PDFs

    render first page

### Text

    first 20 lines

### Videos

    thumbnail + metadata

### Audio

    waveform preview + metadata

------------------------------------------------------------------------

## Architecture

    search result selected
    ↓
    preview service
    ↓
    generate preview
    ↓
    display preview panel

------------------------------------------------------------------------

## Preview Service

Create:

    src/preview_service.py

Responsibilities:

    generate thumbnails
    render pdf preview
    extract metadata

------------------------------------------------------------------------

## Performance Tips

Preview generation should be:

    lazy loaded
    cached

------------------------------------------------------------------------

# 4. Result Reranking (Optional But Powerful)

After hybrid search retrieve top results.

Apply reranking:

    top 50 results
    ↓
    rerank by context relevance
    ↓
    return top 5

Possible models:

    cross-encoder
    miniLM reranker

------------------------------------------------------------------------

# 5. Goal

With these three features SMART SEARCH becomes:

    AI Spotlight
    +
    Semantic file understanding
    +
    Real-time knowledge retrieval

This dramatically increases product value.
