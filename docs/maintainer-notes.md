# Maintainer Notes

Implementation notes for future maintainers and AI models taking over this project. Covers design decisions, known gotchas, and areas that may need attention.

## Design Decisions

### Why `hook_entry.py` exists separately from `app.py`

`app.py` has a `hook` command (`prf hook UserPromptSubmit`) that reads stdin with `sys.stdin.read()`. This works when run directly but **blocks forever** when Claude Code invokes it as a hook subprocess, because Claude Code may not close stdin.

`hook_entry.py` was created as a dedicated `__main__` module with char-by-char stdin reading using `json.JSONDecoder.raw_decode()`. This detects complete JSON without waiting for EOF.

**If you need to change stdin reading**: The char-by-char approach is the only reliable method. `sys.stdin.read()`, `sys.stdin.readlines()`, and `select.select()` all have issues with Claude Code's pipe behavior.

### Why no TUI in hook mode

The Rich TUI (`ui.py`) uses `CONIN$`/`CONOUT$` for terminal I/O. In Claude Code's hook subprocess on Windows, `CONIN$` blocks indefinitely. This was verified by testing:
- Direct execution: `CONIN$`/`CONOUT$` work fine
- Claude Code subprocess: `CONIN$` blocks forever

The `hook_terminal.py` module has utilities for `CONIN$`/`CONOUT$` bypass, but they're not used in the main flow. They're kept for potential future use if the blocking issue is resolved.

### Why `additionalContext` instead of prompt replacement

Claude Code hooks cannot replace the user's prompt. They can only:
1. Inject `additionalContext` (adds information)
2. `block` with a `reason` (prevents processing)
3. Empty stdout (pass through, no modification)

Prompt Refiner uses option 1: injects both original and refined prompts as context, with instructions for Claude to ask the user which version to use.

### Why `project_rules` / `user_rules` are NOT passed to refinement LLM

These fields exist in `prompt-config.json` but are NOT included in the refinement prompt. Previously, the `user_rules` contained "When unsure, ask for clarification rather than guessing" — this caused the LLM to answer questions instead of rewriting prompts.

The refinement system prompt (`_REFINE_SYSTEM_PROMPT` in `refiner.py`) is deliberately minimal and focused on rewriting, not answering.

### Why conversational response rejection exists

Some models (especially weaker ones like `mimo-v2.5-pro`) answer questions instead of rewriting prompts. The refiner has a safety net:

```python
conversational_markers = [
    "i'd be happy", "i can help", "let me help", "sure,",
    "当然", "好的", "没问题", "我可以帮", "请提供",
    "please provide", "could you", "can you",
    "i need more", "需要更多",
]
if any(m in lower for m in conversational_markers):
    return raw_input, True  # Fall back to original
```

This rejects LLM outputs that look like answers rather than rewrites.

### Why `-X utf8` is required on Windows

Without `-X utf8`, Python on Windows uses the system's default encoding (often GBK/cp936 in Chinese Windows). When Claude Code pipes UTF-8 JSON to stdin, the encoding mismatch produces garbled characters.

## Module Responsibilities

| Module | Lines | Responsibility | Depends On |
|--------|-------|----------------|------------|
| `app.py` | ~465 | CLI commands, TUI flow | everything |
| `config.py` | ~256 | Config loading, merging | pydantic |
| `credentials.py` | ~94 | API key resolution | config |
| `refiner.py` | ~156 | Core refinement logic | config, models |
| `llm.py` | ~104 | LLM caller factory | config, credentials, providers |
| `summarizer.py` | ~139 | Context compression | config, models |
| `transcript_reader.py` | ~168 | Transcript parsing | models |
| `hook_integration.py` | ~152 | Hook logic | config, credentials, refiner, llm |
| `hook_entry.py` | ~99 | Hook __main__ | hook_integration |
| `hook_terminal.py` | ~N/A | CONIN$/CONOUT$ utils | (unused in main flow) |
| `ui.py` | ~N/A | Rich TUI | rich |
| `executor.py` | ~N/A | claude CLI submission | subprocess |
| `cache.py` | ~N/A | Summary caching | pathlib |
| `logger.py` | ~N/A | Structured logging | json |
| `setup_wizard.py` | ~N/A | Provider + key wizard | rich |
| `providers/models.py` | ~62 | Provider data types | dataclasses |
| `providers/builtin.py` | ~N/A | 47 provider definitions | models |
| `providers/registry.py` | ~70 | Provider lookup | builtin |
| `providers/adapters.py` | ~202 | HTTP adapter layer | httpx, models |

