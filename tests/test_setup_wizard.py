"""Tests for setup wizard module."""

import json
import pytest
from pathlib import Path

from src.config import RefineConfig, ProviderProfile
from src.setup_wizard import (
    _mask_key,
    _save_provider_config,
    clear_saved_config,
    check_and_run_wizard,
)
from src.providers.models import ApiStyle, AuthScheme, ModelDefaults, ProviderConfig


def _make_provider(**kwargs) -> ProviderConfig:
    defaults = {
        "id": "test",
        "display_name": "Test",
        "category": "custom",
        "api_style": ApiStyle.OPENAI,
        "base_url": "https://api.test.com",
        "auth_scheme": AuthScheme.BEARER,
    }
    defaults.update(kwargs)
    return ProviderConfig(**defaults)


class TestMaskKey:
    def test_short_key(self):
        assert _mask_key("abc") == "****"

    def test_normal_key(self):
        result = _mask_key("sk-ant-1234567890")
        assert result.endswith("7890")


class TestSaveProviderConfig:
    def test_creates_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.setup_wizard._USER_CONFIG_DIR", tmp_path)
        monkeypatch.setattr("src.setup_wizard._USER_CONFIG_PATH", tmp_path / "config.json")

        provider = _make_provider(id="openrouter")
        _save_provider_config(provider, "my-key", "https://or.com", "model-x")

        data = json.loads((tmp_path / "config.json").read_text())
        assert data["active_provider"] == "openrouter"
        assert data["providers"]["openrouter"]["api_key"] == "my-key"
        assert data["providers"]["openrouter"]["base_url"] == "https://or.com"
        assert data["providers"]["openrouter"]["models"]["refine"] == "model-x"

    def test_preserves_existing_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.setup_wizard._USER_CONFIG_DIR", tmp_path)
        monkeypatch.setattr("src.setup_wizard._USER_CONFIG_PATH", tmp_path / "config.json")

        existing = {"auto_refine": True, "providers": {"other": {"api_key": "x"}}}
        (tmp_path / "config.json").write_text(json.dumps(existing))

        provider = _make_provider(id="test")
        _save_provider_config(provider, "key", "url", "model")

        data = json.loads((tmp_path / "config.json").read_text())
        assert data["auto_refine"] is True
        assert data["active_provider"] == "test"
        assert "other" in data["providers"]


class TestClearSavedConfig:
    def test_removes_provider_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.setup_wizard._USER_CONFIG_PATH", tmp_path / "config.json")
        config = {"active_provider": "test", "providers": {"test": {"api_key": "key"}}}
        (tmp_path / "config.json").write_text(json.dumps(config))

        assert clear_saved_config() is True
        data = json.loads((tmp_path / "config.json").read_text())
        assert "active_provider" not in data
        assert "providers" not in data

    def test_returns_false_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.setup_wizard._USER_CONFIG_PATH", tmp_path / "config.json")
        assert clear_saved_config() is False


class TestCheckAndRunWizard:
    def test_returns_true_when_provider_has_key(self):
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="key")},
        )
        assert check_and_run_wizard(config, interactive=False) is True

    def test_returns_true_with_env_var(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        config = RefineConfig()
        assert check_and_run_wizard(config, interactive=False) is True

    def test_returns_false_when_no_key_and_not_interactive(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        config = RefineConfig()
        assert check_and_run_wizard(config, interactive=False) is False
