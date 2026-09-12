#!/usr/bin/env python3
"""
One-time (or re-runnable) pipeline:
  1. Load raw messages JSON → SQLite store
  2. Generate embeddings
  3. Build / rebuild Chroma hybrid index
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tqdm import tqdm

from config.settings import settings
from src.data.store import MessageStore
from src.data.embeddings import EmbeddingService
from src.data.index import HybridIndex


def main():
    settings.ensure_dirs()

    raw_path = settings.RAW_DATA_PATH
    if not raw_path.exists():
        print(f"Raw data not found at {raw_path}")
        print("Run: python scripts/generate_synthetic_data.py")
        sys.exit(1)

    print("Loading messages into SQLite…")
    store = MessageStore()
    count = store.load_from_json(raw_path)
    print(f"  Stored {count} messages (total in DB: {store.count()})")

    print("Loading embedding model…")
    emb_service = EmbeddingService()
    print(f"  Model: {emb_service.model_name} (dim={emb_service.dimension})")

    print("Generating embeddings…")
    messages = store.get_all_messages()
    texts = [m.text for m in messages]
    embeddings = emb_service.embed(texts)
    print(f"  Embedded {len(embeddings)} messages")

    print("Building Chroma index…")
    index = HybridIndex(embedding_service=emb_service)
    index.reset()
    added = index.add_messages(messages, embeddings=embeddings.tolist())
    print(f"  Indexed {added} messages (collection count: {index.count()})")

    print("Done. Index ready for search.")


if __name__ == "__main__":
    main()