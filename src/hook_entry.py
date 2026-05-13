"""Hook entry point for Claude Code integration.

Invoked as: python -m src.hook_entry UserPromptSubmit [--config path]
Reads JSON from stdin, outputs hook response to stdout.
"""

from __future__ import annotations

import asyncio
import json
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

    try:
        payload = _read_stdin_json()
    except Exception:
        return

    if not payload.get("prompt"):
        return
    if event_name not in ("UserPromptSubmit", "UserPromptExpansion"):
        return

    try:
        result = asyncio.run(_run(payload, event_name, config_path))
    except Exception:
        return

    if result:
        print(json.dumps(result, ensure_ascii=False))


async def _run(payload: dict, event_name: str, config_path: str) -> dict | None:
    from .config import load_config
    from .hook_integration import handle_hook

    config = load_config(config_path if config_path else None)
    return await handle_hook(payload, config, event_name=event_name)


if __name__ == "__main__":
    main()
