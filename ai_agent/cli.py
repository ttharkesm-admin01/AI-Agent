"""Command-line entry point: one-shot prompts or an interactive REPL."""

from __future__ import annotations

import argparse
import sys

from ai_agent import __version__
from ai_agent.config import VALID_EFFORTS, Config
from ai_agent.skills import discover_skills


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-agent",
        description="CLI tool-using AI agent powered by Claude, with drop-in SKILL.md skills.",
    )
    parser.add_argument("prompt", nargs="?", help="One-shot prompt (omit for interactive mode)")
    parser.add_argument("-p", "--prompt", dest="prompt_flag", help="One-shot prompt (alias)")
    parser.add_argument("--model", help="Override model (default: env AI_AGENT_MODEL or claude-opus-4-8)")
    parser.add_argument("--effort", choices=VALID_EFFORTS, help="Reasoning effort")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip y/N confirmations for bash/write/edit")
    parser.add_argument("--list-skills", action="store_true", help="List discovered skills and exit")
    parser.add_argument("--version", action="version", version=f"ai-agent {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = Config.from_env()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.model:
        config.model = args.model
    if args.effort:
        config.effort = args.effort
    if args.yes:
        config.require_confirmation = False

    if args.list_skills:
        skills = discover_skills(config.skills_dirs)
        if not skills:
            print("No skills found in:", ", ".join(str(d) for d in config.skills_dirs))
            return 0
        for name in sorted(skills):
            skill = skills[name]
            print(f"{name:20s} {skill.description}")
            print(f"{'':20s} ({skill.path})")
        return 0

    # Import here so --list-skills / --help work without the API dependency chain.
    from ai_agent.agent import Agent

    agent = Agent(config)
    prompt = args.prompt or args.prompt_flag

    if prompt:
        agent.run_turn(prompt)
        return 0

    print(f"ai-agent {__version__} — model {config.model}, effort {config.effort}")
    print("Type your request; 'exit' or Ctrl-D to quit.\n")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            return 0
        try:
            agent.run_turn(line)
        except KeyboardInterrupt:
            print("\n[interrupted]")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
