"""
High-level query parser: extracts person & time filters and prepares
a cleaned query string for embedding.
"""

from __future__ import annotations

from typing import List, Optional

from src.data.models import ParsedQuery, PersonFilter, TimeFilter
from src.query.person_resolver import PersonResolver
from src.query.time_resolver import TimeResolver


class QueryParser:
    """
    Orchestrates person resolution + time resolution.
    """

    def __init__(
        self,
        person_resolver: Optional[PersonResolver] = None,
        time_resolver: Optional[TimeResolver] = None,
    ):
        self.person_resolver = person_resolver or PersonResolver()
        self.time_resolver = time_resolver or TimeResolver()

    def parse(self, query: str) -> ParsedQuery:
        if not query or not query.strip():
            return ParsedQuery(
                original_query=query or "",
                cleaned_query="",
            )

        original = query.strip()

        # Person filters
        person_filters = self.person_resolver.extract_and_resolve(original)

        # Time filter
        time_filter = self.time_resolver.resolve(original)

        # Cleaned query: for embedding we keep the full original text.
        # (Removing person/time tokens can sometimes hurt semantic matching;
        #  the filters are applied downstream.)
        cleaned = original

        return ParsedQuery(
            original_query=original,
            cleaned_query=cleaned,
            person_filters=person_filters,
            time_filter=time_filter if time_filter.resolved else None,
        )

    def get_primary_sender(self, parsed: ParsedQuery) -> Optional[str]:
        """Return the first successfully resolved sender, or None."""
        for pf in parsed.person_filters:
            if pf.resolved_sender:
                return pf.resolved_sender
        return None

    def get_time_range(self, parsed: ParsedQuery):
        """Return (start, end) or (None, None)."""
        if parsed.time_filter and parsed.time_filter.resolved:
            return parsed.time_filter.start, parsed.time_filter.end
        return None, None

    def build_filter_notice(self, parsed: ParsedQuery) -> Optional[str]:
        """
        Human-readable notice when a filter could not be resolved.
        """
        notices = []
        for pf in parsed.person_filters:
            if pf.resolved_sender is None:
                notices.append(
                    f"Could not resolve person '{pf.original_mention}'"
                )
        # Time is only added if we detected something but failed (rare)
        if notices:
            return " – ".join(notices) + " – showing pure semantic results"
        return None