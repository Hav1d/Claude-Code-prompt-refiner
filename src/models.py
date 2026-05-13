"""Data models for prompt refiner."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class UserChoice(Enum):
    """User's action on the refined prompt."""

    ACCEPT = "accept"
    EDIT = "edit"
    ORIGINAL = "original"
    SKIP = "skip"


@dataclass
class RefineResult:
    """Result of a single refinement pass."""

    original_input: str
    context_summary: str
    refined_prompt: str
    final_prompt: str
    user_choice: UserChoice
    duration_ms: float
    error: Optional[str] = None
    degraded: bool = False

    def to_dict(self) -> dict:
        return {
            "original_input": self.original_input,
            "context_summary": self.context_summary,
            "refined_prompt": self.refined_prompt,
            "final_prompt": self.final_prompt,
            "user_choice": self.user_choice.value,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "degraded": self.degraded,
        }


@dataclass
class TranscriptEntry:
    """A single transcript line from Claude Code history."""

    role: str  # "human" or "assistant"
    content: str
    timestamp: Optional[str] = None


@dataclass
class SessionContext:
    """Compressed context from the current session."""

    task: str = ""
    tech_stack: str = ""
    attempted: str = ""
    current_blocker: str = ""
    modifications: str = ""
    constraints: str = ""

    def to_text(self) -> str:
        parts = []
        if self.task:
            parts.append(f"Task: {self.task}")
        if self.tech_stack:
            parts.append(f"Tech stack: {self.tech_stack}")
        if self.attempted:
            parts.append(f"Tried: {self.attempted}")
        if self.current_blocker:
            parts.append(f"Blocker: {self.current_blocker}")
        if self.modifications:
            parts.append(f"Modified: {self.modifications}")
        if self.constraints:
            parts.append(f"Constraints: {self.constraints}")
        return "\n".join(parts) if parts else "(no context)"


@dataclass
class CacheEntry:
    """A cached summarization result."""

    key: str
    summary: str
    created_at: float = field(default_factory=time.time)
    ttl: float = 300.0  # seconds

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl
