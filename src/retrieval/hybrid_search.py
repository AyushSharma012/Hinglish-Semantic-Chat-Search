# """
# Hybrid search: semantic vector search + optional person/time filters.
# """

# from __future__ import annotations

# from datetime import datetime
# from typing import List, Optional, Dict, Any

# from config.settings import settings
# from src.data.index import HybridIndex
# from src.data.models import ParsedQuery
# from src.query.parser import QueryParser
# from src.query.embedding import QueryEmbedder
# from src.retrieval.ranking import rank_results


# class HybridSearcher:
#     """
#     End-to-end search path used by the API and evaluation harness.
#     """

#     def __init__(
#         self,
#         index: Optional[HybridIndex] = None,
#         parser: Optional[QueryParser] = None,
#         embedder: Optional[QueryEmbedder] = None,
#     ):
#         self.index = index or HybridIndex()
#         self.parser = parser or QueryParser()
#         self.embedder = embedder or QueryEmbedder()

#     def search(
#         self,
#         query: str,
#         top_k: int = None,
#         min_score: float = None,
#     ) -> Dict[str, Any]:
#         """
#         Full pipeline:
#           1. Parse query → person + time filters
#           2. Embed query
#           3. Hybrid vector + metadata search
#           4. Rank & truncate

#         Returns a dict ready for context assembly:
#           {
#             "parsed": ParsedQuery,
#             "hits": [ {msg_id, text, sender, timestamp, score}, ... ],
#             "filter_notice": str | None
#           }
#         """
#         top_k = top_k or settings.DEFAULT_TOP_K
#         min_score = min_score if min_score is not None else settings.MIN_SIMILARITY_SCORE

#         parsed = self.parser.parse(query)
#         query_emb = self.embedder.embed(parsed.cleaned_query)
#         parsed.embedding = query_emb

#         sender = self.parser.get_primary_sender(parsed)
#         start, end = self.parser.get_time_range(parsed)
#         filter_notice = self.parser.build_filter_notice(parsed)

#         # If person was mentioned but not resolved → pure semantic
#         # (filter_notice already set)

#         hits = self.index.search(
#             query_embedding=query_emb,
#             top_k=top_k,
#             sender=sender,
#             start_time=start,
#             end_time=end,
#         )

#         ranked = rank_results(hits, top_k=top_k, min_score=min_score)

#         return {
#             "parsed": parsed,
#             "hits": ranked,
#             "filter_notice": filter_notice,
#         }

"""
Hybrid search: semantic vector search + optional person/time filters.
"""


from __future__ import annotations


from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from config.settings import settings
from src.data.index import HybridIndex
from src.data.models import ParsedQuery
from src.query.parser import QueryParser
from src.query.embedding import QueryEmbedder
from src.retrieval.ranking import rank_results

logger = logging.getLogger(__name__)


class HybridSearcher:
    """
    End-to-end search path used by the API and evaluation harness.
    
    Design principles:
    - Person & time filters are OPTIONAL with graceful fallback
    - Always returns results via pure semantic search if filters fail
    - Ranking is pure semantic similarity (no keyword hybrid)
    """


    def __init__(
        self,
        index: Optional[HybridIndex] = None,
        parser: Optional[QueryParser] = None,
        embedder: Optional[QueryEmbedder] = None,
    ):
        self.index = index or HybridIndex()
        self.parser = parser or QueryParser()
        self.embedder = embedder or QueryEmbedder()


    def search(
        self,
        query: str,
        top_k: int = None,
        min_score: float = None,
    ) -> Dict[str, Any]:
        """
        Full pipeline:
          1. Parse query → person + time filters
          2. Embed query
          3. Hybrid vector + metadata search (with fallback)
          4. Rank & truncate


        Returns a dict ready for context assembly:
          {
            "parsed": ParsedQuery,
            "hits": [ {msg_id, text, sender, timestamp, score}, ... ],
            "filter_notice": str | None
          }
        """
        top_k = top_k or settings.DEFAULT_TOP_K
        # Lower min_score threshold to avoid filtering out good results
        min_score = min_score if min_score is not None else getattr(settings, 'MIN_SIMILARITY_SCORE', 0.0)


        # 1. Parse query to extract filters
        parsed = self.parser.parse(query)
        
        # 2. Embed query (same model as indexing)
        query_emb = self.embedder.embed(parsed.cleaned_query)
        parsed.embedding = query_emb


        # 3. Extract filters (optional)
        sender = self.parser.get_primary_sender(parsed)
        # start, end = self.parser.get_time_range(parsed)
        start, end = None,None
        filter_notice = self.parser.build_filter_notice(parsed)


        # 4. Try search WITH filters first (get more candidates initially)
        hits = self.index.search(
            query_embedding=query_emb,
            top_k=top_k * 3,  # Get 3x more to allow for filtering
            sender=sender,
            start_time=start,
            end_time=end,
        )


        # 5. CRITICAL: If filters eliminated all results, retry WITHOUT filters
        has_filters = sender is not None or (start is not None and end is not None)
        
        if not hits and has_filters:
            logger.warning(
                f"Filters eliminated all results for query: '{query[:50]}...' "
                f"(sender={sender}, time={start} to {end}). "
                "Retrying pure semantic search."
            )
            
            # Retry with pure semantic search (no filters)
            hits = self.index.search(
                query_embedding=query_emb,
                top_k=top_k * 3,
                sender=None,
                start_time=None,
                end_time=None,
            )
            
            # Update filter notice to inform user
            if filter_notice:
                filter_notice += " (filters dropped — using pure semantic)"
            else:
                filter_notice = "Could not apply filters — using pure semantic search"


        # 6. Rank results by semantic similarity
        ranked = rank_results(hits, top_k=top_k, min_score=min_score)


        # 7. Log for debugging
        if not ranked:
            logger.warning(f"No matches found for query: '{query[:50]}...'")
        else:
            logger.info(f"Query '{query[:30]}...' → {len(ranked)} results (top score: {ranked[0]['score']:.3f})")


        return {
            "parsed": parsed,
            "hits": ranked,
            "filter_notice": filter_notice,
        }