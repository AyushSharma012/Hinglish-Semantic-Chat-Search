"""
Evaluation harness: runs all 40 labeled queries and reports
overall accuracy + hard (zero-word-overlap) accuracy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import settings
from src.data.models import EvaluationQuery
from src.retrieval.hybrid_search import HybridSearcher
from src.evaluation.metrics import compute_accuracy


class EvaluationHarness:
    def __init__(
        self,
        searcher: Optional[HybridSearcher] = None,
        queries_path: Optional[Path] = None,
        top_k: int = 5,
    ):
        self.searcher = searcher or HybridSearcher()
        self.queries_path = Path(queries_path or settings.EVAL_QUERIES_PATH)
        self.top_k = top_k

    def load_queries(self) -> List[EvaluationQuery]:
        if not self.queries_path.exists():
            raise FileNotFoundError(
                f"Evaluation queries not found at {self.queries_path}. "
                "Run scripts/generate_synthetic_data.py first."
            )
        with open(self.queries_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [EvaluationQuery(**q) for q in raw]

    def run(self) -> Dict[str, Any]:
        queries = self.load_queries()
        per_query: List[Dict[str, Any]] = []

        for eq in queries:
            out = self.searcher.search(eq.query, top_k=self.top_k)
            hits = out["hits"]
            retrieved_ids = [h["msg_id"] for h in hits]

            per_query.append(
                {
                    "query_id": eq.query_id,
                    "query": eq.query,
                    "is_hard": eq.is_hard,
                    "category": eq.category,
                    "ground_truth_msg_ids": eq.ground_truth_msg_ids,
                    "retrieved_msg_ids": retrieved_ids,
                    "scores": [h["score"] for h in hits],
                    "filter_notice": out.get("filter_notice"),
                }
            )

        metrics = compute_accuracy(per_query, k=self.top_k)
        return {
            "metrics": metrics,
            "per_query": per_query,
        }

    def print_report(self, result: Dict[str, Any]) -> None:
        m = result["metrics"]
        print("=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)
        print(f"Total queries          : {m['total']}")
        print(f"Hard (zero-overlap)    : {m['hard_total']}")
        print(f"Top-k                  : {m['k']}")
        print("-" * 60)
        print(f"Overall accuracy       : {m['overall_accuracy']:.2%}  "
              f"({m['overall_hits']}/{m['total']})")
        print(f"Hard-query accuracy    : {m['hard_accuracy']:.2%}  "
              f"({m['hard_hits']}/{m['hard_total']})")
        print(f"Gap (overall − hard)   : {m['gap']:.2%}")
        print("=" * 60)

        # Show failures for debugging
        failures = [
            r for r in result["per_query"]
            if not set(r["retrieved_msg_ids"][: self.top_k]) & set(r["ground_truth_msg_ids"])
        ]
        if failures:
            print("\nFailed queries:")
            for f in failures:
                tag = " [HARD]" if f["is_hard"] else ""
                print(f"  #{f['query_id']}{tag}: {f['query']}")
                print(f"       GT: {f['ground_truth_msg_ids']}  got: {f['retrieved_msg_ids'][:5]}")