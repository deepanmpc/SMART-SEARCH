# 03_PERFORMANCE_AND_SCALING.md

SMART SEARCH --- Performance & Scaling Guide

Author: Deepan Chandrasekaran

This document describes how to make **SMART SEARCH production-grade** by
improving:

-   indexing speed
-   search latency
-   memory efficiency
-   scalability for large datasets

The goal is to support:

100k+ files\
millions of vectors\
\<50ms search latency

------------------------------------------------------------------------

# 1. Indexing Pipeline Optimization

Current indexing pipeline:

file → extraction → chunking → embeddings → vector index → metadata

To scale properly, this pipeline must be **parallelized**.

------------------------------------------------------------------------

## Parallel Processing

Architecture:

file watcher\
↓\
index queue\
↓\
worker pool\
↓\
embedding generation\
↓\
vector insertion

Recommended Python tools:

concurrent.futures\
asyncio\
multiprocessing

------------------------------------------------------------------------

# 2. Embedding Batching

Instead of generating embeddings one-by-one:

embed(file1)\
embed(file2)

Use batching:

embed(\[file1, file2, file3\])

Benefits:

5--10× faster indexing\
fewer API calls\
lower latency

------------------------------------------------------------------------

# 3. Vector Index Scaling

### Small datasets (\<100k vectors)

Use:

IndexFlatIP

Pros: accurate\
simple

------------------------------------------------------------------------

### Medium datasets (100k--5M vectors)

Use:

IndexIVFFlat

Pros: faster search\
better memory usage

------------------------------------------------------------------------

### Large datasets (5M+ vectors)

Use:

IndexHNSWFlat

Pros: graph-based search\
very fast retrieval

------------------------------------------------------------------------

# 4. Vector Normalization

For cosine similarity:

faiss.normalize_L2(vectors)

Use with:

IndexFlatIP

------------------------------------------------------------------------

# 5. SQLite Optimization

Enable performance pragmas:

PRAGMA journal_mode=WAL;\
PRAGMA synchronous=NORMAL;\
PRAGMA cache_size=10000;

Benefits:

faster writes\
better concurrency

------------------------------------------------------------------------

# 6. Thumbnail Caching

Preview generation is expensive.

Solution:

generate thumbnails once\
store in cache

Suggested location:

\~/.smartsearch/cache/thumbnails

------------------------------------------------------------------------

# 7. Search Latency Optimization

Target:

\<50ms search response

Strategies:

preload FAISS index at startup\
keep backend process alive\
cache frequent queries

------------------------------------------------------------------------

# 8. Memory Optimization

Vector storage example:

1M vectors × 768 dims × 4 bytes ≈ 3GB RAM

Solutions:

vector compression\
product quantization\
disk-backed indexes

------------------------------------------------------------------------

# 9. Incremental Index Updates

Instead of rebuilding:

index.add(new_vectors)

For deletions:

mark vectors inactive\
rebuild periodically

------------------------------------------------------------------------

# 10. Background Index Queue

Large indexing must run asynchronously.

Architecture:

index request\
↓\
task queue\
↓\
worker pool\
↓\
progress updates

Tools:

Celery\
Redis queue\
async workers

------------------------------------------------------------------------

# 11. Fault Tolerance

Indexing must not crash the system.

Example pattern:

try: index_file() except: log_error() continue

------------------------------------------------------------------------

# 12. Large Folder Strategy

When indexing large folders:

scan directory\
build file list\
process in batches

Example batch size:

100 files

------------------------------------------------------------------------

# 13. Search Result Caching

Cache recent queries.

Example:

last 50 searches

Cache key:

query hash

------------------------------------------------------------------------

# 14. Startup Performance

Startup sequence:

load FAISS index\
connect SQLite\
start backend daemon

The launcher must feel **instant**.

------------------------------------------------------------------------

# 15. Metrics & Monitoring

Track:

index size\
vector count\
search latency\
RAM usage\
CPU usage

These metrics help maintain performance.

------------------------------------------------------------------------

# 16. Target Performance

SMART SEARCH should comfortably handle:

100k files\
1M vectors\
instant search\
low memory usage

Achieving this makes the system **production ready**.
