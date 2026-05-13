"""Tests for credentials module."""

import json
import pytest
from pathlib import Path

from src.credentials import (
    build_auth_headers,
    has_credentials,
    resolve_credentials,
    _read_claude_config_key,
)


class TestResolveCredentials:
    def test_config_api_key_first(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        key, auth_type = resolve_credentials(config_api_key="config-key")
        assert key == "config-key"
        assert auth_type == "api_key"

    def test_config_auth_token(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        key, auth_type = resolve_credentials(config_auth_token="my-token")
        assert key == "my-token"
        assert auth_type == "bearer"

    def test_env_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        key, auth_type = resolve_credentials()
        assert key == "env-key"
        assert auth_type == "api_key"

    def test_env_auth_token(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "env-token")
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        key, auth_type = resolve_credentials()
        assert key == "env-token"
        assert auth_type == "bearer"

    def test_no_credentials(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        key, auth_type = resolve_credentials()
        assert key is None
        assert auth_type is None


class TestBuildAuthHeaders:
    def test_api_key_header(self):
        assert build_auth_headers("sk-123", "api_key") == {"x-api-key": "sk-123"}

    def test_bearer_header(self):
        assert build_auth_headers("token", "bearer") == {"Authorization": "Bearer token"}


class TestHasCredentials:
    def test_true_when_key_exists(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        assert has_credentials() is True

    def test_false_when_no_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        assert has_credentials() is False


class TestReadClaudeConfigKey:
    def test_reads_from_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"primaryApiKey": "claude-key"}))
        monkeypatch.setattr("src.credentials._CLAUDE_CONFIG_PATH", config_file)
        assert _read_claude_config_key() == "claude-key"

    def test_returns_none_when_no_file(self, monkeypatch):
        monkeypatch.setattr("src.credentials._CLAUDE_CONFIG_PATH", Path("/nonexistent"))
        assert _read_claude_config_key() is None
