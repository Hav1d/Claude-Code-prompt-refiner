# Troubleshooting

Common problems and their solutions.

## Hook Issues

### Hook does nothing (no refinement appears)

**Symptoms**: Type a prompt in Claude Code, Claude processes it directly without showing a refined version.

**Causes**:
1. No API key configured
2. Input matches skip/ignore patterns
3. Hook command not found

**Fixes**:
```bash
# 1. Check credentials
prf config show

# 2. If no key, run setup wizard
prf config set

# 3. Test hook manually
echo '{"prompt": "fix the login bug"}' | python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json

# 4. Check .claude/settings.json exists and has correct hook command
cat .claude/settings.json
```

### Hook hangs / Claude Code shows "Composing... (35s)"

**Symptoms**: After typing a prompt, Claude Code shows "Composing..." for a long time, then either times out or produces unexpected behavior.

**Cause**: Old code used `sys.stdin.read()` which blocks forever if Claude Code doesn't close stdin pipe.

**Fix**: Ensure you're using `hook_entry.py` (not the old `app.py hook` command). The `hook_entry.py` module reads stdin char-by-char with `json.JSONDecoder.raw_decode()` to detect complete JSON without blocking.

### Chinese characters garbled

**Symptoms**: Refined prompt contains garbled characters like `娴ｇ姴銈介崨\udc80閿涘\udcello`.

**Cause**: Windows console encoding mismatch.

**Fix**: Add `-X utf8` to the hook command in `.claude/settings.json`:

```json
{
  "command": "python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json"
}
```

### LLM answers instead of rewriting

**Symptoms**: Refined prompt is something like "I'd be happy to help! Could you provide more details about..." instead of a rewritten version of the input.

**Cause**: Weak model that can't follow "rewrite" instructions, or the system prompt is not being followed.

**Fixes**:
1. Switch to a stronger provider: `prf config set`
2. The refiner has conversational response rejection — if it detects "i'd be happy", "当然", "请提供", etc., it falls back to the original input
3. Check logs for `degraded: true` entries

### Hook timeout

**Symptoms**: Claude Code shows a timeout error for the hook.

**Cause**: LLM call takes longer than the configured timeout (default 30s).

**Fix**: Increase timeout in `.claude/settings.json`:

```json
{
  "type": "command",
  "command": "...",
  "timeout": 60000
}
```

## CLI Issues

### `prf` command not found

**Cause**: Package not installed, or `~/.local/bin` not in PATH.

**Fix**:
```bash
# Install in development mode
cd prompt-refiner
pip install -e .

# Or use python -m
python -m src.app refine "fix the bug"
```

### `pr` command conflicts with GNU pr

**Cause**: The CLI entry point was renamed from `pr` to `prf` to avoid conflict with the GNU `pr` utility.

**Fix**: Use `prf` instead of `pr`.

### Wizard doesn't appear

**Cause**: Running in non-interactive mode (piped input, `--auto` flag, or stdin is not a TTY).

**Fix**: Run `prf config set` directly (not piped).

### No transcript found

**Symptoms**: Context summary is empty, refinement has no session context.

**Causes**:
1. Not running inside a Claude Code project
2. Transcript file doesn't exist yet (new session)
3. Project directory name doesn't match

**Fixes**:
```bash
# Check if transcript exists
ls ~/.claude/projects/

# Set explicit path in config
# prompt-config.json:
{
  "transcript_path": "/path/to/your/session.jsonl"
}

# Or set env var
export CLAUDE_TRANSCRIPT_PATH="/path/to/session.jsonl"
```

## Provider Issues

### API key not found

**Symptoms**: "No API key found" error or graceful degradation (no refinement).

**Fix**:
```bash
# Check what's configured
prf config show

# Set up a provider
prf config set

# Or set environment variable
export ANTHROPIC_API_KEY="sk-..."
```

### Wrong API style detected

**Symptoms**: 400 or 405 errors from the API.

**Cause**: The tool auto-detects API style from the base URL. If the URL contains "anthropic", it uses ANTHROPIC style; otherwise OPENAI style. This may be wrong for some proxies.

**Fix**: Use the `custom` provider with explicit configuration, or set the base URL to match the expected API style.

### Provider not found

**Symptoms**: "Provider 'xxx' not found" error.

**Fix**:
```bash
# List available providers
prf providers list

# Search for a provider
prf providers search deepseek
```

## Test Issues

### Tests hanging

**Cause**: A test opens a real terminal (CONIN$/CONOUT$) instead of mocking it.

**Fix**: Ensure all tests that call hook functions mock the terminal I/O:
```python
with patch("src.hook_integration._show_refinement_in_terminal"):
    result = await handle_hook({"prompt": "fix bug"}, config)
```

### Async test failures

**Cause**: Missing `pytest-asyncio` or wrong `asyncio_mode`.

**Fix**: Ensure `pyproject.toml` has:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

And install: `pip install pytest-asyncio`

## Debugging

### Enable debug mode

```bash
# CLI
prf refine --debug "fix the bug"

# Hook (add --debug to command)
python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json --debug

# Environment variable
export PROMPT_REFINE_DEBUG=1
```

Debug output goes to stderr.

### Check logs

Logs are written to `~/.prompt-refiner/logs/` in JSONL format:

```bash
# View recent logs
cat ~/.prompt-refiner/logs/*.jsonl | tail -5

# Pretty-print a log entry
cat ~/.prompt-refiner/logs/*.jsonl | tail -1 | python -m json.tool
```

Each log entry contains:
```json
{
  "timestamp": "2026-05-13T10:30:00Z",
  "original_input": "fix the bug",
  "context_summary": "Task: Build REST API...",
  "refined_prompt": "Goal: Fix the 422 error...",
  "final_prompt": "Goal: Fix the 422 error...",
  "user_choice": "accept",
  "duration_ms": 1500.0,
  "error": null,
  "degraded": false
}
```

### Manual hook test

```bash
# Test with a specific payload
echo '{"prompt": "fix the login bug", "session_id": "test"}' | python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json

# Expected: JSON with hookSpecificOutput, or nothing (if no key)
```
