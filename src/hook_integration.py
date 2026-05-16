"""Claude Code hook integration module.

Handles the UserPromptSubmit hook event.
Strategy:
  1. Refine the prompt via LLM.
  2. Try to open the real terminal (CONOUT$/CONIN$ or /dev/tty) for interactive review.
  3. If TUI is available: present A/E/O/S choices, wait for user input, then output.
  4. If TUI is NOT available (Windows hook mode):
     a. First invocation: refine prompt, save to temp file, BLOCK with comparison.
     b. Second invocation: user resubmits choice (a/e/o/s), return chosen prompt.
  5. Never silently pass through without telling the user why.

Output format (Claude Code official):
    {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}
    {"decision": "block", "reason": "..."}  — blocks prompt, user must resubmit
Pass-through: empty stdout.
"""

from __future__ import annotations

import difflib
import json
import os
import sys
import tempfile
import time
from typing import Any, Optional

from .config import RefineConfig, load_config
from .hook_terminal import (
    open_terminal_in,
    open_terminal_out,
    terminal_unavailable_reason,
    tui_refine_review,
)
from .refiner import should_refine

# Temp file for pending refinement (Windows fallback two-step flow)
_PENDING_FILE = os.path.join(tempfile.gettempdir(), "prompt-refiner-pending.json")
_PENDING_TTL = 300  # seconds — pending file expires after 5 minutes


def parse_hook_payload(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def extract_prompt_from_hook(payload: dict[str, Any]) -> str:
    return payload.get("prompt", "")


def build_hook_response(
    refined_prompt: str,
    event_name: str = "UserPromptSubmit",
) -> dict[str, Any]:
    if not refined_prompt:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": refined_prompt,
        }
    }


async def handle_hook(
    payload: dict[str, Any],
    config: Optional[RefineConfig] = None,
    event_name: str = "UserPromptSubmit",
) -> dict[str, Any] | None:
    """Process a Claude Code hook event.

    Flow:
      1. Check for pending refinement (user's choice from previous block).
      2. If no pending: refine the prompt via LLM.
      3. Try interactive TUI review (terminal I/O).
      4. If TUI unavailable: save pending + BLOCK with comparison.
      5. Return hookSpecificOutput dict, decision dict, or None to pass through.

    Returns None (pass through) when:
      - Empty prompt
      - Skip command / ignore pattern
      - No API key available
      - LLM call failed
      - User chose ORIGINAL or SKIP in TUI
      - Refinement produced no meaningful change and user didn't accept
    """
    if config is None:
        config = load_config()

    raw_input = extract_prompt_from_hook(payload)
    _stderr_log(f"prompt={raw_input!r}")
    if not raw_input:
        return None

    # --- Step 2 of two-step flow: user resubmitted after BLOCK ---
    pending = _read_pending()
    if pending is not None:
        return _handle_user_choice(raw_input, pending, config)

    if not should_refine(raw_input, config):
        _stderr_log("skipped: should_refine=False")
        return None

    # --- Credential check ---
    from .credentials import resolve_for_config
    api_key, _ = resolve_for_config(config)
    if not api_key:
        _stderr_log("skipped: no API key")
        return None

    # --- Context gathering (transcript + summary, heuristic-only for speed) ---
    from .llm import make_llm_caller
    from .models import SessionContext
    from .refiner import apply_prefix_suffix, refine_prompt
    from .summarizer import _heuristic_summarize
    from .transcript_reader import format_transcript_for_context, read_transcript

    _stderr_log("reading transcript...")
    entries = read_transcript(
        max_entries=config.history_lines,
        explicit_path=payload.get("transcript_path", config.transcript_path),
    )

    context = SessionContext()
    transcript_text = ""
    if entries:
        transcript_text = format_transcript_for_context(entries)
        if transcript_text:
            # Heuristic-only summarization in hook path (no extra LLM call)
            _stderr_log("summarizing transcript (heuristic, fast)...")
            context = _heuristic_summarize(entries)
    _stderr_log(f"transcript: {len(transcript_text)} chars, {len(entries)} entries")

    # --- LLM Refinement (single LLM call, the only API call in hooks) ---
    _stderr_log("calling LLM to refine...")
    try:
        llm_caller = make_llm_caller(config)
        refined, degraded = await refine_prompt(raw_input, context, config, llm_caller=llm_caller, transcript_text=transcript_text)
    except Exception as e:
        _stderr_log(f"LLM failed: {e}")
        return None

    _stderr_log(f"refined={refined!r}  degraded={degraded}")

    # --- If no change, pass through ---
    if raw_input.strip() == refined.strip():
        _stderr_log("skipped: no change")
        return None

    context_text = context.to_text() if context else ""

    # --- Decide: TUI or fallback ---
    # In Claude Code hooks, stdin is always a pipe (JSON payload). On Windows,
    # the subprocess cannot read from CONIN$ — readline() blocks forever.
    # We try TUI only when running interactively (stdin is a real terminal).
    # In hook mode, we go straight to fallback to guarantee fast completion.
    if sys.stdin.isatty():
        # Running interactively — try real terminal TUI
        term_out = open_terminal_out()
        term_in = open_terminal_in()

        if term_out is not None and term_in is not None:
            _stderr_log("TUI available — showing interactive review")
            try:
                choice, edited = tui_refine_review(
                    term_out, term_in,
                    original=raw_input,
                    refined=refined,
                    context_summary=context_text,
                    degraded=degraded,
                )
            except (OSError, EOFError):
                _stderr_log("TUI I/O error — falling back to additionalContext")
                choice, edited = _fallback_via_context(raw_input, refined, degraded)
            finally:
                _close_handles(term_out, term_in)

            _stderr_log(f"user choice: {choice}")

            if choice == "accept":
                return build_hook_response(
                    _make_accepted_context(apply_prefix_suffix(refined, config)),
                    event_name,
                )
            elif choice == "edit":
                return build_hook_response(
                    _make_accepted_context(apply_prefix_suffix(edited, config)),
                    event_name,
                )
            else:
                return None  # original or skip — pass through
        else:
            _close_handles(term_out, term_in)

    # --- Hook mode (pipe stdin) or TUI unavailable ---
    # Two-step flow: save pending + BLOCK with comparison.
    # User sees the comparison, resubmits with their choice (a/e/o/s).
    reason = terminal_unavailable_reason()
    _stderr_log(f"Hook mode: interactive review unavailable ({reason})")

    _write_pending(raw_input, refined, degraded)
    _stderr_log("Saved pending refinement, blocking prompt for user choice.")

    block_reason = _make_block_reason(raw_input, refined, degraded)
    return {"decision": "block", "reason": block_reason}


# --- Pending file management ---

