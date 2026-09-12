#!/usr/bin/env python3
"""
CLI entry-point for the 40-query evaluation harness.
Reports overall accuracy and hard (zero-word-overlap) accuracy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import settings
from src.data.store import MessageStore
from src.data.index import HybridIndex
from src.data.embeddings import EmbeddingService
from src.query.person_resolver import PersonResolver
from src.query.parser import QueryParser
from src.retrieval.hybrid_search import HybridSearcher
from src.evaluation.harness import EvaluationHarness


def main():
    parser = argparse.ArgumentParser(description="Run evaluation on 40 labeled queries")
    parser.add_argument("--top-k", type=int, default=5, help="Top-k for hit@k")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional path to write full JSON results",
    )
    args = parser.parse_args()

    # Wire services
    store = MessageStore()
    if store.count() == 0:
        print("Message store is empty. Run scripts/build_index.py first.")
        sys.exit(1)

    emb = EmbeddingService()
    index = HybridIndex(embedding_service=emb)
    if index.count() == 0:
        print("Chroma index is empty. Run scripts/build_index.py first.")
        sys.exit(1)

    person_resolver = PersonResolver(known_senders=store.get_senders())
    qparser = QueryParser(person_resolver=person_resolver)
    searcher = HybridSearcher(index=index, parser=qparser)

    harness = EvaluationHarness(searcher=searcher, top_k=args.top_k)
    print(f"Running evaluation (top_k={args.top_k})…")
    result = harness.run()
    harness.print_report(result)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()