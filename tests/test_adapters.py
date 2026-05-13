"""Tests for provider adapters."""

import pytest
from src.providers.adapters import ProviderAdapter, create_adapter
from src.providers.models import ApiStyle, AuthScheme, ModelDefaults, ProviderConfig


def _make_provider(**kwargs) -> ProviderConfig:
    defaults = {
        "id": "test",
        "display_name": "Test",
        "category": "custom",
        "api_style": ApiStyle.OPENAI,
        "base_url": "https://api.test.com/v1",
        "auth_scheme": AuthScheme.BEARER,
    }
    defaults.update(kwargs)
    return ProviderConfig(**defaults)


class TestBuildHeaders:
    def test_bearer_auth(self):
        p = _make_provider(auth_scheme=AuthScheme.BEARER)
        adapter = ProviderAdapter(p, api_key="my-key")
        headers = adapter.build_headers()
        assert headers["Authorization"] == "Bearer my-key"

    def test_api_key_auth(self):
        p = _make_provider(auth_scheme=AuthScheme.API_KEY)
        adapter = ProviderAdapter(p, api_key="my-key")
        headers = adapter.build_headers()
        assert headers["x-api-key"] == "my-key"

    def test_custom_header_auth(self):
        p = _make_provider(
            auth_scheme=AuthScheme.CUSTOM_HEADER,
            auth_header_name="x-custom-token",
        )
        adapter = ProviderAdapter(p, api_key="my-key")
        headers = adapter.build_headers()
        assert headers["x-custom-token"] == "my-key"

    def test_no_key(self):
        p = _make_provider()
        adapter = ProviderAdapter(p, api_key="")
        headers = adapter.build_headers()
        assert "Authorization" not in headers


class TestBuildPayload:
    def test_openai_format(self):
        p = _make_provider(api_style=ApiStyle.OPENAI)
        adapter = ProviderAdapter(p, api_key="key")
        payload = adapter.build_payload("system", "user", 100, "model-x")
        assert payload["model"] == "model-x"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["max_tokens"] == 100

    def test_anthropic_format(self):
        p = _make_provider(api_style=ApiStyle.ANTHROPIC)
        adapter = ProviderAdapter(p, api_key="key")
        payload = adapter.build_payload("system", "user", 100, "model-x")
        assert payload["model"] == "model-x"
        assert payload["system"] == "system"
        assert payload["messages"][0]["role"] == "user"


class TestBuildUrl:
    def test_openai_url(self):
        p = _make_provider(api_style=ApiStyle.OPENAI, base_url="https://api.test.com/v1")
        adapter = ProviderAdapter(p, api_key="key")
        assert adapter.build_url("model") == "https://api.test.com/v1/chat/completions"

    def test_anthropic_url(self):
        p = _make_provider(api_style=ApiStyle.ANTHROPIC, base_url="https://api.anthropic.com")
        adapter = ProviderAdapter(p, api_key="key")
        assert adapter.build_url("model") == "https://api.anthropic.com/v1/messages"


class TestParseResponse:
    def test_openai_response(self):
        p = _make_provider(api_style=ApiStyle.OPENAI)
        adapter = ProviderAdapter(p, api_key="key")
        data = {"choices": [{"message": {"content": "hello"}}]}
        assert adapter.parse_response(data) == "hello"

    def test_anthropic_response(self):
        p = _make_provider(api_style=ApiStyle.ANTHROPIC)
        adapter = ProviderAdapter(p, api_key="key")
        data = {"content": [{"type": "text", "text": "hello"}]}
        assert adapter.parse_response(data) == "hello"

    def test_openai_empty(self):
        p = _make_provider(api_style=ApiStyle.OPENAI)
        adapter = ProviderAdapter(p, api_key="key")
        assert adapter.parse_response({"choices": []}) == ""


class TestCreateAdapter:
    def test_creates_adapter(self):
        p = _make_provider()
        adapter = create_adapter(p, api_key="key", base_url="https://custom.com")
        assert adapter.api_key == "key"
        assert adapter.base_url == "https://custom.com"

    def test_uses_provider_base_url(self):
        p = _make_provider(base_url="https://default.com")
        adapter = create_adapter(p, api_key="key")
        assert adapter.base_url == "https://default.com"
