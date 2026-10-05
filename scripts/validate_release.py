#!/usr/bin/env python3
"""Validate Research Orchestrator release consistency with only the Python stdlib."""

from __future__ import annotations

import json
from pathlib import Path
import re
import string
import subprocess
import sys
import tempfile
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "research-orchestrator-skill"
TEMPLATES = SKILL / "templates"

# Built from parts so this file does not match its own scan.
LEGACY_NAME = "context-" + "continuity"

AGENT_NAMES = {
    "Main",
    *string.ascii_uppercase,
    *(a + b for a in string.ascii_uppercase for b in string.ascii_uppercase),
}
VERDICTS = {"CLOSED", "HOLD", "CHALLENGED"}
CROSS_CHECK_STATES = {"PENDING", "REVIEWING", "VERIFIED", "HOLD", "CHALLENGED"}
PLAN_RESOURCES = {"CPU", "GPU", "EITHER"}
HANDOFF_RESOURCES = {"CPU", "GPU", "Other", "none"}

PLAN_FIELDS = [
    "Sources", "Hypothesis", "Evidence", "Improvement",
    "Impact", "Information", "Confidence", "Unblock",
    "Diversity", "Cost", "Priority", "Resource",
    "Parallel", "Other", "Next test",
]
DISCOVERY_FIELDS = ["Source", "Host", "Cross-check", "Finding", "Evidence", "Implication", "Reviews"]
HANDOFF_FIELDS = [
    "Host", "Action", "Result", "Evidence", "Discovery updates",
    "Review verdict", "Files/metrics", "Resource",
    "Other executor", "New plan items", "Next resumable action",
]

DOCS = [
    ROOT / "README.md",
    SKILL / "SKILL.md",
    TEMPLATES / "AGENTS.md.template",
    TEMPLATES / "PLAN.md.template",
    TEMPLATES / "DISCOVERIES.md.template",
    TEMPLATES / "HANDOFF.md.template",
]

FIELD_LINE = re.compile(r"^- ([A-Za-z/ -]+):(.*)$")
REVIEW_LINE = re.compile(r"^\s+- (.+?) \((\S+)\): (\S+) — (.*)$")
PLAN_HEAD = re.compile(r"^### (H-\S+) — ")
DISCOVERY_HEAD = re.compile(r"^## (D-\S+) — ")
HANDOFF_HEAD = re.compile(r"^### (?:YYYY-MM-DD HH:MM|\d{4}-\d{2}-\d{2} \d{2}:\d{2}) — (\S+) — ")
SECTION_HEAD = re.compile(r"^#{2,3} Agent: (\S+)")
ID_NEW = re.compile(r"\b([HD])-([A-Za-z]+)-(\d+)\b")
ID_OLD = re.compile(r"\b[HD]-[A-Za-z]?\d+\b")
AGENT_PROSE = re.compile(r"\bAgent (?:Main|[A-Z]{1,2})\b")


def blocks(lines: list[str], head: re.Pattern[str]):
    """Yield (heading match, field lines) for each block starting with `head`."""
    for i, line in enumerate(lines):
        match = head.match(line)
        if not match:
            continue
        fields = []
        for follow in lines[i + 1:]:
            if follow.startswith("- ") or follow.startswith("  - "):
                fields.append(follow)
            else:
                break
        yield match, fields


def field_names(fields: list[str]) -> list[str]:
    return [m.group(1) for line in fields if (m := FIELD_LINE.match(line))]


def field_value(fields: list[str], name: str) -> str | None:
    for line in fields:
        match = FIELD_LINE.match(line)
        if match and match.group(1) == name:
            return match.group(2).strip()
    return None


def check_resource(value: str | None, allowed: set[str], where: str, errors: list[str]) -> None:
    if value is None:
        return
    tokens = {token.strip() for token in value.split("|")}
    if not tokens <= allowed:
        errors.append(f"{where}: Resource '{value}' uses values outside {sorted(allowed)}")


