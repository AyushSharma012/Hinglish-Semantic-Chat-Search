"""
Query embedding helper – uses the same model as message embeddings.
"""

from __future__ import annotations

from typing import List, Optional

from src.data.embeddings import EmbeddingService


class QueryEmbedder:
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.service = embedding_service or EmbeddingService()

    def embed(self, text: str) -> List[float]:
        return self.service.embed_query(text)