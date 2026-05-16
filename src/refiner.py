"""Core prompt refinement logic."""

from __future__ import annotations

import re
from typing import Optional

import sys

from .config import RefineConfig
from .models import SessionContext


_CYAN = "\033[36m"
_RESET = "\033[0m"


def _refiner_log(message: str) -> None:
    import datetime, os
    print(f"{_CYAN}[prompt-refiner]{_RESET} {message}", file=sys.stderr)
    try:
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hook-debug.log")
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"{datetime.datetime.now().isoformat()} {message}\n")
    except Exception:
        pass

_REFINE_SYSTEM_PROMPT = """
Rewrite the user's input into a clearer, more actionable prompt for Claude Code.

Rules:
- Output ONLY the rewritten prompt. No explanations, no prefacing, no quotes, no markdown fences.
- Preserve the user's original intent, language, tone, and urgency as much as possible.
- Use the conversation history to understand what the user has been doing, what files they've been working on, what errors they've encountered, and what they're trying to accomplish.
- Use the provided context to resolve vague references such as "this project", "it", "that file", "the bug", or "continue".
- Prefer exact names, paths, symbols, task goals, and constraints mentioned in the context when they are relevant.
- Do NOT invent facts, requirements, files, tools, or outcomes that are not supported by the input or context.
- Do NOT answer the user's task; only rewrite it.
- Do NOT add unnecessary detail, but do make implicit goals explicit when the context supports them.
- If the input is already clear and actionable, return it with minimal changes.
- If the input is a greeting or casual small talk, return it unchanged.
- If the input is ambiguous and the context does not resolve it, rewrite it as a concise request for clarification rather than guessing.
- Keep the result concise, direct, and execution-oriented.
"""
# Rewrite user input into a clearer prompt for Claude Code. Rules:
# - Output ONLY the rewritten prompt. No explanation.
# - Greetings (hello/hi/你好) → return unchanged.
# - Vague input → infer intent, rewrite as clear task.
# - Same language in, same language out.

def should_refine(input_text: str, config: RefineConfig) -> bool:
    """Determine whether the input should go through refinement.

    Returns False if:
    - Input matches a skip command
    - Input matches an ignore pattern
    - Input is too short to meaningfully refine
    """
    stripped = input_text.strip()

    # Skip commands
    for cmd in config.skip_commands:
        if stripped.lower().startswith(cmd.lower()):
            return False

    # Ignore patterns
    for pattern in config.ignore_patterns:
        if re.match(pattern, stripped):
            return False

    # Single-letter A/E/O/S choice responses — pass through
    if re.match(r"^[aeos]$", stripped, re.I):
        return False

    # Too short to meaningfully refine
    if len(stripped) < 5:
        return False

    return True


# def build_refine_prompt(
#     raw_input: str,
#     context: SessionContext,
#     config: RefineConfig,
# ) -> tuple[str, str]:
#     """Build the system and user prompts for the refinement LLM call.

#     Returns:
#         (system_prompt, user_prompt) tuple
#     """
#     system_prompt = _REFINE_SYSTEM_PROMPT

#     parts = []
#     context_text = context.to_text()
#     if context_text and context_text != "(no context)":
#         parts.append(f"Context:\n{context_text}")
#     parts.append(f"Input: {raw_input}")
#     user_prompt = "\n\n".join(parts)

#     return system_prompt, user_prompt
def build_refine_prompt(
    raw_input: str,
    context: SessionContext,
    config: RefineConfig,
    transcript_text: str = "",
) -> tuple[str, str]:
    system_prompt = _REFINE_SYSTEM_PROMPT

    context_text = context.to_text()
    parts = []

    if transcript_text:
        parts.append(f"Conversation history:\n{transcript_text}")
    if context_text and context_text != "(no context)":
        parts.append(f"Context:\n{context_text}")
    parts.append(f"Input: {raw_input}")

    user_prompt = "\n\n".join(parts)

    _refiner_log("=== REFINE PROMPT BUILT ===")
    _refiner_log(f"TRANSCRIPT ({len(transcript_text)} chars): {transcript_text[:200]!r}...")
    _refiner_log(f"CONTEXT ONLY:\n{context_text}")
    _refiner_log(f"SYSTEM PROMPT:\n{system_prompt}")
    _refiner_log(f"USER PROMPT:\n{user_prompt}")
    _refiner_log("=== REFINE PROMPT OVER ===")

    return system_prompt, user_prompt

