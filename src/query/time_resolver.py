"""
Resolve relative / absolute time expressions into concrete datetime ranges.
Uses dateparser + simple heuristics for chat-friendly phrases.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

import dateparser
from dateparser.search import search_dates

from src.data.models import TimeFilter


class TimeResolver:
    """
    Converts expressions like "last month", "yesterday", "last week",
    "in March", "between 1st and 15th March" into (start, end) datetimes.
    """

    # Common relative phrases we want to handle reliably
    RELATIVE_PATTERNS = [
        (r"\blast\s+month\b", "last month"),
        (r"\bprevious\s+month\b", "last month"),
        (r"\blast\s+week\b", "last week"),
        (r"\bprevious\s+week\b", "last week"),
        (r"\byesterday\b", "yesterday"),
        (r"\btoday\b", "today"),
        (r"\blast\s+year\b", "last year"),
        (r"\bpichhle\s+mahine\b", "last month"),  # Hinglish
        (r"\bpichhle\s+hafte\b", "last week"),
        (r"\bkal\b", "yesterday"),
        (r"\baaj\b", "today"),
    ]

    def __init__(self, reference: Optional[datetime] = None):
        """
        reference: the "now" used for relative expressions.
        Defaults to current UTC time; can be overridden for reproducibility.
        """
        self.reference = reference or datetime.utcnow()

    def resolve(self, query: str) -> TimeFilter:
        """
        Try to extract a time expression from the query and resolve it.
        Returns a TimeFilter (resolved=False if nothing found).
        """
        # 1. Try known relative phrases first
        for pattern, label in self.RELATIVE_PATTERNS:
            if re.search(pattern, query, flags=re.IGNORECASE):
                start, end = self._relative_to_range(label)
                return TimeFilter(
                    original_expression=label,
                    start=start,
                    end=end,
                    resolved=True,
                )

        # 2. Let dateparser search for any date-like expressions
        try:
            found = search_dates(
                query,
                settings={
                    "RELATIVE_BASE": self.reference,
                    "PREFER_DATES_FROM": "past",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                },
            )
        except Exception:
            found = None

        if found:
            # Take the first detected date span; expand to a reasonable window
            # if only a single day is found
            expr, dt = found[0]
            # If the expression looks like a month name, expand to whole month
            if re.search(r"\b(january|february|march|april|may|june|july|"
                         r"august|september|october|november|december|"
                         r"jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b",
                         expr, re.I):
                start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # next month
                if start.month == 12:
                    end = start.replace(year=start.year + 1, month=1)
                else:
                    end = start.replace(month=start.month + 1)
                end = end - timedelta(microseconds=1)
            else:
                # single day window
                start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1) - timedelta(microseconds=1)

            return TimeFilter(
                original_expression=expr,
                start=start,
                end=end,
                resolved=True,
            )

        return TimeFilter(original_expression="", resolved=False)

    def _relative_to_range(self, label: str) -> Tuple[datetime, datetime]:
        ref = self.reference
        if label == "yesterday":
            start = (ref - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=1) - timedelta(microseconds=1)
        elif label == "today":
            start = ref.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
        elif label == "last week":
            # previous Monday 00:00 → this Monday 00:00
            weekday = ref.weekday()  # 0 = Monday
            this_monday = ref.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=weekday)
            start = this_monday - timedelta(days=7)
            end = this_monday - timedelta(microseconds=1)
        elif label == "last month":
            first_this = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = first_this - timedelta(microseconds=1)
            start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = last_month_end
        elif label == "last year":
            start = ref.replace(
                year=ref.year - 1, month=1, day=1,
                hour=0, minute=0, second=0, microsecond=0
            )
            end = ref.replace(
                year=ref.year - 1, month=12, day=31,
                hour=23, minute=59, second=59, microsecond=999999
            )
        else:
            # fallback: last 30 days
            end = ref
            start = ref - timedelta(days=30)
        return start, end