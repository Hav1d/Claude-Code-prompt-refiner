# Workflow

Detailed description of the prompt refinement pipeline, from user input to final output.

## Pipeline Stages

### 1. Input Acquisition

**CLI mode** (`app.py:refine()`):
- Argument: `prf refine "fix the bug"` → uses argument
- Interactive: `prf refine` → `typer.prompt("Enter your prompt")`
- Piped: `echo "fix bug" | prf refine` → `sys.stdin.read()`

**Hook mode** (`hook_entry.py:main()`):
- Reads JSON from stdin via `_read_stdin_json()`
- Extracts `payload["prompt"]` field
- Char-by-char reading with `json.JSONDecoder.raw_decode()` to avoid EOF blocking

### 2. Skip Check (`refiner.py:should_refine()`)

Returns `False` (skip refinement) if:
- Input starts with a skip command: `/no-refine`, `/nr`, `/skip`
- Input matches an ignore pattern: `^\s*$` (empty) or `^/[a-z]+` (slash commands)
- Input is shorter than 5 characters

### 3. Heuristic Refinement (`refiner.py:_heuristic_refine()`)

Before calling the LLM, applies rule-based checks:
- **Greetings** (hello/hi/hey/你好/嗨/哈喽/您好) → return unchanged
- **Already structured** (starts with Goal/Context/Task/请/帮我/修改/修复/etc.) → return unchanged

If a rule matches, the LLM is skipped entirely (faster, cheaper).

### 4. Transcript Reading (`transcript_reader.py:read_transcript()`)

Reads the last N entries (default 15) from Claude Code's `.jsonl` transcript file.

**Discovery order**:
1. Explicit path from config (`transcript_path`)
2. `CLAUDE_TRANSCRIPT_PATH` env var
3. `~/.claude/projects/<project-dir>/` → most recent `.jsonl` file
4. `~/.claude/history.jsonl` (global fallback)

**Parsing**: Each line is a JSON object with `role` (human/assistant) and `content` (string or Anthropic content blocks).

### 5. Context Summarization (`summarizer.py:summarize_history()`)

Compresses transcript into `SessionContext` with 6 fields:
- **Task**: What the user is working on
- **Tech stack**: Languages, frameworks, tools in use
- **Tried**: Approaches already attempted
- **Blocker**: Current error or blocking issue
- **Modified**: Files or components changed
- **Constraints**: Explicit user constraints

**Two strategies**:
1. **LLM**: Sends transcript to configured model with `_SUMMARY_SYSTEM_PROMPT`
2. **Heuristic fallback**: Extracts last human message as task, finds error patterns, lists modified files

Results are cached in `~/.prompt-refiner/` with configurable TTL (default 300s).

### 6. Prompt Refinement (`refiner.py:refine_prompt()`)

Calls the configured LLM with:
- **System prompt** (`_REFINE_SYSTEM_PROMPT`): Rules for rewriting (not answering)
- **User prompt**: Context summary (if available) + raw input

**Post-LLM validation**:
- Reject empty or too-short results (<3 chars)
- Reject conversational responses (contains markers like "i'd be happy", "当然", "请提供")
- Reject if result is >3x longer than input (model hallucinated content)

On any rejection: returns original input with `degraded=True`.

### 7. Review (CLI) / Interactive TUI (Hook)

**CLI mode** (`ui.py:show_refinement_result()`):
- Shows unified diff between original and refined
- Presents 4 choices: Accept / Edit / Original / Skip
- Edit mode: inline text editing of the refined prompt
- Simple "Press Enter to submit" confirmation after choice

**Hook mode** (TUI-first, then fallback):

1. **Terminal TUI** (`hook_terminal.py:tui_refine_review()`):
   - Tries to open the real terminal (CONOUT$/CONIN$ or /dev/tty)
   - If available: shows full interactive review with diff and A/E/O/S menu
   - User choice is processed BEFORE anything reaches Claude Code
   - Accept/Edit: returns refined prompt as `additionalContext` with `USER APPROVED` marker
   - Original/Skip: passes through (empty stdout)

2. **Fallback** (`hook_integration.py:_make_fallback_context()`):
   - If terminal TUI is unavailable, logs reason to stderr
   - Returns `additionalContext` with both versions and A/E/O/S instructions
   - Strong language tells Claude to NOT answer until user confirms

### 8. Prefix/Suffix Application (`refiner.py:apply_prefix_suffix()`)

Wraps the final prompt with configured `prefix` and `suffix`:
```
<prefix>

<refined prompt>

<suffix>
```

### 9. Output

**CLI mode**:
- `submit_to_claude_code(prompt)`: Invokes `claude` CLI with the prompt
- `write_to_file(prompt, path)`: Writes to file if `--output` specified
- `--dry-run`: Shows what would happen without executing

**Hook mode**:
- Prints `{"hookSpecificOutput": {"hookEventName": "...", "additionalContext": "..."}}` to stdout
- Empty stdout if no refinement needed (pass through)

## Mode Comparison

| Stage | CLI Mode | Hook Mode |
|-------|----------|-----------|
| Input | Argument / interactive / pipe | stdin JSON from Claude Code |
| Skip check | Same | Same |
| Heuristic | Same | Same |
| Transcript | Same | Same |
| Summary | Same (LLM or heuristic) | Same (LLM or heuristic) |
| Refinement | Same (LLM + validation) | Same (LLM + validation) |
| Review | Rich TUI: A/E/O/S via Rich | Terminal TUI: A/E/O/S via CONIN$/CONOUT$ or fallback |
| Output | `claude` CLI / file / pipe | stdout JSON / empty |

## Degradation Paths

Every stage has a fallback:

| Stage | Failure | Fallback |
|-------|---------|----------|
| Config loading | File not found / invalid JSON | Built-in defaults |
| Credential resolution | No key anywhere | Skip LLM, use original input |
| Transcript reading | File not found / parse error | Empty list (no context) |
| Context summarization | LLM call fails | Heuristic extraction |
| Prompt refinement | LLM call fails / bad output | Original input with `degraded=True` |
| Hook output | Any exception | Empty stdout (pass through) |
