"""Summarize conversation history into a compact context block."""

from __future__ import annotations

from typing import Optional

from .config import RefineConfig
from .models import SessionContext, TranscriptEntry
from .transcript_reader import format_transcript_for_context

_SUMMARY_SYSTEM_PROMPT = """You are a context compressor. Given a conversation transcript, extract a structured summary with these fields:

1. **Task**: What is the user currently working on? (1 sentence)
2. **Tech stack**: Languages, frameworks, tools confirmed in use.
3. **Tried**: What approaches or solutions have been attempted.
4. **Blocker**: Current error or blocking issue (exact error text if present).
5. **Modified**: Files or components that have been changed.
6. **Constraints**: Explicit constraints or rules the user has stated.

Rules:
- Be extremely concise. Each field should be 1-2 lines max.
- Preserve exact file paths, error messages, and command names.
- If a field has no relevant info, leave it empty.
- Output as plain text with the format: "Field: value"
"""


async def summarize_history(
    entries: list[TranscriptEntry],
    config: RefineConfig,
    llm_caller: Optional[callable] = None,
) -> SessionContext:
    """Summarize transcript entries into a SessionContext.

    Args:
        entries: Recent transcript entries.
        config: Configuration.
        llm_caller: Async function (system, user, max_tokens) -> str.
                    If None, uses a simple heuristic extraction.

    Returns:
        SessionContext with extracted fields.
    """
    if not entries:
        return SessionContext()

    transcript_text = format_transcript_for_context(entries)

    if llm_caller is None:
        return _heuristic_summarize(entries)

    try:
        summary_text = await llm_caller(
            _SUMMARY_SYSTEM_PROMPT,
            f"Transcript:\n{transcript_text}",
            config.max_summary_tokens,
        )
        return _parse_summary(summary_text)
    except Exception:
        # Fallback to heuristic
        return _heuristic_summarize(entries)


def _heuristic_summarize(entries: list[TranscriptEntry]) -> SessionContext:
    """Fast heuristic summarization without LLM calls."""
    ctx = SessionContext()
    human_msgs = [e.content for e in entries if e.role == "human"]
    assistant_msgs = [e.content for e in entries if e.role == "assistant"]

    if human_msgs:
        ctx.task = human_msgs[-1][:200]

    # Extract error patterns
    for msg in reversed(assistant_msgs):
        lower = msg.lower()
        if any(kw in lower for kw in ["error", "failed", "exception", "traceback"]):
            # Find the error line
            for line in msg.split("\n"):
                if any(kw in line.lower() for kw in ["error", "failed", "exception"]):
                    ctx.current_blocker = line.strip()[:200]
                    break
            break

    # Extract file modifications from assistant messages
    modified_files: list[str] = []
    for msg in assistant_msgs:
        for line in msg.split("\n"):
            if any(kw in line for kw in ["Created", "Modified", "Edited", "Wrote"]):
                if "." in line:
                    modified_files.append(line.strip()[:100])
    if modified_files:
        ctx.modifications = "; ".join(modified_files[-5:])

    return ctx


def _parse_summary(text: str) -> SessionContext:
    """Parse LLM-generated summary text into SessionContext."""
    ctx = SessionContext()
    field_map = {
        "task": "task",
        "tech stack": "tech_stack",
        "tried": "attempted",
        "blocker": "current_blocker",
        "modified": "modifications",
        "constraints": "constraints",
    }
    current_field = None
    current_value: list[str] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        matched = False
        for key, attr in field_map.items():
            if line.lower().startswith(key + ":"):
                if current_field:
                    setattr(ctx, current_field, " ".join(current_value).strip())
                current_field = attr
                current_value = [line.split(":", 1)[1].strip()]
                matched = True
                break
        if not matched:
            # Check if this is a new unknown field (contains ":") — skip it
            if ":" in line and current_field:
                # Unknown field, save current and stop accumulating
                setattr(ctx, current_field, " ".join(current_value).strip())
                current_field = None
                current_value = []
            elif current_field:
                current_value.append(line)

    if current_field:
        setattr(ctx, current_field, " ".join(current_value).strip())

    return ctx