def check_doc(path: Path, errors: list[str]) -> None:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for match, fields in blocks(lines, PLAN_HEAD):
        where = f"{rel}: {match.group(1)}"
        if field_names(fields) != PLAN_FIELDS:
            errors.append(f"{where}: PLAN fields {field_names(fields)} != {PLAN_FIELDS}")
        check_resource(field_value(fields, "Resource"), PLAN_RESOURCES, where, errors)

    for match, fields in blocks(lines, DISCOVERY_HEAD):
        where = f"{rel}: {match.group(1)}"
        if field_names(fields) != DISCOVERY_FIELDS:
            errors.append(f"{where}: DISCOVERIES fields {field_names(fields)} != {DISCOVERY_FIELDS}")
        source = field_value(fields, "Source")
        if source not in AGENT_NAMES:
            errors.append(f"{where}: Source '{source}' is not a standard agent name")
        host = field_value(fields, "Host")
        if not host or host in AGENT_NAMES:
            errors.append(f"{where}: Host '{host}' must name the host, not an agent slot")
        state = (field_value(fields, "Cross-check") or "").split(" ", 1)[0]
        if state not in CROSS_CHECK_STATES:
            errors.append(f"{where}: Cross-check '{state}' not in {sorted(CROSS_CHECK_STATES)}")
        verdicts: list[str] = []
        for line in fields[fields.index("- Reviews:") + 1:] if "- Reviews:" in fields else []:
            review = REVIEW_LINE.match(line)
            if not review:
                errors.append(f"{where}: review line must be '<Host> (<Agent>): <VERDICT> — reason': {line.strip()}")
                continue
            reviewer_host, agent, verdict, reason = review.groups()
            verdicts.append(verdict)
            if agent not in AGENT_NAMES:
                errors.append(f"{where}: reviewer agent '{agent}' is not a standard agent name")
            if verdict not in VERDICTS:
                errors.append(f"{where}: verdict '{verdict}' not in {sorted(VERDICTS)}")
            if reviewer_host == host and not reason.startswith("same host —"):
                errors.append(f"{where}: {reviewer_host} reviewed its own host's discovery")
        # A settled state must be backed by a review carrying the matching verdict.
        needs = {"VERIFIED": "CLOSED", "HOLD": "HOLD", "CHALLENGED": "CHALLENGED"}
        if state in needs and needs[state] not in verdicts:
            errors.append(f"{where}: Cross-check '{state}' has no '{needs[state]}' review line")
        if state in {"VERIFIED", "HOLD"} and "CHALLENGED" in verdicts:
            errors.append(f"{where}: Cross-check must stay CHALLENGED while a CHALLENGED review stands")

    for match, fields in blocks(lines, HANDOFF_HEAD):
        where = f"{rel}: handoff event by {match.group(1)}"
        if match.group(1) not in AGENT_NAMES:
            errors.append(f"{where}: '{match.group(1)}' is not a standard agent name")
        if field_names(fields) != HANDOFF_FIELDS:
            errors.append(f"{where}: HANDOFF fields {field_names(fields)} != {HANDOFF_FIELDS}")
        check_resource(field_value(fields, "Resource"), HANDOFF_RESOURCES, where, errors)

    for line in lines:
        section = SECTION_HEAD.match(line)
        if section and section.group(1) not in AGENT_NAMES:
            errors.append(f"{rel}: section agent '{section.group(1)}' is not a standard agent name")

    for match in ID_NEW.finditer(text):
        kind, agent, number = match.groups()
        width = 2 if kind == "H" else 3
        if agent not in AGENT_NAMES or len(number) != width:
            errors.append(f"{rel}: ID '{match.group(0)}' should be {kind}-<Agent>-{'N' * width}")
    for match in ID_OLD.finditer(text):
        errors.append(f"{rel}: legacy ID format '{match.group(0)}'")
    for match in AGENT_PROSE.finditer(text):
        errors.append(f"{rel}: write '{match.group(0)[6:]}' instead of '{match.group(0)}'")


