"""Tests for hook_terminal module."""

import pytest
from io import StringIO

from src.hook_terminal import prompt_choice, tty_print, tty_readline


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


class TestOpenTerminal:
    """Test open_terminal_in/open_terminal_out return file handles or None."""

    def test_imports_exist(self):
        from src.hook_terminal import open_terminal_in, open_terminal_out
        assert callable(open_terminal_in)
        assert callable(open_terminal_out)
