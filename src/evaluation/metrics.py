"""
Accuracy metrics for the 40-query evaluation set.
"""

from __future__ import annotations

from typing import List, Dict, Any, Set


def hit_at_k(
    retrieved_ids: List[int],
    ground_truth_ids: List[int],
    k: int = 5,
) -> bool:
    """True if any ground-truth message appears in the top-k retrieved ids."""
    gt: Set[int] = set(ground_truth_ids)
    for mid in retrieved_ids[:k]:
        if mid in gt:
            return True
    return False


def compute_accuracy(
    results: List[Dict[str, Any]],
    k: int = 5,
) -> Dict[str, Any]:
    """
    results: list of dicts, each containing at least:
      - query_id
      - is_hard
      - ground_truth_msg_ids
      - retrieved_msg_ids   (ordered by rank)
    """
    total = len(results)
    if total == 0:
        return {
            "overall_accuracy": 0.0,
            "hard_accuracy": 0.0,
            "overall_hits": 0,
            "hard_hits": 0,
            "total": 0,
            "hard_total": 0,
            "gap": 0.0,
        }

    overall_hits = 0
    hard_hits = 0
    hard_total = 0

    for r in results:
        retrieved = r.get("retrieved_msg_ids", [])
        gt = r.get("ground_truth_msg_ids", [])
        is_hard = r.get("is_hard", False)
        hit = hit_at_k(retrieved, gt, k=k)
        if hit:
            overall_hits += 1
        if is_hard:
            hard_total += 1
            if hit:
                hard_hits += 1

    overall_acc = overall_hits / total
    hard_acc = (hard_hits / hard_total) if hard_total else 0.0
    gap = overall_acc - hard_acc

    return {
        "overall_accuracy": round(overall_acc, 4),
        "hard_accuracy": round(hard_acc, 4),
        "overall_hits": overall_hits,
        "hard_hits": hard_hits,
        "total": total,
        "hard_total": hard_total,
        "gap": round(gap, 4),
        "k": k,
    }