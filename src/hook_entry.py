"""Hook entry point for Claude Code integration.

Invoked as: python -m src.hook_entry UserPromptSubmit [--config path]
Reads JSON from stdin, outputs hook response to stdout.

When running as a Claude Code plugin, configuration comes from userConfig
environment variables (CLAUDE_PLUGIN_OPTION_*). These are merged with any
--config file provided.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys


def _parse_args(argv: list[str]) -> tuple[str, str]:
    event_name = "UserPromptSubmit"
    config_path = ""
    args = argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config_path = args[i + 1]
            i += 2
        elif not args[i].startswith("--"):
            event_name = args[i]
            i += 1
        else:
            i += 1
    return event_name, config_path


def _plugin_env_config() -> dict:
    """Build config dict from CLAUDE_PLUGIN_OPTION_* environment variables.

    These are set by Claude Code from userConfig values in plugin.json.
    """
    provider = os.environ.get("CLAUDE_PLUGIN_OPTION_PROVIDER", "").strip()
    api_key = os.environ.get("CLAUDE_PLUGIN_OPTION_API_KEY", "").strip()
    base_url = os.environ.get("CLAUDE_PLUGIN_OPTION_BASE_URL", "").strip()

    if not api_key:
        return {}

    cfg: dict = {}
    if provider:
        cfg["active_provider"] = provider
        cfg["providers"] = {
            provider: {
                "api_key": api_key,
            }
        }
        if base_url:
            cfg["providers"][provider]["base_url"] = base_url
    else:
        cfg["api_key"] = api_key
        if base_url:
            cfg["api_base_url"] = base_url

    return cfg


def _read_stdin_json() -> dict:
    """Read JSON from stdin without blocking for EOF.

    Claude Code pipes JSON to the hook but may not close stdin (no EOF).
    sys.stdin.read() blocks forever in that case. Instead, read char by
    char and use json.JSONDecoder.raw_decode to detect when the JSON
    object is complete.
    """
    buf = ""
    decoder = json.JSONDecoder()
    while True:
        ch = sys.stdin.read(1)
        if not ch:
            break
        buf += ch
        stripped = buf.lstrip()
        if not stripped:
            continue
        if stripped[0] == "{":
            try:
                obj, _ = decoder.raw_decode(stripped)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
        else:
            if len(buf) > 200:
                return {}
    if buf.strip():
        try:
            return json.loads(buf.strip())
        except json.JSONDecodeError:
            pass
    return {}


def main() -> None:
    event_name, config_path = _parse_args(sys.argv)
    # Write to log file for debugging — stderr may be suppressed by Claude Code
    import datetime as _dt, os as _os
    log_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "hook-debug.log")
    def _log(msg):
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"{_dt.datetime.now().isoformat()} {msg}\n")

    _log(f"HOOK STARTED event={event_name} config={config_path!r}")

    try:
        payload = _read_stdin_json()
    except Exception as exc:
        _log(f"stdin read failed: {exc}")
        return

    _log(f"payload keys={list(payload.keys()) if payload else 'EMPTY'}, prompt={payload.get('prompt', 'N/A')!r}")

    if not payload.get("prompt"):
        _log("no prompt in payload, exiting")
        return
    if event_name not in ("UserPromptSubmit", "UserPromptExpansion"):
        _log(f"unknown event: {event_name}")
        return

    try:
        result = asyncio.run(_run(payload, event_name, config_path))
    except Exception as exc:
        _log(f"run failed: {exc}")
        return

    if result:
        _log(f"OUTPUT: {json.dumps(result, ensure_ascii=False)[:500]}")
        print(json.dumps(result, ensure_ascii=False))
    else:
        _log("result is None, pass through (no stdout output)")


async def _run(payload: dict, event_name: str, config_path: str) -> dict | None:
    from .config import load_config
    from .hook_integration import handle_hook

    # Merge: plugin env config (from userConfig) overrides file config
    file_config_path = config_path if config_path else None
    config = load_config(file_config_path)

    env_cfg = _plugin_env_config()
    if env_cfg:
        # Apply plugin env overrides to the loaded config
        config_data = config.model_dump()
        _deep_merge(config_data, env_cfg)
        from .config import RefineConfig
        config = RefineConfig(**config_data)

    return await handle_hook(payload, config, event_name=event_name)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (mutates base)."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


if __name__ == "__main__":
    main()
