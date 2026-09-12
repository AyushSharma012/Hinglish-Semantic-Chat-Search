"""
Embedding generation service using a Hinglish-capable multilingual model.
"""

from __future__ import annotations

from typing import List, Optional, Union
import numpy as np

from config.settings import settings


class EmbeddingService:
    """
    Thin wrapper around sentence-transformers.
    Uses paraphrase-multilingual-MiniLM-L12-v2 by default (good Hinglish support).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.DEVICE
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed(
        self,
        texts: Union[str, List[str]],
        batch_size: Optional[int] = None,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Embed one or more texts.
        Returns shape (n, dim) float32 array. L2-normalized if normalize=True.
        """
        model = self._load_model()
        if isinstance(texts, str):
            texts = [texts]
        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> List[float]:
        """Convenience: embed a single query and return as list."""
        vec = self.embed(query)
        return vec[0].tolist()

    @property
    def dimension(self) -> int:
        model = self._load_model()
        return model.get_sentence_embedding_dimension()