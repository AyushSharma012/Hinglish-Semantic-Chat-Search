"""
Map natural-language person mentions to known sender identities.
Uses exact + fuzzy matching (rapidfuzz).
"""

from __future__ import annotations

from typing import List, Optional, Dict, Tuple
import re

from rapidfuzz import fuzz, process

from config.settings import settings
from src.data.models import PersonFilter


class PersonResolver:
    """
    Resolves person names appearing in queries to stored sender names.
    """

    def __init__(self, known_senders: Optional[List[str]] = None):
        self.known_senders: List[str] = known_senders or []
        # Lower-case map for quick exact lookup
        self._lower_map: Dict[str, str] = {
            s.lower(): s for s in self.known_senders
        }

    def set_senders(self, senders: List[str]) -> None:
        self.known_senders = list(senders)
        self._lower_map = {s.lower(): s for s in self.known_senders}

    def resolve(self, mention: str) -> Tuple[Optional[str], float]:
        """
        Resolve a single mention.
        Returns (resolved_sender_or_None, confidence 0-100).
        """
        if not mention or not self.known_senders:
            return None, 0.0

        cleaned = mention.strip().lower()
        # Exact
        if cleaned in self._lower_map:
            return self._lower_map[cleaned], 100.0

        # Fuzzy
        match = process.extractOne(
            cleaned,
            list(self._lower_map.keys()),
            scorer=fuzz.WRatio,
        )
        if match and match[1] >= settings.PERSON_FUZZY_THRESHOLD:
            return self._lower_map[match[0]], float(match[1])
        return None, float(match[1]) if match else 0.0

    def extract_and_resolve(self, query: str) -> List[PersonFilter]:
        """
        Simple heuristic extraction of person mentions followed by resolution.
        Looks for common patterns: "Priya said", "what did Rahul", "from Amit", etc.
        Also checks every known sender name appearing in the query.
        """
        filters: List[PersonFilter] = []
        seen = set()

        # 1. Direct presence of known sender names (case-insensitive)
        query_lower = query.lower()
        for sender in self.known_senders:
            if sender.lower() in query_lower and sender not in seen:
                resolved, conf = self.resolve(sender)
                filters.append(
                    PersonFilter(
                        original_mention=sender,
                        resolved_sender=resolved,
                        confidence=conf,
                    )
                )
                seen.add(sender)

        # 2. Common English / Hinglish patterns
        patterns = [
            r"(?:what did|did|from|by|said by|message from|messages of)\s+([A-Za-z\u0900-\u097F]+)",
            r"([A-Za-z\u0900-\u097F]+)\s+(?:said|ne kaha|bol[aei]|bola|boli|kehte)",
            r"(?:priya|rahul|amit|neha|vikram|sonal|arjun|meera)\b",  # fallback known names
        ]
        for pat in patterns:
            for m in re.finditer(pat, query, flags=re.IGNORECASE):
                name = m.group(1) if m.lastindex else m.group(0)
                name = name.strip()
                if name.lower() in seen:
                    continue
                resolved, conf = self.resolve(name)
                filters.append(
                    PersonFilter(
                        original_mention=name,
                        resolved_sender=resolved,
                        confidence=conf,
                    )
                )
                seen.add(name.lower())

        return filters