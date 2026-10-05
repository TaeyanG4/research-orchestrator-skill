#!/usr/bin/env python3
"""Validate Research Orchestrator release consistency with only the Python stdlib."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "research-orchestrator-skill"


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    json_files = [
        ROOT / "plugin.json",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / ".claude-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "marketplace.json",
    ]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid JSON: {path}: {exc}", errors)

    text_suffixes = {".md", ".json", ".yaml", ".yml", ".py", ".template"}
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in text_suffixes:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "context-continuity" in text:
                fail(f"legacy name remains: {path}", errors)

    plan_fields = [
        "Sources:", "Hypothesis:", "Evidence:", "Improvement:",
        "Impact:", "Information:", "Confidence:", "Unblock:",
        "Diversity:", "Cost:", "Priority:", "Resource:",
        "Parallel:", "Other:", "Next test:",
    ]
    for path in [SKILL / "SKILL.md", SKILL / "templates" / "PLAN.md.template"]:
        text = path.read_text(encoding="utf-8")
        missing = [field for field in plan_fields if field not in text]
        if missing:
            fail(f"PLAN fields missing in {path}: {missing}", errors)

    verdict_files = [
        SKILL / "SKILL.md",
        SKILL / "templates" / "AGENTS.md.template",
        SKILL / "templates" / "DISCOVERIES.md.template",
        SKILL / "templates" / "HANDOFF.md.template",
    ]
    for path in verdict_files:
        text = path.read_text(encoding="utf-8")
        for verdict in ("CLOSED", "HOLD", "CHALLENGED"):
            if verdict not in text:
                fail(f"{verdict} missing in {path}", errors)

    handoff_fields = [
        "Action:", "Result:", "Evidence:", "Discovery updates:",
        "Review verdict:", "Files/metrics:", "Resource:",
        "Other executor:", "New plan items:", "Next resumable action:",
    ]
    for path in [SKILL / "SKILL.md", SKILL / "templates" / "HANDOFF.md.template"]:
        text = path.read_text(encoding="utf-8")
        missing = [field for field in handoff_fields if field not in text]
        if missing:
            fail(f"HANDOFF fields missing in {path}: {missing}", errors)

    openai_yaml = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for required in (
        "short_description: Orchestrate agent research",
        "- CHAT",
        "- CODEX",
        'brand_color: "#1687D9"',
    ):
        if required not in openai_yaml:
            fail(f"openai.yaml missing expected metadata: {required}", errors)

    initializer = SKILL / "scripts" / "init_research_orchestrator.py"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        first = subprocess.run(
            [sys.executable, str(initializer), str(target), "-n", "Validation Project", "--agents", "A,B"],
            text=True,
            capture_output=True,
        )
        if first.returncode != 0:
            fail(f"initializer failed: {first.stderr}", errors)
        plan = target / "plan.md"
        if plan.exists():
            with plan.open("a", encoding="utf-8") as handle:
                handle.write("\nKEEP-ME\n")
        second = subprocess.run(
            [sys.executable, str(initializer), str(target), "-n", "Validation Project", "--agents", "A,B"],
            text=True,
            capture_output=True,
        )
        if second.returncode != 0:
            fail(f"initializer second run failed: {second.stderr}", errors)
        if not plan.exists() or "KEEP-ME" not in plan.read_text(encoding="utf-8"):
            fail("initializer overwrote existing plan.md", errors)

    if errors:
        print("VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VALIDATION: PASS")
    print("- JSON manifests parse")
    print("- no legacy context-continuity name remains")
    print("- PLAN fields are consistent")
    print("- discovery verdicts are consistent")
    print("- HANDOFF fields are consistent")
    print("- OpenAI metadata is aligned")
    print("- initializer preserves existing files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
