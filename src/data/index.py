"""
Hybrid vector + metadata index using ChromaDB (local persistent).
Supports semantic similarity search combined with person and/or time filters.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings
from src.data.models import Message
from src.data.embeddings import EmbeddingService


class HybridIndex:
    """
    ChromaDB-backed hybrid index.
    Each document stores:
      - id          : str(msg_id)
      - embedding   : vector
      - document    : original text
      - metadata    : {sender, timestamp_iso, msg_id}
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        collection_name: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.persist_path = Path(persist_path or settings.CHROMA_PATH)
        self.collection_name = collection_name or settings.CHROMA_COLLECTION
        self.embedding_service = embedding_service or EmbeddingService()

        self.client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_messages(
        self,
        messages: List[Message],
        embeddings: Optional[List[List[float]]] = None,
        batch_size: int = 128,
    ) -> int:
        """
        Add messages to the index.
        If embeddings is None they are computed on the fly.
        """
        if not messages:
            return 0

        if embeddings is None:
            texts = [m.text for m in messages]
            emb_array = self.embedding_service.embed(texts)
            embeddings = emb_array.tolist()

        total = 0
        for i in range(0, len(messages), batch_size):
            batch_msgs = messages[i : i + batch_size]
            batch_embs = embeddings[i : i + batch_size]
            ids = [str(m.msg_id) for m in batch_msgs]
            documents = [m.text for m in batch_msgs]
            metadatas = [
                {
                    "sender": m.sender,
                    "timestamp": m.timestamp.isoformat(),
                    "msg_id": m.msg_id,
                }
                for m in batch_msgs
            ]
            # Chroma upsert
            self.collection.upsert(
                ids=ids,
                embeddings=batch_embs,
                documents=documents,
                metadatas=metadatas,
            )
            total += len(batch_msgs)
        return total

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        sender: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: vector similarity + optional metadata filters.
        Returns list of dicts:
          {
            "msg_id": int,
            "text": str,
            "sender": str,
            "timestamp": str (iso),
            "score": float   # cosine similarity (1 - distance)
          }
        Ranked by score descending.
        """
        where: Dict[str, Any] = {}
        if sender is not None:
            where["sender"] = sender

        # Chroma supports only one operator level; for time we post-filter
        # if both sender and time are present we still filter sender in Chroma
        # and time in Python (simple & reliable for 4k–10k msgs).

        n_results = min(top_k * 5, 100) if (start_time or end_time) else top_k

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )

        hits: List[Dict[str, Any]] = []
        if not results["ids"] or not results["ids"][0]:
            return hits

        for i, msg_id_str in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i]
            # cosine distance → similarity
            score = 1.0 - dist

            ts_str = meta["timestamp"]
            ts = datetime.fromisoformat(ts_str)

            if start_time and ts < start_time:
                continue
            if end_time and ts > end_time:
                continue

            hits.append(
                {
                    "msg_id": int(meta["msg_id"]),
                    "text": results["documents"][0][i],
                    "sender": meta["sender"],
                    "timestamp": ts_str,
                    "score": float(score),
                }
            )

        # Already roughly sorted by distance; re-sort by score and truncate
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:top_k]

    def count(self) -> int:
        return self.collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection (full rebuild)."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )