#!/usr/bin/env python3
"""Create the four Research Orchestrator files without overwriting existing work."""

from __future__ import annotations

import argparse
from pathlib import Path
import string
import sys


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

# Agent names are work slots, assigned in this order: Main, A ... Z, AA ... ZZ.
AGENT_ORDER = [
    "Main",
    *string.ascii_uppercase,
    *(a + b for a in string.ascii_uppercase for b in string.ascii_uppercase),
]


def parse_agents(raw: str | None) -> list[str]:
    """Return canonical agent names from a count ("3") or a list ("Main,A,B")."""
    if not raw or not raw.strip():
        return ["Main"]
    raw = raw.strip()
    if raw.isdigit():
        count = int(raw)
        if not 1 <= count <= len(AGENT_ORDER):
            raise ValueError(f"agent count must be between 1 and {len(AGENT_ORDER)}")
        return AGENT_ORDER[:count]

    canonical = {name.lower(): name for name in AGENT_ORDER}
    names: list[str] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        name = canonical.get(item.lower())
        if name is None:
            raise ValueError(
                f"invalid agent name '{item}': use Main, a letter A-Z, or two letters AA-ZZ, "
                "never a host or model name such as Claude, Codex, or GPT"
            )
        if name in names:
            raise ValueError(f"duplicate agent name '{name}'")
        names.append(name)
    return names or ["Main"]


def agent_sections(names: list[str]) -> str:
    blocks = []
    for name in names:
        blocks.append(
            f"## Agent: {name}\n\n"
            "_No active items yet. Add only actionable unfinished hypotheses or experiments._\n\n"
            "_For each item use the standard hypothesis block including Sources, Hypothesis, Evidence, Improvement, Priority, Resource, Parallel, Other, and Next test._\n"
        )
    return "\n".join(blocks).rstrip() + "\n"


def handoff_agent_sections(names: list[str]) -> str:
    blocks = []
    for name in names:
        blocks.append(
            f"### Agent: {name}\n"
            "- Current host: unassigned\n"
            "- Current thread: none yet\n"
            "- Resumable state: read discoveries, then your own plan section\n"
            "- Blocker: none\n"
            "- Next action: choose the highest-priority item in your plan section\n"
        )
    return "\n".join(blocks).rstrip() + "\n"


def render(template_name: str, values: dict[str, str]) -> str:
    text = (TEMPLATES / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def write_if_missing(path: Path, content: str) -> str:
    if path.exists():
        print(f"[SKIP] {path}")
        return "skip"
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[CREATE] {path}")
    return "create"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Research Orchestrator files.")
    parser.add_argument("target", nargs="?", default=".", help="Project directory")
    parser.add_argument("-n", "--name", help="Project name (defaults to directory name)")
    parser.add_argument(
        "--agents",
        help="Agent count (e.g. 2 -> Main,A) or comma-separated names from Main, A-Z, AA-ZZ",
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"Error: target directory does not exist: {target}", file=sys.stderr)
        return 1

    try:
        agents = parse_agents(args.agents)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    name = args.name or target.name
    values = {
        "{{PROJECT_NAME}}": name,
        "{{AGENT_NAMES}}": ", ".join(agents),
        "{{AGENT_SECTIONS}}": agent_sections(agents),
        "{{HANDOFF_AGENT_SECTIONS}}": handoff_agent_sections(agents),
    }

    files = [
        ("AGENTS.md.template", "agents.md"),
        ("PLAN.md.template", "plan.md"),
        ("DISCOVERIES.md.template", "discoveries.md"),
        ("HANDOFF.md.template", "handoff.md"),
    ]

    created = 0
    for template, filename in files:
        result = write_if_missing(target / filename, render(template, values))
        created += result == "create"

    print(f"Done. Created {created} file(s). Existing files were preserved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
