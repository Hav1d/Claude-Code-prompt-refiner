"""Tests for logger module."""

from src.logger import RefineLogger, format_diff
from src.models import RefineResult, UserChoice


class TestFormatDiff:
    def test_identical(self):
        assert format_diff("hello", "hello") == "  hello"

    def test_addition(self):
        diff = format_diff("hello", "hello world")
        assert "+ hello world" in diff

    def test_removal(self):
        diff = format_diff("hello world", "hello")
        assert "- hello world" in diff

    def test_empty(self):
        assert format_diff("", "") == ""


class TestRefineLogger:
    def test_log_result(self, tmp_path):
        logger = RefineLogger(tmp_path, debug=True)
        result = RefineResult(
            original_input="fix bug",
            context_summary="(no context)",
            refined_prompt="Fix the bug",
            final_prompt="Fix the bug",
            user_choice=UserChoice.ACCEPT,
            duration_ms=100.0,
        )
        logger.log_result(result)
        assert logger.get_log_path().exists()

        # Verify content
        import json
        lines = logger.get_log_path().read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["user_choice"] == "accept"
        assert data["original_input"] == "fix bug"

    def test_debug_logging(self, tmp_path):
        logger = RefineLogger(tmp_path, debug=True)
        logger.log_debug("test message", {"key": "value"})

        import json
        lines = logger.get_log_path().read_text().strip().split("\n")
        data = json.loads(lines[0])
        assert data["level"] == "debug"
        assert data["message"] == "test message"

    def test_debug_disabled(self, tmp_path):
        logger = RefineLogger(tmp_path, debug=False)
        logger.log_debug("should not appear")
        assert not logger.get_log_path().exists() or \
            logger.get_log_path().read_text().strip() == ""