## Gotchas

### `sys.stdin.read()` blocks forever

Claude Code pipes JSON to hook stdin but may not close the pipe. Any blocking stdin read will hang. Always use the char-by-char approach in `hook_entry.py`.

### `_cwd_to_project_dir()` path conversion

Claude Code stores transcripts in `~/.claude/projects/<encoded-cwd>/`. The encoding replaces `:`, `\`, `/` with `-` and collapses consecutive dashes. If transcript discovery breaks, check this function in `transcript_reader.py`.

### Provider auto-detection from URL

`llm.py` auto-detects API style from the base URL:
- URL contains "anthropic" → `ApiStyle.ANTHROPIC`
- Otherwise → `ApiStyle.OPENAI`

This may be wrong for some proxies. The `custom` provider with explicit config is the escape hatch.

### `RefineConfig.get_api_key()` chain

```
provider_profile.api_key
  → provider_profile.auth_token
  → config.api_key (legacy)
  → config.auth_token (legacy)
```

First non-empty value wins. Then `resolve_for_config()` adds env var fallbacks.

### `_REFINE_SYSTEM_PROMPT` is a constant

The system prompt for refinement is hardcoded in `refiner.py`. It's deliberately short and focused. Changing it affects all refinement quality. Test thoroughly after any modification.

## Areas for Improvement

1. **Streaming support**: The `ProviderAdapter.call()` method does a single POST and waits for the full response. Streaming would improve perceived latency.

2. **Retry logic**: No retry on transient API failures. Adding exponential backoff would improve reliability.

3. **Provider health checks**: No way to test if a provider's API key is valid before using it. A `prf providers test` command would be useful.

4. **Hook mode TUI**: If the `CONIN$` blocking issue is resolved (e.g., by using a different IPC mechanism), the TUI could work in hook mode too.

5. **Multi-turn refinement**: Currently single-shot. Could allow the user to iteratively refine the prompt with follow-up instructions.

6. **Config validation**: No schema validation on load. Invalid config values may cause runtime errors.

## File Sizes (Approximate)

| File | Lines | Status |
|------|-------|--------|
| `app.py` | 465 | Could be split (CLI commands + flow logic) |
| `config.py` | 256 | OK |
| `providers/adapters.py` | 202 | OK |
| `transcript_reader.py` | 168 | OK |
| `refiner.py` | 156 | OK |
| `hook_integration.py` | 152 | OK |
| `summarizer.py` | 139 | OK |
| `hook_entry.py` | 99 | OK |
| `credentials.py` | 94 | OK |
| `providers/registry.py` | 70 | OK |
| `providers/models.py` | 62 | OK |
| `llm.py` | 104 | OK |

## Git History Context

Key commits:
- Backup commit before refine prompt fix: `be8f4a4`
- Stronger refine prompt + debug logging: `11974f1`

The project went through several iterations:
1. Initial: PreToolUse hook with TUI review
2. Switch to UserPromptSubmit hook
3. Remove TUI from hook mode (CONIN$ blocking)
4. Fix Chinese encoding (`-X utf8`)
5. Fix stdin reading (char-by-char)
6. Fix refine prompt template (LLM answering instead of rewriting)
7. Add conversational response rejection

## Testing Notes

- `test_setup_wizard.py` may fail in non-interactive environments
- All other test files should pass: `pytest` (170 tests)
- Tests use `monkeypatch` for env vars and `unittest.mock.AsyncMock` for LLM calls
- `asyncio_mode = "auto"` in pyproject.toml means all async functions are auto-detected as tests
