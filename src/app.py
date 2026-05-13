"""CLI entry point for Prompt Refiner."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .cache import SummaryCache
from .config import RefineConfig, load_config, resolve_path
from .executor import submit_to_claude_code, write_to_file
from .logger import RefineLogger
from .llm import make_llm_caller, make_summary_caller
from .models import RefineResult, UserChoice
from .refiner import apply_prefix_suffix, refine_prompt, should_refine
from .summarizer import summarize_history
from .transcript_reader import format_transcript_for_context, read_transcript
from .ui import (
    confirm_submit,
    console,
    edit_prompt,
    show_error,
    show_info,
    show_refinement_result,
    show_skip_reason,
    show_success,
    show_welcome,
)

app = typer.Typer(
    name="prompt-refiner",
    help="Refine your prompts before sending to Claude Code.",
    add_completion=False,
)

config_app = typer.Typer(name="config", help="Manage configuration.", add_completion=False)
providers_app = typer.Typer(name="providers", help="Manage AI providers.", add_completion=False)
app.add_typer(config_app)
app.add_typer(providers_app)


# ─── Main Commands ──────────────────────────────────────────

@app.command()
def refine(
    prompt: Optional[str] = typer.Argument(None, help="Prompt to refine"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
    no_submit: bool = typer.Option(False, "--no-submit", "-n"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o"),
    skip_refine: bool = typer.Option(False, "--skip", "-s"),
    auto: bool = typer.Option(False, "--auto", "-a"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Refine a prompt interactively before submitting to Claude Code."""
    config = load_config(config_path)
    if debug:
        config.debug_mode = True

    _ensure_credentials(config, interactive=sys.stdin.isatty() and not auto)

    raw_input = prompt
    if raw_input is None:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read().strip()
        else:
            raw_input = typer.prompt("Enter your prompt")

    if not raw_input:
        show_error("No input provided.")
        raise typer.Exit(1)

    result = asyncio.run(
        _refine_flow(
            raw_input=raw_input,
            config=config,
            skip_refine=skip_refine,
            auto_accept=auto,
            no_submit=no_submit,
            dry_run=dry_run,
            output_file=output_file,
        )
    )
    raise typer.Exit(result)


