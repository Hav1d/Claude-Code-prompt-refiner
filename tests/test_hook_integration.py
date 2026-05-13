"""Tests for hook integration module."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from src.config import RefineConfig, ProviderProfile
from src.hook_integration import (
    build_hook_response,
    extract_prompt_from_hook,
    handle_hook,
    parse_hook_payload,
)


class TestParseHookPayload:
    def test_valid_json(self):
        assert parse_hook_payload('{"prompt": "test"}') == {"prompt": "test"}

    def test_empty_string(self):
        assert parse_hook_payload("") == {}

    def test_invalid_json(self):
        assert parse_hook_payload("not json") == {}


class TestExtractPromptFromHook:
    def test_prompt_field(self):
        assert extract_prompt_from_hook({"prompt": "fix bug", "session_id": "abc"}) == "fix bug"

    def test_missing_prompt(self):
        assert extract_prompt_from_hook({"session_id": "abc"}) == ""


class TestBuildHookResponse:
    def test_with_refined_prompt(self):
        result = build_hook_response("refined", "UserPromptSubmit")
        assert result == {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "refined",
            }
        }

    def test_empty_prompt(self):
        assert build_hook_response("", "UserPromptSubmit") == {}


class TestHandleHook:
    @pytest.mark.asyncio
    async def test_returns_none_for_empty_prompt(self):
        assert await handle_hook({"prompt": ""}) is None

    @pytest.mark.asyncio
    async def test_returns_none_for_skip_command(self):
        assert await handle_hook({"prompt": "/no-refine fix this"}) is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_credentials(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()
        assert await handle_hook({"prompt": "fix the login bug in the app"}, config) is None

    @pytest.mark.asyncio
    async def test_returns_additional_context_on_success(self, monkeypatch):
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("refined prompt", False))

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
            patch("src.refiner.apply_prefix_suffix", return_value="final prompt"),
        ):
            result = await handle_hook({"prompt": "fix the login bug in the app"}, config)

        assert result is not None
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "Original prompt:" in ctx
        assert "fix the login bug in the app" in ctx
        assert "Refined prompt:" in ctx
        assert "final prompt" in ctx

    @pytest.mark.asyncio
    async def test_returns_none_on_llm_failure(self, monkeypatch):
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", AsyncMock(side_effect=Exception("fail"))),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is None
