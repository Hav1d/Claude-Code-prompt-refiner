#!/usr/bin/env python
"""Demo: refine a prompt without submitting to Claude Code.

Run: python examples/refine-demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.llm import make_llm_caller
from src.models import SessionContext
from src.refiner import apply_prefix_suffix, refine_prompt


async def demo():
    config = load_config()
    context = SessionContext(
        task="Building a REST API with FastAPI",
        tech_stack="Python 3.11, FastAPI, SQLAlchemy",
        current_blocker="Getting 422 Unprocessable Entity on POST /users",
    )

    raw_input = "fix the user creation endpoint it's broken"

    print(f"Original: {raw_input}")
    print()

    llm_caller = make_llm_caller(config)
    refined, degraded = await refine_prompt(raw_input, context, config, llm_caller=llm_caller)

    print(f"Refined: {refined}")
    print(f"Degraded: {degraded}")

    final = apply_prefix_suffix(refined, config)
    print(f"\nFinal (with prefix/suffix): {final}")


if __name__ == "__main__":
    asyncio.run(demo())
