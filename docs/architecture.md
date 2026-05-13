# Architecture

## Design Decisions

### 1. Python + Rich + Typer

Chosen for:
- Fast local execution without a runtime server
- Rich TUI for terminal-native review experience
- Typer for clean CLI with auto-generated help
- Pydantic for validated config with type safety

### 2. Async LLM calls via httpx

- Direct Anthropic API calls (no SDK dependency)
- Async for future extensibility (batch, concurrent)
- Graceful degradation: if LLM fails, fall back to heuristic extraction

### 3. File-backed caching

- SHA256 hash of transcript text as cache key
- In-memory + disk dual-layer for speed
- TTL-based expiry (default 5 minutes)
- Avoids re-summarizing the same session state

### 4. Hook integration model

Claude Code hooks receive a JSON payload and can:
- `continue` — pass through unchanged
- `modify` — replace the prompt with the refined version

The hook entry point is designed to be non-blocking. If refinement fails, it degrades to `continue`.

### 5. Separation of concerns

```
transcript_reader → summarizer → refiner → UI → executor
       ↑                ↑           ↑
       └── cache ───────┘           │
                                    └── logger
```

Each module is independently testable and replaceable.

## Token Optimization Strategy

1. **History compression**: Only 10-20 recent entries, summarized by a cheap model
2. **Summary caching**: Same session state → same summary (no re-computation)
3. **Minimal context injection**: Summary is kept under 300 tokens
4. **Cheap model for refinement**: Haiku-class model for the refinement pass
5. **Skip rules**: Short inputs, slash commands, and explicit `/no-refine` bypass the LLM entirely

## Future Extensions

- **Plugin system**: Load custom refinement rules from Python modules
- **MCP integration**: Query external tools (issue tracker, docs) for context
- **Skill integration**: Auto-attach relevant Claude Code skills
- **VSCode extension**: Visual diff view for refined prompts
- **Learning mode**: Track which refinements users accept/reject to improve defaults
