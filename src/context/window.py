"""
Fetch ±N surrounding messages for every matched message,
preserving chronological order and original text/sender/timestamp.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from config.settings import settings
from src.data.store import MessageStore
from src.data.models import MatchedMessage, SearchResult


class ContextAssembler:
    def __init__(self, store: Optional[MessageStore] = None):
        self.store = store or MessageStore()

    def assemble(
        self,
        hits: List[Dict[str, Any]],
        context_window: int = None,
    ) -> List[SearchResult]:
        """
        For each hit produce a SearchResult containing the matched message
        and its surrounding context window.
        """
        window = context_window if context_window is not None else settings.DEFAULT_CONTEXT_WINDOW
        results: List[SearchResult] = []

        for rank, hit in enumerate(hits, start=1):
            center_id = hit["msg_id"]
            ctx_msgs = self.store.get_context_window(center_id, window=window)

            context: List[MatchedMessage] = []
            matched: Optional[MatchedMessage] = None

            for m in ctx_msgs:
                is_match = m.msg_id == center_id
                mm = MatchedMessage(
                    msg_id=m.msg_id,
                    text=m.text,
                    sender=m.sender,
                    timestamp=m.timestamp,
                    is_match=is_match,
                )
                context.append(mm)
                if is_match:
                    matched = mm

            # Safety: if the matched message somehow missing from window
            if matched is None:
                matched = MatchedMessage(
                    msg_id=hit["msg_id"],
                    text=hit["text"],
                    sender=hit["sender"],
                    timestamp=hit["timestamp"] if isinstance(hit["timestamp"], str)
                    else hit["timestamp"],
                    is_match=True,
                )
                # ensure it appears in context
                context = [matched]

            results.append(
                SearchResult(
                    rank=rank,
                    score=float(hit["score"]),
                    matched_message=matched,
                    context=context,
                )
            )
        return results