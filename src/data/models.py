"""
Core data models used across the system.
"""

from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single chat message as stored in the system."""

    msg_id: int = Field(..., description="Unique sequential message ID")
    text: str = Field(..., description="Original unaltered Hinglish text")
    sender: str = Field(..., description="Participant / sender name")
    timestamp: datetime = Field(..., description="Exact timestamp of the message")
    # Optional extra metadata
    thread_id: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MatchedMessage(BaseModel):
    """A matched message with its metadata (used inside results)."""

    msg_id: int
    text: str
    sender: str
    timestamp: datetime
    is_match: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SearchResult(BaseModel):
    """One ranked search hit with surrounding context."""

    rank: int
    score: float
    matched_message: MatchedMessage
    context: List[MatchedMessage]


class QueryResult(BaseModel):
    """Full response returned by the search system."""

    query: str
    status: str  # "ok" | "no_matches" | "error"
    filter_notice: Optional[str] = None
    results: List[SearchResult] = Field(default_factory=list)
    message: Optional[str] = None  # used for "No matches found" or errors


class EvaluationQuery(BaseModel):
    """Ground-truth evaluation query."""

    query_id: int
    query: str
    ground_truth_msg_ids: List[int]
    is_hard: bool = False  # True if zero-word-overlap
    category: str = "meaning"  # meaning | person | time | combined
    notes: Optional[str] = None


class PersonFilter(BaseModel):
    """Resolved person filter."""

    original_mention: str
    resolved_sender: Optional[str] = None
    confidence: float = 0.0


class TimeFilter(BaseModel):
    """Resolved time range filter."""

    original_expression: str
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    resolved: bool = False


class ParsedQuery(BaseModel):
    """Internal representation after query parsing."""

    original_query: str
    cleaned_query: str  # query with person/time tokens optionally removed
    person_filters: List[PersonFilter] = Field(default_factory=list)
    time_filter: Optional[TimeFilter] = None
    embedding: Optional[List[float]] = None