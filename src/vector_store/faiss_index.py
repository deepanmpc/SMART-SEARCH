"""
FAISS vector index — store and search embedding vectors.
"""

import numpy as np
from pathlib import Path
from typing import List, Tuple

import faiss


class FaissIndex:
    """Wrapper around FAISS IndexFlatIP (cosine similarity via L2 normalization)."""

    def __init__(self, dimension: int = 3072):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)

    def add(self, embeddings: List[List[float]]) -> List[int]:
        """Add vectors. Returns assigned vector IDs."""
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)
        start_id = self.index.ntotal
        self.index.add(vectors)
        return list(range(start_id, start_id + len(embeddings)))

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[int, float]]:
        """Search for top_k most similar vectors."""
        query = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query)
        scores, ids = self.index.search(query, top_k)
        return [(int(vid), float(score)) for score, vid in zip(scores[0], ids[0]) if vid != -1]

    def save(self, path: str = "index.faiss"):
        faiss.write_index(self.index, path)

    def load(self, path: str = "index.faiss") -> bool:
        if Path(path).exists():
            self.index = faiss.read_index(path)
            return True
        return False

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal
