"""
Persistent message store using SQLite.
Stores original Hinglish text + sender + timestamp + sequential msg_id.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterable

from config.settings import settings
from src.data.models import Message


class MessageStore:
    """SQLite-backed store for chat messages."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or settings.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    msg_id INTEGER PRIMARY KEY,
                    text TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    thread_id TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)"
            )
            conn.commit()

    def upsert_messages(self, messages: Iterable[Message]) -> int:
        """Insert or replace a batch of messages. Returns count written."""
        count = 0
        with self._get_conn() as conn:
            for msg in messages:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO messages
                    (msg_id, text, sender, timestamp, thread_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        msg.msg_id,
                        msg.text,
                        msg.sender,
                        msg.timestamp.isoformat(),
                        msg.thread_id,
                    ),
                )
                count += 1
            conn.commit()
        return count

    def get_message(self, msg_id: int) -> Optional[Message]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE msg_id = ?", (msg_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_message(row)

    def get_messages_by_ids(self, msg_ids: List[int]) -> List[Message]:
        if not msg_ids:
            return []
        placeholders = ",".join("?" * len(msg_ids))
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM messages WHERE msg_id IN ({placeholders}) ORDER BY msg_id",
                msg_ids,
            ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def get_context_window(
        self, center_msg_id: int, window: int = 3
    ) -> List[Message]:
        """
        Return messages in [center - window, center + window] inclusive,
        ordered chronologically (by msg_id).
        """
        start_id = max(1, center_msg_id - window)
        end_id = center_msg_id + window
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE msg_id BETWEEN ? AND ?
                ORDER BY msg_id
                """,
                (start_id, end_id),
            ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def get_all_messages(self) -> List[Message]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages ORDER BY msg_id"
            ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def get_messages_in_range(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        sender: Optional[str] = None,
    ) -> List[Message]:
        clauses = []
        params: List[Any] = []
        if start is not None:
            clauses.append("timestamp >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp <= ?")
            params.append(end.isoformat())
        if sender is not None:
            clauses.append("sender = ?")
            params.append(sender)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM messages{where} ORDER BY msg_id", params
            ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def count(self) -> int:
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()
        return int(row["c"])

    def get_senders(self) -> List[str]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT sender FROM messages ORDER BY sender"
            ).fetchall()
        return [r["sender"] for r in rows]

    def get_time_bounds(self) -> tuple[Optional[datetime], Optional[datetime]]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT MIN(timestamp) AS mn, MAX(timestamp) AS mx FROM messages"
            ).fetchone()
        if row is None or row["mn"] is None:
            return None, None
        return (
            datetime.fromisoformat(row["mn"]),
            datetime.fromisoformat(row["mx"]),
        )

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> Message:
        return Message(
            msg_id=row["msg_id"],
            text=row["text"],
            sender=row["sender"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            thread_id=row["thread_id"],
        )

    def load_from_json(self, json_path: Path) -> int:
        """Load messages from a JSON file (list of dicts)."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        messages = []
        for item in data:
            ts = item["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            messages.append(
                Message(
                    msg_id=item["msg_id"],
                    text=item["text"],
                    sender=item["sender"],
                    timestamp=ts,
                    thread_id=item.get("thread_id"),
                )
            )
        return self.upsert_messages(messages)