@app.command("batch")
def batch_refine(
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Refine prompts in a continuous loop."""
    config = load_config(config_path)
    if debug:
        config.debug_mode = True

    _ensure_credentials(config, interactive=True)
    show_welcome()
    console.print("[info]Continuous mode — type 'quit' to stop.[/info]")

    while True:
        try:
            raw_input = typer.prompt("\nPrompt")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[info]Goodbye.[/info]")
            break

        if raw_input.strip().lower() in ("quit", "exit", "q"):
            break
        if not raw_input.strip():
            continue

        asyncio.run(
            _refine_flow(
                raw_input=raw_input, config=config, skip_refine=False,
                auto_accept=False, no_submit=False, dry_run=False, output_file=None,
            )
        )


@app.command("clear-cache")
def clear_cache_cmd(config_path: Optional[str] = typer.Option(None, "--config", "-c")):
    """Clear the summarization cache."""
    config = load_config(config_path)
    cache_dir = resolve_path(config.cache_dir, Path.home() / ".prompt-refiner")
    cache = SummaryCache(cache_dir, config.cache_ttl)
    count = cache.clear()
    show_success(f"Cleared {count} cached entries.")


@app.command("hook")
def hook_entry(
    event: str = typer.Argument(..., help="Hook event type"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Entry point for Claude Code hook integration."""
    config = load_config(config_path)
    if debug:
        config.debug_mode = True

    try:
        payload_raw = sys.stdin.read()
        payload = json.loads(payload_raw) if payload_raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        payload = {}

    raw_input = payload.get("prompt", "")
    if not raw_input:
        return
    if not should_refine(raw_input, config):
        return

    asyncio.run(
        _refine_flow(
            raw_input=raw_input, config=config, skip_refine=False,
            auto_accept=True, no_submit=True, dry_run=False,
            output_file=None, hook_mode=True, hook_event=event,
        )
    )


# ─── Config Commands ────────────────────────────────────────

@config_app.command("show")
def config_show(config_path: Optional[str] = typer.Option(None, "--config", "-c")):
    """Show the current configuration."""
    from .setup_wizard import show_config_status

    config = load_config(config_path)
    data = config.model_dump()
    # Mask sensitive fields
    for key in ("api_key", "auth_token"):
        if data.get(key):
            data[key] = _mask_value(data[key])
    # Mask provider keys
    for pid, pdata in data.get("providers", {}).items():
        if pdata.get("api_key"):
            pdata["api_key"] = _mask_value(pdata["api_key"])
        if pdata.get("auth_token"):
            pdata["auth_token"] = _mask_value(pdata["auth_token"])

    console.print_json(json.dumps(data, indent=2, ensure_ascii=False))
    console.print()
    show_config_status(config)


@config_app.command("set")
def config_set():
    """Set or update provider via interactive wizard."""
    from .setup_wizard import run_wizard
    result = run_wizard()
    raise typer.Exit(0 if result else 1)


@config_app.command("clear")
def config_clear():
    """Remove saved configuration."""
    from .setup_wizard import clear_saved_config
    if clear_saved_config():
        show_success("Configuration removed.")
    else:
        show_info("No saved configuration found.")


# ─── Providers Commands ─────────────────────────────────────

@providers_app.command("list")
def providers_list():
    """List all available providers."""
    from .providers import get_registry

    registry = get_registry()
    category_labels = {
        "official": "Official",
        "domestic": "国内",
        "international": "国际",
        "proxy": "代理",
        "custom": "自定义",
    }

    table = Table(title=f"Providers ({len(registry)} total)", show_lines=False)
    table.add_column("ID", style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("API Style")
    table.add_column("Default Model")
    table.add_column("Notes", max_width=30)

    for p in registry.list_all():
        model = p.default_models.refine or p.default_models.summary or "-"
        notes = p.notes[:28] + ".." if len(p.notes) > 30 else p.notes
        table.add_row(
            p.id, p.display_name,
            category_labels.get(p.category, p.category),
            p.api_style.value, model, notes,
        )

    console.print(table)


@providers_app.command("show")
def providers_show(provider_id: str = typer.Argument(..., help="Provider ID")):
    """Show details for a specific provider."""
    from .providers import get_registry

    registry = get_registry()
    provider = registry.get(provider_id)
    if provider is None:
        show_error(f"Provider '{provider_id}' not found.")
        raise typer.Exit(1)

    data = {
        "id": provider.id,
        "display_name": provider.display_name,
        "category": provider.category,
        "api_style": provider.api_style.value,
        "base_url": provider.base_url,
        "auth_scheme": provider.auth_scheme.value,
        "auth_env_names": provider.auth_env_names,
        "default_models": {
            "summary": provider.default_models.summary,
            "refine": provider.default_models.refine,
            "executor": provider.default_models.executor,
            "reasoning": provider.default_models.reasoning,
        },
        "supports_streaming": provider.supports_streaming,
        "supports_tools": provider.supports_tools,
        "supports_reasoning": provider.supports_reasoning,
        "notes": provider.notes,
        "website": provider.website,
    }
    console.print_json(json.dumps(data, indent=2, ensure_ascii=False))


@providers_app.command("search")
def providers_search(keyword: str = typer.Argument(..., help="Search keyword")):
    """Search providers by keyword."""
    from .providers import get_registry

    registry = get_registry()
    results = registry.search(keyword)
    if not results:
        console.print(f"[warning]No providers matching '{keyword}'[/warning]")
        return

    table = Table(title=f"Search: '{keyword}' ({len(results)} results)")
    table.add_column("ID", style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("Notes", max_width=40)

    for p in results:
        table.add_row(p.id, p.display_name, p.category, p.notes)

    console.print(table)


# ─── Helpers ────────────────────────────────────────────────

def _ensure_credentials(config: RefineConfig, interactive: bool = True) -> None:
    """Check for credentials and run wizard if needed."""
    from .setup_wizard import check_and_run_wizard
    check_and_run_wizard(config, interactive=interactive)


def _mask_value(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


async def _refine_flow(
    raw_input: str,
    config: RefineConfig,
    skip_refine: bool,
    auto_accept: bool,
    no_submit: bool,
    dry_run: bool,
    output_file: Optional[str],
    hook_mode: bool = False,
    hook_event: str = "UserPromptSubmit",
) -> int:
    """Core refinement flow. Returns exit code."""
    start_time = time.monotonic()
    log_dir = resolve_path(config.log_dir, Path.home() / ".prompt-refiner" / "logs")
    logger = RefineLogger(log_dir, config.log_format, config.debug_mode)
    logger.log_debug("refine_flow_start", {"input_length": len(raw_input)})

    cache_dir = resolve_path(config.cache_dir, Path.home() / ".prompt-refiner")
    cache = SummaryCache(cache_dir, config.cache_ttl)

    entries = read_transcript(max_entries=config.history_lines, explicit_path=config.transcript_path)
    transcript_text = format_transcript_for_context(entries) if entries else ""
    context_summary_text = ""

    if entries and transcript_text:
        cached = cache.get(transcript_text)
        if cached:
            context_summary_text = cached
        else:
            try:
                summary_caller = make_summary_caller(config)
                ctx = await summarize_history(entries, config, llm_caller=summary_caller)
                context_summary_text = ctx.to_text()
                if context_summary_text and context_summary_text != "(no context)":
                    cache.put(transcript_text, context_summary_text)
            except (ValueError, Exception):
                pass

    from .models import SessionContext
    context = SessionContext()
    if context_summary_text and context_summary_text != "(no context)":
        for line in context_summary_text.split("\n"):
            if line.startswith("Task:"):
                context.task = line[5:].strip()
            elif line.startswith("Tech stack:"):
                context.tech_stack = line[11:].strip()
            elif line.startswith("Tried:"):
                context.attempted = line[6:].strip()
            elif line.startswith("Blocker:"):
                context.current_blocker = line[8:].strip()
            elif line.startswith("Modified:"):
                context.modifications = line[9:].strip()
            elif line.startswith("Constraints:"):
                context.constraints = line[12:].strip()

    if skip_refine or not should_refine(raw_input, config):
        reason = "explicitly skipped" if skip_refine else "input pattern ignored"
        if not hook_mode:
            show_skip_reason(reason)
        final = apply_prefix_suffix(raw_input, config)
        duration = (time.monotonic() - start_time) * 1000
        logger.log_result(RefineResult(
            original_input=raw_input, context_summary=context_summary_text,
            refined_prompt=raw_input, final_prompt=final,
            user_choice=UserChoice.SKIP, duration_ms=duration,
        ))
        if output_file:
            write_to_file(final, output_file)
        if not no_submit and not hook_mode:
            submit_to_claude_code(final, dry_run=dry_run)
        elif hook_mode:
            _output_hook_result(final, hook_event)
        return 0

    try:
        llm_caller = make_llm_caller(config)
        refined, degraded = await refine_prompt(raw_input, context, config, llm_caller=llm_caller)
    except (ValueError, Exception):
        if not hook_mode:
            show_info("No API key available. Using original prompt.")
        final = apply_prefix_suffix(raw_input, config)
        if output_file:
            write_to_file(final, output_file)
        if not no_submit and not hook_mode:
            submit_to_claude_code(final, dry_run=dry_run)
        elif hook_mode:
            _output_hook_result(final, hook_event)
        return 0

    if auto_accept or (config.auto_refine and len(raw_input) >= config.auto_refine_min_length):
        choice = UserChoice.ACCEPT
        final = apply_prefix_suffix(refined, config)
        if not hook_mode:
            show_success("Auto-accepted refined prompt.")
    else:
        choice = show_refinement_result(
            original=raw_input, refined=refined,
            context_summary=context_summary_text, degraded=degraded,
        )
        if choice == UserChoice.ACCEPT:
            final = apply_prefix_suffix(refined, config)
        elif choice == UserChoice.EDIT:
            edited = edit_prompt(refined)
            final = apply_prefix_suffix(edited, config)
        elif choice == UserChoice.ORIGINAL:
            final = apply_prefix_suffix(raw_input, config)
        else:
            final = apply_prefix_suffix(raw_input, config)

    duration = (time.monotonic() - start_time) * 1000
    logger.log_result(RefineResult(
        original_input=raw_input, context_summary=context_summary_text,
        refined_prompt=refined, final_prompt=final,
        user_choice=choice, duration_ms=duration, degraded=degraded,
    ))

    if output_file:
        write_to_file(final, output_file)
    if hook_mode:
        _output_hook_result(final, hook_event)
    elif not no_submit:
        if confirm_submit(final):
            submit_to_claude_code(final, dry_run=dry_run)
        else:
            show_info("Submission cancelled.")
    return 0


def _output_hook_result(prompt: str, event_name: str = "UserPromptSubmit") -> None:
    """Output refined prompt in official Claude Code hook format."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": prompt,
        }
    }
    print(json.dumps(output, ensure_ascii=False))


def main():
    app()


if __name__ == "__main__":
    main()
