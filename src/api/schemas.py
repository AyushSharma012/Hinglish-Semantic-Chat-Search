"""
Pydantic request / response models matching the Frontend–Backend Contract.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Free-text query")
    top_k: int = Field(default=5, ge=1, le=20)
    context_window: int = Field(default=3, ge=0, le=10)


class MatchedMessageOut(BaseModel):
    msg_id: int
    text: str
    sender: str
    timestamp: str  # ISO
    is_match: bool = False


class SearchResultOut(BaseModel):
    rank: int
    score: float
    matched_message: MatchedMessageOut
    context: List[MatchedMessageOut]


class SearchResponse(BaseModel):
    query: str
    status: str  # "ok" | "no_matches" | "error"
    filter_notice: Optional[str] = None
    results: List[SearchResultOut] = Field(default_factory=list)
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    message_count: int = 0
    index_count: int = 0


class ParticipantsResponse(BaseModel):
    participants: List[str]