def check_frontmatter(errors: list[str]) -> None:
    lines = (SKILL / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        errors.append("SKILL.md: missing frontmatter")
        return
    body = lines[1:lines.index("---", 1)]
    keys = [line.split(":", 1)[0] for line in body if line and not line.startswith(" ")]
    if keys != ["name", "description"]:
        errors.append(f"SKILL.md: frontmatter keys {keys} != ['name', 'description']")
    name_line = next((line for line in body if line.startswith("name:")), "")
    if name_line.split(":", 1)[-1].strip() != SKILL.name:
        errors.append(f"SKILL.md: name must equal directory name '{SKILL.name}'")


def check_manifests(errors: list[str]) -> None:
    manifests = {
        "plugin.json": ("version",),
        ".codex-plugin/plugin.json": ("version",),
        ".claude-plugin/plugin.json": ("version",),
        ".claude-plugin/marketplace.json": ("metadata", "version"),
        ".agents/plugins/marketplace.json": None,
    }
    versions = {}
    for rel, version_key in manifests.items():
        try:
            data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid JSON: {rel}: {exc}")
            continue
        if version_key:
            value = data
            for key in version_key:
                value = value.get(key, {}) if isinstance(value, dict) else {}
            versions[rel] = value
    if len(set(map(str, versions.values()))) > 1:
        errors.append(f"manifest versions differ: {versions}")

    openai_yaml = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for required in (
        "short_description: Orchestrate agent research",
        "- CHAT",
        "- CODEX",
        'brand_color: "#1687D9"',
    ):
        if required not in openai_yaml:
            errors.append(f"openai.yaml missing expected metadata: {required}")


def check_legacy_name(errors: list[str]) -> None:
    text_suffixes = {".md", ".json", ".yaml", ".yml", ".py", ".template", ".svg"}
    for path in ROOT.rglob("*"):
        if ".git" in path.relative_to(ROOT).parts:
            continue
        if path.is_file() and path.suffix.lower() in text_suffixes:
            if LEGACY_NAME in path.read_text(encoding="utf-8", errors="ignore"):
                errors.append(f"legacy name remains: {path.relative_to(ROOT)}")


def check_readme_images(errors: list[str]) -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for ref in re.findall(r'<img[^>]+src="([^"]+)"|!\[[^\]]*\]\(([^)\s]+)', text):
        src = next(part for part in ref if part)
        if "://" in src:
            continue
        path = ROOT / src
        if not path.is_file():
            errors.append(f"README image missing: {src}")
        elif path.suffix == ".svg":
            try:
                ElementTree.parse(path)
            except ElementTree.ParseError as exc:
                errors.append(f"README image is not valid SVG: {src}: {exc}")


def run_init(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    initializer = SKILL / "scripts" / "init_research_orchestrator.py"
    return subprocess.run(
        [sys.executable, str(initializer), str(target), "-n", "Validation Project", *args],
        text=True,
        capture_output=True,
    )


def check_initializer(errors: list[str]) -> None:
    outputs = ["agents.md", "plan.md", "discoveries.md", "handoff.md"]
    with tempfile.TemporaryDirectory() as tmp:
        cases = {"default": ([], ["Main"]), "count": (["--agents", "3"], ["Main", "A", "B"]),
                 "list": (["--agents", "main, a, aa"], ["Main", "A", "AA"])}
        for label, (args, expected) in cases.items():
            target = Path(tmp) / label
            target.mkdir()
            result = run_init(target, *args)
            if result.returncode != 0:
                errors.append(f"initializer ({label}) failed: {result.stderr.strip()}")
                continue
            for name in outputs:
                path = target / name
                if not path.exists():
                    errors.append(f"initializer ({label}) did not create {name}")
                    continue
                raw = path.read_bytes()
                if b"{{" in raw:
                    errors.append(f"initializer ({label}) left a placeholder in {name}")
                if b"\r\n" in raw:
                    errors.append(f"initializer ({label}) wrote CRLF line endings in {name}")
            plan = (target / "plan.md").read_text(encoding="utf-8")
            sections = re.findall(r"^## Agent: (\S+)", plan, flags=re.M)
            if sections != expected:
                errors.append(f"initializer ({label}) plan sections {sections} != {expected}")

        target = Path(tmp) / "default"
        plan = target / "plan.md"
        with plan.open("a", encoding="utf-8") as handle:
            handle.write("\nKEEP-ME\n")
        if run_init(target).returncode != 0 or "KEEP-ME" not in plan.read_text(encoding="utf-8"):
            errors.append("initializer overwrote existing plan.md")

        for bad in ("A,A", "Claude", "Main,Codex", "AAA", "0"):
            target = Path(tmp) / f"bad-{len(list(Path(tmp).iterdir()))}"
            target.mkdir()
            result = run_init(target, "--agents", bad)
            if result.returncode == 0 or any(target.iterdir()):
                errors.append(f"initializer accepted invalid --agents '{bad}'")


def main() -> int:
    errors: list[str] = []

    check_manifests(errors)
    check_legacy_name(errors)
    check_frontmatter(errors)
    check_readme_images(errors)
    for path in DOCS:
        check_doc(path, errors)
    check_initializer(errors)

    if errors:
        print("VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VALIDATION: PASS")
    print("- JSON manifests parse and share one version")
    print("- OpenAI metadata is aligned")
    print("- no legacy skill name remains")
    print("- SKILL.md frontmatter has only name and description")
    print("- README images exist and SVGs parse")
    print("- PLAN, DISCOVERIES, and HANDOFF examples use the exact field order")
    print("- discoveries record Host and Cross-check; reviews come from a different host")
    print("- Resource values are CPU/GPU/EITHER (plan) and CPU/GPU/Other/none (handoff)")
    print("- agent names and IDs follow Main, A-Z, AA-ZZ and H-<Agent>-NN / D-<Agent>-NNN")
    print("- initializer creates LF files, validates agent names, and preserves existing files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
