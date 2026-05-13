"""Tests for config module — including migration from legacy format."""

import json
import pytest
from pathlib import Path

from src.config import RefineConfig, ProviderProfile, load_config, _deep_merge, _migrate_legacy_config


class TestRefineConfig:
    def test_defaults(self):
        config = RefineConfig()
        assert config.active_provider == ""
        assert config.auto_refine is False
        assert config.debug_mode is False
        assert config.history_lines == 15

    def test_prefix_suffix(self):
        config = RefineConfig(prefix="Be concise.", suffix="Use Python.")
        assert config.prefix == "Be concise."
        assert config.suffix == "Use Python."

    def test_skip_commands_default(self):
        config = RefineConfig()
        assert "/no-refine" in config.skip_commands
        assert "/skip" in config.skip_commands

    def test_get_active_profile_empty(self):
        config = RefineConfig()
        profile = config.get_active_profile()
        assert profile.api_key == ""

    def test_get_active_profile_with_provider(self):
        config = RefineConfig(
            active_provider="openrouter",
            providers={
                "openrouter": ProviderProfile(api_key="test-key", base_url="https://or.com")
            },
        )
        profile = config.get_active_profile()
        assert profile.api_key == "test-key"
        assert profile.base_url == "https://or.com"

    def test_get_model_from_profile(self):
        config = RefineConfig(
            active_provider="test",
            providers={
                "test": ProviderProfile(models={"refine": "gpt-4", "summary": "gpt-3.5"})
            },
        )
        assert config.get_model("refine") == "gpt-4"
        assert config.get_model("summary") == "gpt-3.5"

    def test_get_model_legacy_fallback(self):
        config = RefineConfig(refine_model="legacy-model")
        assert config.get_model("refine") == "legacy-model"

    def test_get_model_default(self):
        config = RefineConfig()
        assert config.get_model("refine") == "claude-haiku-4-5-20251001"

    def test_get_api_key_from_profile(self):
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="profile-key")},
        )
        assert config.get_api_key() == "profile-key"

    def test_get_api_key_legacy(self):
        config = RefineConfig(api_key="legacy-key")
        assert config.get_api_key() == "legacy-key"

    def test_get_base_url_from_profile(self):
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(base_url="https://custom.com")},
        )
        assert config.get_base_url() == "https://custom.com"


class TestDeepMerge:
    def test_basic_merge(self):
        assert _deep_merge({"a": 1, "b": 2}, {"b": 3, "c": 4}) == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        assert _deep_merge({"a": {"x": 1}}, {"a": {"y": 2}}) == {"a": {"x": 1, "y": 2}}

    def test_does_not_mutate(self):
        base = {"a": {"x": 1}}
        _deep_merge(base, {"a": {"y": 2}})
        assert base == {"a": {"x": 1}}


class TestMigrateLegacyConfig:
    def test_no_migration_needed(self):
        data = {"active_provider": "claude", "providers": {"claude": {}}}
        result = _migrate_legacy_config(data)
        assert result["active_provider"] == "claude"

    def test_migrates_api_key(self):
        data = {"api_key": "sk-ant-123", "refine_model": "claude-haiku"}
        result = _migrate_legacy_config(data)
        assert result["active_provider"] == "custom"
        assert result["providers"]["custom"]["api_key"] == "sk-ant-123"
        assert result["providers"]["custom"]["models"]["refine"] == "claude-haiku"
        assert "api_key" not in result  # Legacy field removed

    def test_migrates_auth_token(self):
        data = {"auth_token": "bearer-token", "api_base_url": "https://proxy.com"}
        result = _migrate_legacy_config(data)
        assert result["active_provider"] == "custom"
        assert result["providers"]["custom"]["auth_token"] == "bearer-token"
        assert result["providers"]["custom"]["base_url"] == "https://proxy.com"

    def test_no_migration_without_legacy_fields(self):
        data = {"auto_refine": True, "history_lines": 20}
        result = _migrate_legacy_config(data)
        assert "active_provider" not in result


class TestLoadConfig:
    def test_load_from_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.config._SEARCH_ORDER", [])
        config_data = {
            "active_provider": "test",
            "providers": {"test": {"api_key": "file-key"}},
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(str(config_file))
        assert config.active_provider == "test"
        assert config.get_api_key() == "file-key"

    def test_load_legacy_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.config._SEARCH_ORDER", [])
        config_data = {"api_key": "legacy-key", "refine_model": "custom-model"}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(str(config_file))
        assert config.active_provider == "custom"
        assert config.get_api_key() == "legacy-key"

    def test_defaults_when_no_file(self, monkeypatch):
        monkeypatch.setattr("src.config._SEARCH_ORDER", [])
        config = load_config("/nonexistent/path.json")
        assert config.active_provider == ""

    def test_env_override(self, monkeypatch):
        monkeypatch.setattr("src.config._SEARCH_ORDER", [])
        monkeypatch.setenv("PROMPT_REFINE_PROVIDER", "env-provider")
        config = load_config()
        assert config.active_provider == "env-provider"
