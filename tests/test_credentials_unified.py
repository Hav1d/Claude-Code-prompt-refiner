"""Tests for unified credential resolution via resolve_for_config."""

import pytest

from src.config import RefineConfig, ProviderProfile
from src.credentials import resolve_for_config


class TestResolveForConfig:
    def test_returns_profile_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="profile-key", base_url="https://api.test.com")},
        )
        key, url = resolve_for_config(config)
        assert key == "profile-key"
        assert url == "https://api.test.com"

    def test_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()
        key, url = resolve_for_config(config)
        assert key == "env-key"

    def test_returns_empty_when_no_credentials(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()
        key, url = resolve_for_config(config)
        assert key == ""
        assert url == ""

    def test_env_base_url_fallback(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.com")
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()
        key, url = resolve_for_config(config)
        assert url == "https://proxy.com"
