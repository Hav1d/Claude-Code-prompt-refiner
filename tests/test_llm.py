"""Tests for LLM caller module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.config import RefineConfig, ProviderProfile
from src.llm import call_llm, make_llm_caller, make_summary_caller


class TestCallLlm:
    @pytest.mark.asyncio
    async def test_raises_on_no_credentials(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        with pytest.raises(ValueError, match="No API key"):
            await call_llm("system", "user")

    @pytest.mark.asyncio
    async def test_uses_provider_adapter(self, monkeypatch):
        """When active_provider is set, uses the adapter layer."""
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key", base_url="https://api.test.com")},
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "refined"}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.providers.adapters.httpx.AsyncClient", return_value=mock_client):
            result = await call_llm("system", "user", model="test-model", config=config)

        assert result == "refined"


class TestMakeLlmCaller:
    @pytest.mark.asyncio
    async def test_uses_config_refine_model(self, monkeypatch):
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(
                api_key="test-key",
                base_url="https://api.test.com",
                models={"refine": "refine-model"},
            )},
        )
        caller = make_llm_caller(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.providers.adapters.httpx.AsyncClient", return_value=mock_client):
            await caller("sys", "usr", 100)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json", {})
        assert payload["model"] == "refine-model"
