"""
Central configuration for Hinglish Semantic Chat Search.
All tunable parameters live here.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project root (resolved relative to this file)
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

    # Embedding
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 64
    EMBEDDING_DIM: int = 384  # MiniLM-L12-v2 output dim

    # Paths
    DATA_DIR: Path = PROJECT_ROOT / "data"
    RAW_DATA_PATH: Path = DATA_DIR / "raw" / "messages.json"
    DB_PATH: Path = DATA_DIR / "processed" / "messages.db"
    CHROMA_PATH: Path = DATA_DIR / "processed" / "chroma"
    EVAL_QUERIES_PATH: Path = DATA_DIR / "evaluation" / "queries.json"
    PARTICIPANTS_PATH: Path = DATA_DIR / "processed" / "participants.json"

    # Search defaults
    DEFAULT_TOP_K: int = 5
    DEFAULT_CONTEXT_WINDOW: int = 3
    MAX_TOP_K: int = 20
    MAX_CONTEXT_WINDOW: int = 10

    # Chroma collection name
    CHROMA_COLLECTION: str = "chat_messages"

    # Similarity threshold (cosine). Results below this may be filtered.
    MIN_SIMILARITY_SCORE: float = 0.25

    # Person resolution
    PERSON_FUZZY_THRESHOLD: int = 80  # rapidfuzz score

    def ensure_dirs(self) -> None:
        """Create required directories if they do not exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "processed").mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "evaluation").mkdir(parents=True, exist_ok=True)
        self.CHROMA_PATH.mkdir(parents=True, exist_ok=True)


# Singleton
settings = Settings()
settings.ensure_dirs()