def apply_prefix_suffix(prompt: str, config: RefineConfig) -> str:
    """Apply configured prefix and suffix to the final prompt."""
    parts = []
    if config.prefix:
        parts.append(config.prefix.strip())
    parts.append(prompt)
    if config.suffix:
        parts.append(config.suffix.strip())
    return "\n\n".join(parts)


# ── Heuristic patterns ────────────────────────────────────────────

# Greetings / casual small talk that should NOT trigger an LLM call.
# These are pass-through: the original prompt is returned unchanged.
_GREETING_PATTERN = (
    r"^(hello|hi|hey|yo|sup|hola|bonjour)\b"
    r"|^(你好[呀啊嘛哦]?|您好[啊嘛哦]?|嗨|哈喽|喂|在吗[？?]?)"
    r"|^(你是谁[呀啊嘛]?|你叫什么[名字]?|你能做[什么啥]|你会[什么啥]|你叫什么名字)"
    r"|^(早上好|晚上好|下午好|大家好|各位好)"
    r"|^(谢谢|多谢|感谢|thanks|thank you|thx)\b"
)


def _heuristic_refine(raw_input: str) -> str | None:
    """Apply rule-based refinement without calling LLM.

    Returns refined text if a rule applies, None if LLM should be called.
    """
    stripped = raw_input.strip()

    # Greetings / small talk / thanks → pass through unchanged
    if re.match(rf"{_GREETING_PATTERN}\s*[!！。.，,？?~～…]*\s*$", stripped, re.I | re.X):
        return stripped

    # Already structured (has Goal:/Context: prefix) → return unchanged
    if re.match(r"^(Goal|Context|Task|请|帮我|修改|修复|实现|添加|删除|检查|解释|分析)", stripped):
        return stripped

    return None


async def refine_prompt(
    raw_input: str,
    context: SessionContext,
    config: RefineConfig,
    llm_caller: Optional[callable] = None,
    transcript_text: str = "",
) -> tuple[str, bool]:
    """Refine a raw user input into a structured prompt.

    Args:
        raw_input: The user's original input.
        context: Compressed session context.
        config: Configuration.
        llm_caller: Async function (system, user, max_tokens) -> str.
        transcript_text: Raw conversation transcript for context.

    Returns:
        (refined_prompt, was_degraded) tuple.
    """
    # Try heuristic first (no LLM needed)
    heuristic = _heuristic_refine(raw_input)
    if heuristic is not None:
        return heuristic, False

    if llm_caller is None:
        return raw_input, True

    system_prompt, user_prompt = build_refine_prompt(raw_input, context, config, transcript_text)

    try:
        result = await llm_caller(
            system_prompt,
            user_prompt,
            config.max_refined_tokens,
        )
        _refiner_log(f"LLM raw response ({len(result)} chars): {result[:200]!r}")
        result = result.strip()

        # Sanity check: if LLM returned empty, conversational, or garbage
        if not result or len(result) < 3:
            return raw_input, True

        # Reject tool calls — model tried to execute instead of rewrite
        if any(tag in result for tag in ("<tool_call>", "<function=", "</tool_call>", "<|tool")):
            _refiner_log("rejected: model returned tool call instead of refined prompt")
            return raw_input, True

        # Reject conversational responses (model answered instead of rewriting)
        lower = result.lower()
        conversational_markers = [
            "i'd be happy", "i can help", "let me help", "sure,",
            "当然", "好的", "没问题", "我可以帮", "请提供",
            "please provide", "could you", "can you",
            "i need more", "需要更多",
        ]
        if any(m in lower for m in conversational_markers):
            return raw_input, True

        # Reject if result is much longer than input (model hallucinated content).
        # For very short inputs (<50 chars), allow up to 500 chars of expansion.
        # For longer inputs, use 3x multiplier with a 200-char absolute floor.
        max_len = max(len(raw_input) * 3, 200) if len(raw_input) < 50 else len(raw_input) * 3
        if len(result) > max_len:
            _refiner_log(f"rejected: output too long ({len(result)} > {max_len})")
            return raw_input, True

        return result, False
    except Exception:
        return raw_input, True
