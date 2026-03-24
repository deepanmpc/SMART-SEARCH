"""
FAISS vector index — store and search embedding vectors.
"""

import numpy as np
from pathlib import Path
from typing import List, Tuple

import faiss


class FaissIndex:
    """Wrapper around a FAISS IndexFlatIP (inner-product / cosine similarity)."""

    def __init__(self, dimension: int = 3072):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)

    def add(self, embeddings: List[List[float]]) -> List[int]:
        """
        Add embedding vectors to the index.
        Returns the list of vector IDs assigned (0-based, sequential).
        """

        vectors = np.array(embeddings, dtype=np.float32)

        # Normalize for cosine similarity
        faiss.normalize_L2(vectors)

        start_id = self.index.ntotal
        self.index.add(vectors)

        return list(range(start_id, start_id + len(embeddings)))

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Search for the top_k most similar vectors.
        Returns list of (vector_id, similarity_score).
        """

        query = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query)

        scores, ids = self.index.search(query, top_k)

        results = []
        for score, vid in zip(scores[0], ids[0]):
            if vid != -1:  # FAISS returns -1 for empty spots
                results.append((int(vid), float(score)))

        return results

    def save(self, path: str = "index.faiss"):
        """Persist the index to disk."""
        faiss.write_index(self.index, path)

    def load(self, path: str = "index.faiss"):
        """Load a persisted index from disk."""
        if Path(path).exists():
            self.index = faiss.read_index(path)
            return True
        return False

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal
