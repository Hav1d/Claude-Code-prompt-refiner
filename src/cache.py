"""Simple file-based cache for summarization results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from .models import CacheEntry


class SummaryCache:
    """File-backed cache for context summaries."""

    def __init__(self, cache_dir: Path, ttl: float = 300.0):
        self._dir = cache_dir / "summaries"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl
        self._memory: dict[str, CacheEntry] = {}

    @staticmethod
    def _make_key(transcript_text: str) -> str:
        return hashlib.sha256(transcript_text.encode()).hexdigest()[:16]

    def _entry_path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def get(self, transcript_text: str) -> Optional[str]:
        """Return cached summary if valid, else None."""
        key = self._make_key(transcript_text)

        # Memory cache first
        entry = self._memory.get(key)
        if entry and not entry.is_expired():
            return entry.summary

        # Disk cache
        path = self._entry_path(key)
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entry = CacheEntry(
                    key=key,
                    summary=data["summary"],
                    created_at=data["created_at"],
                    ttl=self._ttl,
                )
                if not entry.is_expired():
                    self._memory[key] = entry
                    return entry.summary
                else:
                    path.unlink(missing_ok=True)
            except (json.JSONDecodeError, OSError, KeyError):
                path.unlink(missing_ok=True)

        return None

    def put(self, transcript_text: str, summary: str) -> None:
        """Store a summary in cache."""
        import time

        key = self._make_key(transcript_text)
        entry = CacheEntry(key=key, summary=summary, created_at=time.time(), ttl=self._ttl)
        self._memory[key] = entry

        path = self._entry_path(key)
        try:
            path.write_text(
                json.dumps({"summary": summary, "created_at": entry.created_at}),
                encoding="utf-8",
            )
        except OSError:
            pass  # Non-critical

    def clear(self) -> int:
        """Clear all cached entries. Returns count of removed files."""
        count = 0
        for f in self._dir.glob("*.json"):
            f.unlink(missing_ok=True)
            count += 1
        self._memory.clear()
        return count
