"""Tests for hook_terminal module."""

import pytest
from io import StringIO

from src.hook_terminal import (
    prompt_choice,
    terminal_unavailable_reason,
    tty_print,
    tty_readline,
    tui_refine_review,
)


class TestPromptChoice:
    def test_valid_choice(self):
        out = StringIO()
        inp = StringIO("a\n")
        result = prompt_choice(out, inp, "Choose: ", "aeos", "a")
        assert result == "a"

    def test_default_on_empty(self):
        out = StringIO()
        inp = StringIO("\n")
        result = prompt_choice(out, inp, "Choose: ", "aeos", "s")
        assert result == "s"

    def test_default_on_eof(self):
        out = StringIO()
        inp = StringIO("")
        result = prompt_choice(out, inp, "Choose: ", "aeos", "o")
        assert result == "o"

    def test_invalid_then_valid(self):
        out = StringIO()
        inp = StringIO("x\na\n")
        result = prompt_choice(out, inp, "Choose: ", "aeos", "a")
        assert result == "a"
        assert "Please enter one of" in out.getvalue()


class TestTtyPrint:
    def test_writes_line(self):
        out = StringIO()
        tty_print(out, "hello world")
        assert out.getvalue() == "hello world\n"


class TestTtyReadline:
    def test_reads_line(self):
        inp = StringIO("hello\n")
        result = tty_readline(inp)
        assert result == "hello"

    def test_eof_returns_empty(self):
        inp = StringIO("")
        result = tty_readline(inp)
        assert result == ""


class TestTuiRefineReview:
    def test_accept_choice(self):
        out = StringIO()
        inp = StringIO("a\n")
        choice, edited = tui_refine_review(out, inp, "fix bug", "Goal: Fix the login bug")
        assert choice == "accept"
        assert edited == ""
        output = out.getvalue()
        assert "Prompt Refiner" in output
        assert "[A]ccept" in output
        assert "[E]dit" in output
        assert "[O]riginal" in output
        assert "[S]kip" in output
        assert "fix bug" in output
        assert "Goal: Fix the login bug" in output

    def test_original_choice(self):
        out = StringIO()
        inp = StringIO("o\n")
        choice, edited = tui_refine_review(out, inp, "original", "refined version")
        assert choice == "original"
        assert edited == ""

    def test_skip_choice(self):
        out = StringIO()
        inp = StringIO("s\n")
        choice, edited = tui_refine_review(out, inp, "orig", "refined")
        assert choice == "skip"
        assert edited == ""

    def test_edit_choice(self):
        out = StringIO()
        inp = StringIO("e\nedited prompt\n\n")
        choice, edited = tui_refine_review(out, inp, "original", "refined")
        assert choice == "edit"
        assert edited == "edited prompt"

    def test_edit_empty_returns_refined(self):
        out = StringIO()
        inp = StringIO("e\n\n")
        choice, edited = tui_refine_review(out, inp, "original", "refined")
        assert choice == "edit"
        assert edited == "refined"

    def test_default_on_empty_input(self):
        out = StringIO()
        inp = StringIO("\n")
        choice, edited = tui_refine_review(out, inp, "orig", "refined")
        assert choice == "accept"  # default is 'a'

    def test_no_changes_label(self):
        out = StringIO()
        inp = StringIO("a\n")
        choice, _ = tui_refine_review(out, inp, "same text", "same text")
        assert choice == "accept"
        assert "No changes" in out.getvalue()

    def test_context_summary_displayed(self):
        out = StringIO()
        inp = StringIO("a\n")
        tui_refine_review(out, inp, "orig", "refined", context_summary="Task: Build API")
        assert "Task: Build API" in out.getvalue()

    def test_no_context_placeholder_skipped(self):
        out = StringIO()
        inp = StringIO("a\n")
        tui_refine_review(out, inp, "orig", "refined", context_summary="(no context)")
        assert "(no context)" not in out.getvalue()

    def test_degraded_warning(self):
        out = StringIO()
        inp = StringIO("a\n")
        tui_refine_review(out, inp, "orig", "refined", degraded=True)
        assert "WARNING" in out.getvalue()


class TestTerminalUnavailableReason:
    def test_returns_string(self):
        reason = terminal_unavailable_reason()
        assert len(reason) > 10
        # Should mention either CONIN$/CONOUT$ or /dev/tty
        assert "CONIN" in reason or "/dev/tty" in reason


class TestOpenTerminal:
    """Test open_terminal_in/open_terminal_out exist and are callable."""

    def test_imports_exist(self):
        from src.hook_terminal import open_terminal_in, open_terminal_out
        assert callable(open_terminal_in)
        assert callable(open_terminal_out)
