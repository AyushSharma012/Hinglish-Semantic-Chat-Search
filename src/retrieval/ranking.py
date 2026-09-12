"""
Pure semantic-similarity ranking helpers.
"""

from typing import List, Dict, Any


def rank_results(
    hits: List[Dict[str, Any]],
    top_k: int = 5,
    min_score: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Sort by score descending and truncate.
    Expects each hit to already contain a 'score' key.
    """
    filtered = [h for h in hits if h.get("score", 0.0) >= min_score]
    filtered.sort(key=lambda x: x["score"], reverse=True)
    return filtered[:top_k]