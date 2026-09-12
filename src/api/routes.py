"""
FastAPI routes implementing the contract:
  POST /search
  GET  /health
  GET  /participants
  POST /reindex   (admin)
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from config.settings import settings
from src.api.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultOut,
    MatchedMessageOut,
    HealthResponse,
    ParticipantsResponse,
)
from src.data.store import MessageStore
from src.data.index import HybridIndex
from src.data.embeddings import EmbeddingService
from src.query.person_resolver import PersonResolver
from src.query.parser import QueryParser
from src.retrieval.hybrid_search import HybridSearcher
from src.context.window import ContextAssembler


router = APIRouter()

# ---------------------------------------------------------------------------
# Shared services (initialized at startup via lifespan in main.py)
# ---------------------------------------------------------------------------
_store: Optional[MessageStore] = None
_index: Optional[HybridIndex] = None
_searcher: Optional[HybridSearcher] = None
_assembler: Optional[ContextAssembler] = None
_person_resolver: Optional[PersonResolver] = None


def init_services() -> None:
    global _store, _index, _searcher, _assembler, _person_resolver
    _store = MessageStore()
    emb = EmbeddingService()
    _index = HybridIndex(embedding_service=emb)
    _person_resolver = PersonResolver(known_senders=_store.get_senders())
    parser = QueryParser(person_resolver=_person_resolver)
    _searcher = HybridSearcher(index=_index, parser=parser)
    _assembler = ContextAssembler(store=_store)


def get_searcher() -> HybridSearcher:
    if _searcher is None:
        init_services()
    return _searcher


def get_assembler() -> ContextAssembler:
    if _assembler is None:
        init_services()
    return _assembler


def get_store() -> MessageStore:
    if _store is None:
        init_services()
    return _store


def get_index() -> HybridIndex:
    if _index is None:
        init_services()
    return _index


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """
    Main search endpoint.
    Accepts free-text query (English / Hindi / Hinglish).
    Returns ranked results with surrounding context.
    """
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        searcher = get_searcher()
        assembler = get_assembler()

        out = searcher.search(query=query, top_k=req.top_k)
        hits = out["hits"]
        filter_notice = out["filter_notice"]

        if not hits:
            return SearchResponse(
                query=query,
                status="no_matches",
                filter_notice=filter_notice,
                results=[],
                message="No matches found",
            )

        search_results = assembler.assemble(
            hits, context_window=req.context_window
        )

        # Convert to response schema (timestamps → ISO strings)
        results_out = []
        for sr in search_results:
            matched = MatchedMessageOut(
                msg_id=sr.matched_message.msg_id,
                text=sr.matched_message.text,
                sender=sr.matched_message.sender,
                timestamp=sr.matched_message.timestamp.isoformat()
                if hasattr(sr.matched_message.timestamp, "isoformat")
                else str(sr.matched_message.timestamp),
                is_match=True,
            )
            ctx = [
                MatchedMessageOut(
                    msg_id=m.msg_id,
                    text=m.text,
                    sender=m.sender,
                    timestamp=m.timestamp.isoformat()
                    if hasattr(m.timestamp, "isoformat")
                    else str(m.timestamp),
                    is_match=m.is_match,
                )
                for m in sr.context
            ]
            results_out.append(
                SearchResultOut(
                    rank=sr.rank,
                    score=round(sr.score, 4),
                    matched_message=matched,
                    context=ctx,
                )
            )

        return SearchResponse(
            query=query,
            status="ok",
            filter_notice=filter_notice,
            results=results_out,
        )
    except Exception as exc:
        # Never expose stack traces to the Searcher
        return SearchResponse(
            query=query,
            status="error",
            message="Unable to process query. Please try again.",
        )


@router.get("/health", response_model=HealthResponse)
def health():
    store = get_store()
    index = get_index()
    return HealthResponse(
        status="ok",
        message_count=store.count(),
        index_count=index.count(),
    )


@router.get("/participants", response_model=ParticipantsResponse)
def participants():
    store = get_store()
    return ParticipantsResponse(participants=store.get_senders())


@router.post("/reindex")
def reindex():
    """
    Admin-only: rebuild embeddings + Chroma index from the SQLite store.
    """
    try:
        store = get_store()
        index = get_index()
        emb = EmbeddingService()

        messages = store.get_all_messages()
        if not messages:
            return {"status": "ok", "message": "No messages to index", "count": 0}

        index.reset()
        texts = [m.text for m in messages]
        embeddings = emb.embed(texts).tolist()
        count = index.add_messages(messages, embeddings=embeddings)

        # Refresh person resolver
        global _person_resolver, _searcher
        _person_resolver = PersonResolver(known_senders=store.get_senders())
        from src.query.parser import QueryParser
        parser = QueryParser(person_resolver=_person_resolver)
        _searcher = HybridSearcher(index=index, parser=parser)

        return {"status": "ok", "message": "Reindex complete", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))