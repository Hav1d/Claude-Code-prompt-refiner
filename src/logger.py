"""Structured logging for prompt refinement sessions."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import RefineResult


class RefineLogger:
    """Logs each refinement session to a structured log file."""

    def __init__(self, log_dir: Path, log_format: str = "jsonl", debug: bool = False):
        self._dir = log_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._format = log_format
        self._debug = debug
        self._session_file = self._dir / f"session-{_timestamp_tag()}.jsonl"

    def log_result(self, result: RefineResult) -> None:
        """Append a refinement result to the session log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result.to_dict(),
        }
        try:
            with open(self._session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def log_debug(self, message: str, data: Optional[dict] = None) -> None:
        """Write a debug-level log line (only when debug_mode is on)."""
        if not self._debug:
            return
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "debug",
            "message": message,
        }
        if data:
            entry["data"] = data
        try:
            with open(self._session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def get_log_path(self) -> Path:
        return self._session_file


def _timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def format_diff(original: str, refined: str) -> str:
    """Generate a simple diff-style comparison between original and refined."""
    orig_lines = original.strip().splitlines()
    ref_lines = refined.strip().splitlines()

    diff_parts: list[str] = []
    max_lines = max(len(orig_lines), len(ref_lines))

    for i in range(max_lines):
        orig = orig_lines[i] if i < len(orig_lines) else ""
        ref = ref_lines[i] if i < len(ref_lines) else ""
        if orig != ref:
            if orig:
                diff_parts.append(f"- {orig}")
            if ref:
                diff_parts.append(f"+ {ref}")
        else:
            diff_parts.append(f"  {orig}")

    return "\n".join(diff_parts)