def _write_pending(original: str, refined: str, degraded: bool) -> None:
    """Save pending refinement to temp file for two-step flow."""
    data = {"original": original, "refined": refined, "degraded": degraded, "created_at": time.time()}
    try:
        with open(_PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError as e:
        _stderr_log(f"Failed to write pending file: {e}")


def _read_pending() -> dict[str, Any] | None:
    """Read pending refinement from temp file. Returns None if not found or expired."""
    try:
        if not os.path.exists(_PENDING_FILE):
            return None
        with open(_PENDING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "original" not in data or "refined" not in data:
            return None
        # Check expiration
        created_at = data.get("created_at", 0)
        if time.time() - created_at > _PENDING_TTL:
            _stderr_log("Pending file expired, clearing")
            _clear_pending()
            return None
        return data
    except (OSError, json.JSONDecodeError):
        return None


def _clear_pending() -> None:
    """Remove the pending file after user makes a choice."""
    try:
        if os.path.exists(_PENDING_FILE):
            os.remove(_PENDING_FILE)
    except OSError:
        pass


def _handle_user_choice(
    user_input: str,
    pending: dict[str, Any],
    config: RefineConfig,
) -> dict[str, Any] | None:
    """Process the user's choice from the two-step BLOCK flow.

    User resubmits after seeing the comparison. Their input is parsed as:
      a/accept → use refined
      e/edit   → use refined (user can edit in Claude Code)
      o/original → use original
      s/skip   → use original
      multi-char input → treat as new prompt (clear pending, refine it)
      single invalid char → re-block with the comparison
    """
    from .refiner import apply_prefix_suffix

    choice = user_input.strip().lower()
    original = pending["original"]
    refined = pending["refined"]

    _stderr_log(f"Processing user choice: {choice!r}")

    if choice in ("a", "accept"):
        _clear_pending()
        final = apply_prefix_suffix(refined, config)
        _stderr_log(f"User accepted refined: {final!r}")
        return build_hook_response(_make_accepted_context(final))

    if choice in ("e", "edit"):
        _clear_pending()
        final = apply_prefix_suffix(refined, config)
        _stderr_log(f"User chose edit (refined shown): {final!r}")
        return build_hook_response(
            f"[PROMPT-REFINER: EDIT MODE]\n\n"
            f"The user chose to edit the refined prompt. Show them this prompt and ask them to edit it:\n\n"
            f"{final}"
        )

    if choice in ("o", "original"):
        _clear_pending()
        _stderr_log("User chose original — passing through")
        return None  # pass through original

    # If input is longer than a single character, it's a new prompt, not a choice.
    # Clear pending and let the hook process it as a fresh input.
    if len(choice) > 1:
        _clear_pending()
        _stderr_log(f"User submitted new prompt (not a choice), clearing pending: {choice[:80]!r}")
        return None  # pass through — hook will re-trigger and refine this new prompt

    # Single character but not a valid choice — re-block
    _stderr_log(f"Invalid choice {choice!r}, re-blocking")
    _write_pending(original, refined, pending.get("degraded", False))
    block_reason = _make_block_reason(original, refined, pending.get("degraded", False))
    return {"decision": "block", "reason": block_reason}


def _close_handles(out, inp) -> None:
    for h in (out, inp):
        if h is not None:
            try:
                h.close()
            except OSError:
                pass


def _make_accepted_context(prompt: str) -> str:
    """Build additionalContext when user has already accepted the refinement via TUI."""
    return (
        f"[PROMPT-REFINER: USER APPROVED]\n\n"
        f"The user's message (e.g. 'a') is a selection choice from the prompt refiner, "
        f"NOT the actual prompt. The real prompt the user wants you to process is:\n\n"
        f"{prompt}\n\n"
        f"Process THIS prompt as if the user typed it directly. "
        f"Do NOT respond to the selection letter. Do NOT re-display the comparison."
    )


def _make_block_reason(
    original: str,
    refined: str,
    degraded: bool,
) -> str:
    """Build the block reason shown to the user when TUI is unavailable.

    This is displayed by Claude Code when decision=block is returned.
    The user sees this and resubmits with their choice (a/e/o/s).
    """
    degraded_note = "\n(refinement model was degraded, results may be minimal)\n" if degraded else ""

    return (
        f"Prompt Refiner has optimized your input.\n"
        f"{degraded_note}\n"
        f"--- Original ---\n{original.strip()}\n\n"
        f"--- Refined ---\n{refined.strip()}\n\n"
        f"Choose one:\n"
        f"  a = Accept refined\n"
        f"  e = Edit refined\n"
        f"  o = Use original\n\n"
        f"Type your choice and resubmit."
    )


# ANSI color codes
_CYAN = "\033[36m"
_RESET = "\033[0m"


def _stderr_log(message: str) -> None:
    """Log to stderr and debug file for visibility."""
    import datetime, os
    print(f"{_CYAN}[prompt-refiner]{_RESET} {message}", file=sys.stderr)
    try:
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hook-debug.log")
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"{datetime.datetime.now().isoformat()} {message}\n")
    except Exception:
        pass
