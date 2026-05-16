# Testing

How to run tests, what they cover, and how to add new tests.

## Running Tests

```bash
# All tests
pytest

# Verbose output
pytest -v

# Specific file
pytest tests/test_refiner.py -v

# Specific test
pytest tests/test_refiner.py::TestShouldRefine::test_skip_command -v

# With coverage
pytest --cov=src --cov-report=term-missing

# Stop on first failure
pytest -x
```

## Test Structure

```
tests/
├── test_config.py           # Config loading, merging, legacy migration
├── test_credentials.py      # Credential resolution chain
├── test_refiner.py          # should_refine, heuristic, LLM refinement
├── test_llm.py              # LLM caller, adapter integration
├── test_summarizer.py       # Context summarization
├── test_transcript_reader.py # Transcript parsing
├── test_hook_integration.py # Hook logic: handle_hook, build_hook_response
├── test_hook_entry.py       # Hook entry: stdin reading, arg parsing
├── test_hook_e2e.py         # End-to-end hook flow
├── test_hook_terminal.py    # CONIN$/CONOUT$ terminal bypass
├── test_providers.py        # Provider registry, adapters
├── test_ui.py               # TUI components
├── test_cache.py            # Summary caching
├── test_logger.py           # Structured logging
├── test_app.py              # CLI commands
├── test_models.py           # Data models
└── test_setup_wizard.py     # Setup wizard (may need interactive env)
```

**170 tests collected** (some may require interactive terminal).

## Key Test Patterns

### Async Tests

All async tests use `pytest-asyncio` with `asyncio_mode = "auto"`:

```python
@pytest.mark.asyncio
async def test_refine_with_llm(self):
    mock_llm = AsyncMock(return_value="refined prompt")
    result, degraded = await refine_prompt("fix bug", SessionContext(), config, llm_caller=mock_llm)
    assert result == "refined prompt"
    assert degraded is False
```

### Mocking the LLM

Most tests mock the LLM caller to avoid real API calls:

```python
from unittest.mock import AsyncMock, patch

mock_refine = AsyncMock(return_value=("Goal: Fix login bug", False))

with patch("src.refiner.refine_prompt", mock_refine):
    result = await handle_hook({"prompt": "fix bug"}, config)
```

### Mocking Credentials

```python
# Clear all credential sources
monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)

# Or set a test key
config = RefineConfig(
    active_provider="test",
    providers={"test": ProviderProfile(api_key="test-key")},
)
```

### Testing Hook Output Format

```python
def test_hook_output_format():
    result = build_hook_response("refined prompt", "UserPromptSubmit")
    assert result == {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "refined prompt",
        }
    }
```

### Testing Graceful Degradation

```python
@pytest.mark.asyncio
async def test_no_credentials_returns_none(self, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
    config = RefineConfig()
    result = await handle_hook({"prompt": "fix the login bug"}, config)
    assert result is None  # Pass through, not crash
```

## Test Coverage

Run coverage report:

```bash
pytest --cov=src --cov-report=term-missing
```

Target: 80% minimum. Key areas with high coverage:
- `refiner.py`: should_refine, heuristic, LLM validation
- `hook_integration.py`: handle_hook, build_hook_response
- `config.py`: loading, merging, legacy migration
- `credentials.py`: resolution chain

## Adding New Tests

1. Follow the existing file naming: `tests/test_<module>.py`
2. Use `pytest.mark.asyncio` for async tests
3. Mock external calls (LLM, file system) — don't make real API calls
4. Test both success and failure paths
5. Test graceful degradation (no crash on missing config/key)

## Pytest Configuration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

`asyncio_mode = "auto"` means all async test functions are automatically treated as async tests without needing `@pytest.mark.asyncio` (though it's still used for clarity).
