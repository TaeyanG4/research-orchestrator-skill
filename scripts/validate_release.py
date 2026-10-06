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
    "Host", "User", "Action", "Result", "Artifacts", "Discovery updates",
    "Review verdict", "Resource", "Other executor", "New plan items",
]

READMES = {
    "README.md": "English",
    "README.ko.md": "한국어",
    "README.zh-CN.md": "简体中文",
    "README.ja.md": "日本語",
}
EXAMPLE = ROOT / "examples" / "cv-leakage-study"
# Must match how the example was generated.
EXAMPLE_INIT_ARGS = ["-n", "CV Leakage Study", "--agents", "3", "--user", "kim",
                     "--platform", "multi", "--platforms", "Claude Code, Codex", "--git", "push",
                     "--collector", "Claude Code/sonnet", "--queue-limits", "50,5",
                     "--reviewer", "Codex/sol", "--fallback", "wait"]

DOCS = [
    *(ROOT / name for name in READMES),
    SKILL / "SKILL.md",
    TEMPLATES / "AGENTS.md.template",
    TEMPLATES / "PLAN.md.template",
    TEMPLATES / "DISCOVERIES.md.template",
    TEMPLATES / "HANDOFF.md.template",
    *(EXAMPLE / name for name in ("agents.md", "plan.md", "discoveries.md", "handoff.md")),
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
NEW_ITEMS_IDS = re.compile(r"^H-[A-Za-z]+-\d{2}(?:, H-[A-Za-z]+-\d{2})*$")


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


def check_priority(fields: list[str], where: str, errors: list[str]) -> None:
    """When every factor is a concrete score, Priority must match the formula."""
    names = ["Impact", "Information", "Confidence", "Unblock", "Diversity", "Cost", "Priority"]
    values = [field_value(fields, name) or "" for name in names]
    if not all(value.isdigit() for value in values):
        return
    impact, information, confidence, unblock, diversity, cost, priority = map(int, values)
    if any(score > 3 for score in (impact, information, confidence, unblock, diversity, cost)):
        errors.append(f"{where}: scores must be 0-3")
    expected = 2 * impact + 2 * information + confidence + unblock + diversity + (3 - cost)
    if priority != expected:
        errors.append(f"{where}: Priority {priority} != formula result {expected}")


def check_doc(path: Path, errors: list[str]) -> None:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for match, fields in blocks(lines, PLAN_HEAD):
        where = f"{rel}: {match.group(1)}"
        if field_names(fields) != PLAN_FIELDS:
            errors.append(f"{where}: PLAN fields {field_names(fields)} != {PLAN_FIELDS}")
        check_resource(field_value(fields, "Resource"), PLAN_RESOURCES, where, errors)
        check_priority(fields, where, errors)

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
        # Real events (not the YYYY-MM-DD format sample) must list IDs or justify zero follow-ups.
        if not match.group(0).startswith("### YYYY"):
            new_items = field_value(fields, "New plan items") or ""
            if not (NEW_ITEMS_IDS.match(new_items) or new_items.startswith("none — ")):
                errors.append(f"{where}: New plan items '{new_items}' must list H- IDs or read 'none — <reason>'")
            updates = field_value(fields, "Discovery updates") or ""
            if not (updates.startswith("D-") or updates.startswith("none — ")):
                errors.append(f"{where}: Discovery updates '{updates}' must list D- IDs or read 'none — <reason>'")

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
    if re.search(r"\bMain\b", text):
        errors.append(f"{rel}: the Main slot was removed; slots start at A")


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


def readme_shape(text: str) -> tuple[int, int, list[str]]:
    """Structure that every translation must share with the English README."""
    images = re.findall(r'<img[^>]+src="([^"]+)"', text)
    return text.count("```"), len(re.findall(r"```mermaid", text)), images


def check_readmes(errors: list[str]) -> None:
    english_shape = readme_shape((ROOT / "README.md").read_text(encoding="utf-8"))
    for name, label in READMES.items():
        text = (ROOT / name).read_text(encoding="utf-8")

        # Language switcher: own language in bold, every other README linked.
        if f"<b>{label}</b>" not in text:
            errors.append(f"{name}: language switcher must show <b>{label}</b>")
        for other in READMES:
            if other != name and f'href="{other}"' not in text:
                errors.append(f"{name}: language switcher is missing a link to {other}")

        if name != "README.md" and readme_shape(text) != english_shape:
            errors.append(f"{name}: code blocks, diagrams, or images differ from README.md")

        # Every relative link and image must exist.
        refs = re.findall(r'(?:src|href)="([^"]+)"|\]\(([^)\s]+)\)', text)
        for ref in refs:
            target = next(part for part in ref if part).split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            path = ROOT / target
            if not path.exists():
                errors.append(f"{name}: broken link {target}")
            elif path.suffix == ".svg":
                try:
                    ElementTree.parse(path)
                except ElementTree.ParseError as exc:
                    errors.append(f"{name}: invalid SVG {target}: {exc}")


def run_checker(target: Path) -> subprocess.CompletedProcess[str]:
    checker = SKILL / "scripts" / "check_project.py"
    return subprocess.run([sys.executable, str(checker), str(target)], text=True,
                          capture_output=True, encoding="utf-8", errors="replace")


def check_example(errors: list[str]) -> None:
    """The worked example must match the current template and pass the consistency checker."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".git").mkdir()  # git sync needs a repository; otherwise it is switched off
        result = run_init(Path(tmp), *EXAMPLE_INIT_ARGS, name=None)
        if result.returncode != 0:
            errors.append(f"example: initializer failed: {result.stderr.strip()}")
            return
        expected = (Path(tmp) / "agents.md").read_text(encoding="utf-8")
        fresh = run_checker(Path(tmp))
        if fresh.returncode != 0:
            errors.append("check_project.py fails on a freshly initialized project:\n" + fresh.stdout.strip())
    if (EXAMPLE / "agents.md").read_text(encoding="utf-8") != expected:
        errors.append("examples/cv-leakage-study/agents.md is out of date with AGENTS.md.template")
    example = run_checker(EXAMPLE)
    if example.returncode != 0:
        errors.append("check_project.py fails on the worked example:\n" + example.stdout.strip())


def run_init(target: Path, *args: str, name: str | None = "Validation Project") -> subprocess.CompletedProcess[str]:
    initializer = SKILL / "scripts" / "init_research_orchestrator.py"
    name_args = ["-n", name] if name else []
    return subprocess.run(
        [sys.executable, str(initializer), str(target), *name_args, *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def check_initializer(errors: list[str]) -> None:
    outputs = ["agents.md", "plan.md", "discoveries.md", "handoff.md"]
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".git").mkdir()
        cases = {"default": ([], ["A"]), "count": (["--agents", "3"], ["A", "B", "C"]),
                 "list": (["--agents", "a, b, aa"], ["A", "B", "AA"])}
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

        for bad in ("A,A", "Claude", "A,Codex", "Main", "AAA", "0"):
            target = Path(tmp) / f"bad-{len(list(Path(tmp).iterdir()))}"
            target.mkdir()
            result = run_init(target, "--agents", bad)
            if result.returncode == 0 or any(target.iterdir()):
                errors.append(f"initializer accepted invalid --agents '{bad}'")

        bad_settings = {
            "user with a space": ["--user", "kim lee"],
            "user named like a slot": ["--user", "B"],
            "user named like a host": ["--user", "Codex"],
            "single without --platforms": ["--platform", "single"],
            "single with two platforms": ["--platform", "single", "--platforms", "Claude Code, Codex"],
            "multi with one platform": ["--platform", "multi", "--platforms", "Codex"],
            "unknown git mode": ["--git", "sometimes"],
            "unknown platform mode": ["--platform", "both"],
            "collector on a platform not listed": ["--platforms", "Claude Code, Codex", "--collector", "Gemini/pro"],
            "collector without a model": ["--collector", "Claude Code"],
            "reviewer on a platform not listed": ["--platform", "single", "--platforms", "Codex", "--reviewer", "Claude Code/opus"],
            "queue limits with resume >= stop": ["--queue-limits", "5,50"],
            "unknown fallback": ["--fallback", "sometimes"],
        }
        for label, args in bad_settings.items():
            target = Path(tmp) / f"bad-{len(list(Path(tmp).iterdir()))}"
            target.mkdir()
            result = run_init(target, *args)
            if result.returncode == 0 or any(target.iterdir()):
                errors.append(f"initializer accepted invalid settings ({label})")


def check_settings_modes(errors: list[str]) -> None:
    """Every platform/git combination renders cleanly and passes the checker; --reconfigure is safe."""
    combos = [("single", "Claude Code"), ("multi", "Claude Code, Codex"), ("adaptive", "Claude Code, Codex")]
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".git").mkdir()
        for mode, platforms in combos:
            for git in ("push", "commit", "off"):
                target = Path(tmp) / f"{mode}-{git}"
                target.mkdir()
                result = run_init(target, "--user", "kim", "--platform", mode, "--platforms", platforms, "--git", git)
                if result.returncode != 0:
                    errors.append(f"initializer ({mode}/{git}) failed: {result.stderr.strip()}")
                    continue
                agents = (target / "agents.md").read_text(encoding="utf-8")
                if "{{" in agents or "\n\n\n" in agents:
                    errors.append(f"agents.md ({mode}/{git}) has leftover template markers or blank-line runs")
                if (mode == "single") == ("Cross-host take-over by judgment" in agents):
                    errors.append(f"agents.md ({mode}) has the wrong cross-host take-over rules")
                if f"- Platform mode: {mode}" not in agents or f"- Git sync: {git}" not in agents:
                    errors.append(f"agents.md ({mode}/{git}) does not record its settings")
                checked = run_checker(target)
                if checked.returncode != 0:
                    errors.append(f"check_project.py fails on a fresh {mode}/{git} project:\n" + checked.stdout.strip())

        target = Path(tmp) / "single-off"
        result = run_init(target, "--reconfigure", "--platform", "multi", "--platforms", "Claude Code, Codex",
                          "--git", "push", name=None)
        agents = (target / "agents.md").read_text(encoding="utf-8")
        if result.returncode != 0 or "- Platform mode: multi" not in agents or "- Git sync: push" not in agents:
            errors.append(f"--reconfigure did not switch single/off to multi/push: {result.stderr.strip()}")
        with (target / "agents.md").open("a", encoding="utf-8") as handle:
            handle.write("\nHAND-EDIT\n")
        refused = run_init(target, "--reconfigure", "--git", "off", name=None)
        if refused.returncode == 0 or "HAND-EDIT" not in (target / "agents.md").read_text(encoding="utf-8"):
            errors.append("--reconfigure overwrote a hand-edited agents.md without --force")
        forced = run_init(target, "--reconfigure", "--git", "off", "--force", name=None)
        if forced.returncode != 0 or "- Git sync: off" not in (target / "agents.md").read_text(encoding="utf-8"):
            errors.append("--reconfigure --force did not rewrite agents.md")

        # Direct edits: runtime settings apply at once; mode/git edits are applied by --reconfigure.
        target = Path(tmp) / "multi-push"
        agents_md = target / "agents.md"
        text = agents_md.read_text(encoding="utf-8")
        text = text.replace("- Plan collector: off", "- Plan collector: on — Codex / sol")
        text = text.replace("- Platform mode: multi", "- Platform mode: single").replace(
            "- Platforms: Claude Code, Codex", "- Platforms: Codex")
        agents_md.write_text(text, encoding="utf-8", newline="\n")
        stale = run_checker(target)
        if "do not match its Platform mode" not in stale.stdout:
            errors.append("check_project.py did not note rules that are out of sync with edited settings")
        applied = run_init(target, "--reconfigure", name=None)
        text = agents_md.read_text(encoding="utf-8")
        if (applied.returncode != 0 or "Cross-host take-over by judgment" in text
                or "- Plan collector: on — Codex / sol" not in text or "- Platform mode: single" not in text):
            errors.append(f"--reconfigure did not apply directly edited settings: {applied.stderr.strip()}")
        if run_checker(target).returncode != 0:
            errors.append("check_project.py fails after applying directly edited settings")

    # Outside a git repository, git sync is reported and switched off; nothing is created.
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "no-repo"
        target.mkdir()
        result = run_init(target, "--git", "push")
        agents = (target / "agents.md").read_text(encoding="utf-8") if (target / "agents.md").exists() else ""
        if result.returncode != 0 or "- Git sync: off" not in agents or "not inside a git repository" not in result.stderr:
            errors.append("initializer outside a git repository must switch Git sync to off and say so")
        if any(p.name == ".git" for p in Path(tmp).rglob(".git")):
            errors.append("initializer created a git repository; it must never run git init")
        again = run_init(target, "--reconfigure", "--git", "commit", name=None)
        if again.returncode != 0 or "- Git sync: off" not in (target / "agents.md").read_text(encoding="utf-8"):
            errors.append("--reconfigure outside a git repository must keep Git sync off")


def main() -> int:
    # Error messages can quote CJK README text; never crash on a legacy console code page.
    sys.stdout.reconfigure(errors="backslashreplace")
    errors: list[str] = []

    check_manifests(errors)
    check_legacy_name(errors)
    check_frontmatter(errors)
    check_readmes(errors)
    for path in DOCS:
        check_doc(path, errors)
    check_example(errors)
    check_initializer(errors)
    check_settings_modes(errors)

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
    print("- all READMEs have the language switcher, working links, valid SVGs, and the same structure")
    print("- PLAN, DISCOVERIES, and HANDOFF blocks use the exact field order (docs, templates, example)")
    print("- concrete Priority values match the formula")
    print("- real handoff events list new plan items and discovery updates or give 'none - <reason>'")
    print("- the worked example matches the current template and passes check_project.py")
    print("- check_project.py passes on a freshly initialized project")
    print("- every platform mode (single/multi/adaptive) x git mode (push/commit/off) renders and passes")
    print("- --reconfigure switches settings, applies directly edited settings, and refuses to overwrite hand-edited rules")
    print("- collector, reviewer, queue limits, and fallback settings are validated")
    print("- outside a git repository, git sync is reported and switched off; no repository is created")
    print("- discoveries record Host and Cross-check; reviews come from a different host")
    print("- Resource values are CPU/GPU/EITHER (plan) and CPU/GPU/Other/none (handoff)")
    print("- agent names and IDs follow A-Z, AA-ZZ and H-<Agent>-NN / D-<Agent>-NNN")
    print("- initializer creates LF files, validates agent names, and preserves existing files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
