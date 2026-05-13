"""Tests for refiner module."""

import pytest

from src.config import RefineConfig
from src.models import SessionContext
from src.refiner import (
    apply_prefix_suffix,
    build_refine_prompt,
    should_refine,
)


class TestShouldRefine:
    def test_normal_input(self):
        config = RefineConfig()
        assert should_refine("fix the login bug", config) is True

    def test_skip_command(self):
        config = RefineConfig()
        assert should_refine("/no-refine fix this", config) is False
        assert should_refine("/nr fix this", config) is False
        assert should_refine("/skip", config) is False

    def test_empty_input(self):
        config = RefineConfig()
        assert should_refine("", config) is False
        assert should_refine("   ", config) is False

    def test_short_input(self):
        config = RefineConfig()
        assert should_refine("hi", config) is False
        assert should_refine("test", config) is False

    def test_slash_command_ignored(self):
        config = RefineConfig()
        assert should_refine("/help", config) is False
        assert should_refine("/clear", config) is False

    def test_custom_skip_commands(self):
        config = RefineConfig(skip_commands=["/pass"], ignore_patterns=["^\\s*$"])
        assert should_refine("/pass this", config) is False
        # /no-refine is no longer a skip command, but still matches ignore_pattern ^/[a-z]+ by default
        # With ignore_patterns overridden, it should pass through
        assert should_refine("/no-refine this", config) is True

    def test_custom_ignore_patterns(self):
        config = RefineConfig(ignore_patterns=[r"^test_"])
        assert should_refine("test_something", config) is False
        assert should_refine("fix the bug", config) is True


class TestBuildRefinePrompt:
    def test_basic(self):
        config = RefineConfig()
        context = SessionContext()
        system, user = build_refine_prompt("fix the bug", context, config)
        assert "prompt refiner" in system.lower()
        assert "fix the bug" in user

    def test_with_context(self):
        config = RefineConfig()
        context = SessionContext(task="Build REST API", current_blocker="422 error")
        system, user = build_refine_prompt("fix the endpoint", context, config)
        assert "Build REST API" in user
        assert "422 error" in user

    def test_with_rules(self):
        config = RefineConfig(
            user_rules=["Always use type hints"],
            project_rules=["This is a Python project"],
        )
        context = SessionContext()
        system, _ = build_refine_prompt("fix it", context, config)
        assert "Always use type hints" in system
        assert "This is a Python project" in system


class TestApplyPrefixSuffix:
    def test_no_prefix_suffix(self):
        config = RefineConfig()
        result = apply_prefix_suffix("fix the bug", config)
        assert result == "fix the bug"

    def test_with_prefix(self):
        config = RefineConfig(prefix="Be concise.")
        result = apply_prefix_suffix("fix the bug", config)
        assert result.startswith("Be concise.")
        assert "fix the bug" in result

    def test_with_suffix(self):
        config = RefineConfig(suffix="Use Python.")
        result = apply_prefix_suffix("fix the bug", config)
        assert result.endswith("Use Python.")

    def test_both(self):
        config = RefineConfig(prefix="Be concise.", suffix="Use Python.")
        result = apply_prefix_suffix("fix the bug", config)
        assert result.startswith("Be concise.")
        assert result.endswith("Use Python.")
