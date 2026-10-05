#!/usr/bin/env python3
"""Check that a project's agents.md, plan.md, discoveries.md, and handoff.md agree with each other.

Run at session start, after a take-over, and before closing:

    python <skill-root>/scripts/check_project.py [project-dir]

Exit code 0 means no problems; 1 means problems were found; 2 means files are missing.
Only structured lines are checked (headings and "- Field:" bullets outside code fences),
so the format examples and prose that the templates contain are ignored.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
import string
import sys


AGENT_NAMES = {*string.ascii_uppercase, *(a + b for a in string.ascii_uppercase for b in string.ascii_uppercase)}
PLAN_FIELDS = [
    "Sources", "Hypothesis", "Evidence", "Improvement", "Impact", "Information", "Confidence",
    "Unblock", "Diversity", "Cost", "Priority", "Resource", "Parallel", "Other", "Next test",
]
DISCOVERY_FIELDS = ["Source", "Host", "Cross-check", "Finding", "Evidence", "Implication", "Reviews"]
EVENT_FIELDS = [
    "Host", "Action", "Result", "Artifacts", "Discovery updates", "Review verdict",
    "Resource", "Other executor", "New plan items",
]
CROSS_CHECK_STATES = {"PENDING", "REVIEWING", "VERIFIED", "HOLD", "CHALLENGED"}
VERDICT_FOR_STATE = {"VERIFIED": "CLOSED", "HOLD": "HOLD", "CHALLENGED": "CHALLENGED"}
FREE_HOSTS = {"unassigned", "released"}

H_ID = re.compile(r"\bH-[A-Za-z]+-\d+\b")
D_ID = re.compile(r"\bD-[A-Za-z]+-\d+\b")
FIELD = re.compile(r"^- ([A-Za-z/() -]+?):\s?(.*)$")
REVIEW = re.compile(r"^\s+- (.+?) \((\S+)\): (\S+) — ")
SHARED_VALUE = re.compile(r"(?i)\b(champion|current best|best model|baseline)\b\s*[:=]")


@dataclass
class Block:
    key: str
    line: int
    title: str = ""
    owner: str = ""
    fields: dict[str, str] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)


def unfenced(text: str) -> list[str]:
    """Return lines with fenced code blocks blanked out, keeping line numbers."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
        else:
            out.append("" if fenced else line)
    return out


def collect_fields(lines: list[str], start: int, block: Block) -> int:
    """Read consecutive '- Field:' lines (and indented sub-bullets) after a heading."""
    i = start
    while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  - ")):
        line = lines[i]
        match = FIELD.match(line)
        if match and not line.startswith("  "):
            block.fields[match.group(1)] = match.group(2).strip()
            block.order.append(match.group(1))
        else:
            block.extra.append(line)
        i += 1
    return i


class Checker:
    def __init__(self, root: Path):
        self.root = root
        self.problems: list[str] = []
        self.notes: list[str] = []

    def problem(self, where: str, message: str, owner: str = "") -> None:
        tag = f"[{owner}] " if owner else ""
        self.problems.append(f"{tag}{where}: {message}")

    # ---------- parsing ----------

    def parse_plan(self, lines: list[str]) -> None:
        self.plan_sections: list[str] = []
        self.plan_items: dict[str, Block] = {}
        self.retired: set[str] = set()
        section = ""
        i = 0
        while i < len(lines):
            line = lines[i]
            n = i + 1
            if line.startswith("## Agent: "):
                section = line[len("## Agent: "):].strip()
                if section in self.plan_sections:
                    self.problem(f"plan.md:{n}", f"duplicate section for agent {section}", section)
                self.plan_sections.append(section)
            elif line.startswith("### H-"):
                head = line[4:]
                item_id, _, title = head.partition(" — ")
                block = Block(key=item_id.strip(), line=n, title=title, owner=section)
                i = collect_fields(lines, i + 1, block)
                self.add_plan_item(block)
                self.retired.update(re.findall(r"\(from (H-[A-Za-z]+-\d+)\)", title))
                continue
            elif line.startswith("#"):
                if not line.startswith("# "):
                    self.problem(f"plan.md:{n}", f"unexpected heading '{line.strip()}'; plan.md holds plan items only")
            elif line.startswith("- ") or line.startswith("  - "):
                self.problem(f"plan.md:{n}", f"line outside any plan item: '{line.strip()[:60]}'", section)
            elif section and line.strip() and not line.strip().startswith("_"):
                self.problem(f"plan.md:{n}", f"text inside agent section {section} that is not a plan item: '{line.strip()[:60]}'", section)
            if SHARED_VALUE.search(line):
                self.problem(
                    f"plan.md:{n}",
                    f"project-wide value '{line.strip()[:60]}' belongs in handoff.md Shared state, not plan.md",
                    section,
                )
            i += 1

    def add_plan_item(self, block: Block) -> None:
        where = f"plan.md:{block.line}"
        if block.key in self.plan_items:
            self.problem(where, f"duplicate plan item ID {block.key}", block.owner)
        self.plan_items[block.key] = block
        if not block.owner:
            self.problem(where, f"{block.key} is not inside any '## Agent:' section")
        elif not block.key.startswith(f"H-{block.owner}-"):
            self.problem(where, f"{block.key} sits in agent {block.owner}'s section but carries another owner's prefix", block.owner)
        if block.order != PLAN_FIELDS:
            missing = [f for f in PLAN_FIELDS if f not in block.order]
            self.problem(where, f"{block.key} fields do not match the plan format (missing: {missing or 'none'}; check order)", block.owner)

    def parse_discoveries(self, lines: list[str]) -> None:
        self.discoveries: dict[str, Block] = {}
        self.discovery_order: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("## D-"):
                disc_id, _, title = line[3:].partition(" — ")
                block = Block(key=disc_id.strip(), line=i + 1, title=title)
                i = collect_fields(lines, i + 1, block)
                block.owner = block.fields.get("Source", "")
                if block.key in self.discoveries:
                    self.problem(f"discoveries.md:{block.line}", f"duplicate discovery ID {block.key}", block.owner)
                self.discoveries[block.key] = block
                self.discovery_order.append(block.key)
                continue
            i += 1

    def parse_handoff(self, lines: list[str]) -> None:
        self.shared: dict[str, str] = {}
        self.handoff_sections: dict[str, Block] = {}
        self.events: list[Block] = []
        area = ""
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("## "):
                area = line[3:].strip().lower()
            elif area.startswith("shared state") and line.startswith("- "):
                match = FIELD.match(line)
                if match:
                    self.shared[match.group(1)] = match.group(2).strip()
            elif line.startswith("### Agent: "):
                block = Block(key=line[len("### Agent: "):].strip(), line=i + 1)
                i = collect_fields(lines, i + 1, block)
                if block.key in self.handoff_sections:
                    self.problem(f"handoff.md:{block.line}", f"duplicate handoff section for agent {block.key}", block.key)
                self.handoff_sections[block.key] = block
                continue
            elif re.match(r"^### \d{4}-\d{2}-\d{2} \d{2}:\d{2} — ", line):
                parts = line[4:].split(" — ")
                block = Block(key=parts[2].strip() if len(parts) > 2 else "", line=i + 1,
                              owner=parts[1].strip() if len(parts) > 1 else "")
                i = collect_fields(lines, i + 1, block)
                self.events.append(block)
                continue
            i += 1

    # ---------- checks ----------

    def check_agents(self) -> None:
        listed_raw = self.shared.get("Active agent(s)")
        if listed_raw is None:
            self.problem("handoff.md", "Shared state has no 'Active agent(s)' line")
            listed: list[str] = []
        else:
            listed = [a.strip() for a in listed_raw.split(",") if a.strip()]
        for name in set(listed) | set(self.plan_sections) | set(self.handoff_sections):
            if name not in AGENT_NAMES:
                self.problem("handoff.md/plan.md", f"'{name}' is not a valid agent name (use A-Z, AA-ZZ)", name)
                continue
            missing = [
                label for label, present in (
                    ("Active agent(s)", name in listed),
                    ("a '## Agent:' section in plan.md", name in self.plan_sections),
                    ("a '### Agent:' section in handoff.md", name in self.handoff_sections),
                ) if not present
            ]
            if missing:
                self.problem("plan.md/handoff.md", f"agent {name} is missing {', '.join(missing)}", name)

    def check_handoff_sections(self) -> None:
        for name, block in self.handoff_sections.items():
            where = f"handoff.md:{block.line}"
            for required in ("Current host", "Current thread", "Next action"):
                if required not in block.fields:
                    self.problem(where, f"agent {name}'s section has no '{required}' line", name)
            thread_ids = H_ID.findall(block.fields.get("Current thread", "").split(" ", 1)[0])
            next_ids = H_ID.findall(block.fields.get("Next action", ""))
            for item_id in dict.fromkeys(thread_ids + next_ids):
                item = self.plan_items.get(item_id)
                if item is None:
                    self.problem(where, f"agent {name}'s handoff names {item_id}, but it is not in plan.md", name)
                elif item.owner != name:
                    self.problem(where, f"agent {name}'s handoff names {item_id}, which sits in {item.owner}'s plan section", name)

    def check_events(self) -> None:
        # An event's heading names the plan item it completed; 'none' means it completed nothing.
        finished = {e.key for e in self.events
                    if e.key.lower() != "none" and not e.fields.get("Action", "").startswith("took over")}
        taken_over = set(self.retired)
        for event in self.events:
            action = event.fields.get("Action", "")
            taken_over.update(re.findall(r"took over (H-[A-Za-z]+-\d+)", action))
            finished.update(re.findall(r"removed (H-[A-Za-z]+-\d+)", action))

        for index, event in enumerate(self.events):
            where = f"handoff.md:{event.line}"
            if event.order != EVENT_FIELDS:
                missing = [f for f in EVENT_FIELDS if f not in event.order]
                self.problem(where, f"event fields do not match the handoff format (missing: {missing or 'none'}; check order)", event.owner)
            action = event.fields.get("Action", "")
            if event.key.lower() != "none" and not H_ID.fullmatch(event.key):
                self.problem(where, f"event heading ends in '{event.key}'; use the completed plan item ID or 'none'", event.owner)
            for item_id in re.findall(r"removed (H-[A-Za-z]+-\d+)", action):
                if item_id in self.plan_items:
                    self.problem(where, f"{item_id} is logged as removed but is still in plan.md", event.owner)
            if event.key in self.plan_items and not action.startswith("took over"):
                self.problem(where, f"{event.key} is logged as finished but is still in plan.md", event.owner)
            for name in ("Discovery updates", "New plan items"):
                value = event.fields.get(name, "")
                if value.lower() == "none" or value == "":
                    self.problem(where, f"'{name}' must list IDs or read 'none — <reason>'", event.owner)
            later = {e.key for e in self.events[index + 1:] if not e.fields.get("Action", "").startswith("took over")}
            for item_id in H_ID.findall(event.fields.get("New plan items", "")):
                if item_id in self.plan_items or item_id in later or item_id in taken_over:
                    continue
                if item_id in finished:
                    continue
                self.problem(
                    where,
                    f"{item_id} was queued here but is not in plan.md and was never finished or taken over",
                    event.owner,
                )
            for name in ("Discovery updates", "Review verdict"):
                for disc_id in D_ID.findall(event.fields.get(name, "")):
                    if disc_id not in self.discoveries:
                        self.problem(where, f"'{name}' names {disc_id}, which is not in discoveries.md", event.owner)

    def check_retired(self) -> None:
        for item_id in self.retired:
            if item_id in self.plan_items:
                self.problem(f"plan.md:{self.plan_items[item_id].line}", f"{item_id} was taken over (retired) but is still in plan.md",
                             self.plan_items[item_id].owner)

    def check_plan_sources(self) -> None:
        for item in self.plan_items.values():
            for disc_id in D_ID.findall(item.fields.get("Sources", "")):
                if disc_id not in self.discoveries:
                    self.problem(f"plan.md:{item.line}", f"{item.key} cites {disc_id}, which is not in discoveries.md", item.owner)

    def check_discoveries(self) -> None:
        for disc in self.discoveries.values():
            where = f"discoveries.md:{disc.line}"
            if disc.order != DISCOVERY_FIELDS:
                missing = [f for f in DISCOVERY_FIELDS if f not in disc.order]
                self.problem(where, f"{disc.key} fields do not match the discovery format (missing: {missing or 'none'}; check order)", disc.owner)
            raw_state = disc.fields.get("Cross-check", "")
            state = raw_state.split(" ", 1)[0]
            if state not in CROSS_CHECK_STATES:
                self.problem(where, f"{disc.key} has unknown Cross-check state '{raw_state}'", disc.owner)
            verdicts = [m.group(3) for line in disc.extra if (m := REVIEW.match(line))]
            if state in VERDICT_FOR_STATE and VERDICT_FOR_STATE[state] not in verdicts:
                self.problem(where, f"{disc.key} is {state} but has no '{VERDICT_FOR_STATE[state]}' review line", disc.owner)
            if state in {"VERIFIED", "HOLD"} and "CHALLENGED" in verdicts:
                self.problem(where, f"{disc.key} must stay CHALLENGED while a CHALLENGED review stands", disc.owner)
            if state == "REVIEWING":
                claim = re.search(r"\((\S+)\)\s*$", raw_state)
                claimer = claim.group(1) if claim else ""
                section = self.handoff_sections.get(claimer)
                if section is None:
                    self.problem(where, f"{disc.key} is claimed by '{claimer}', which has no handoff section", disc.owner)
                elif section.fields.get("Current host", "").lower() in FREE_HOSTS:
                    self.problem(where, f"{disc.key} is still claimed by {claimer}, but that slot is released; reset it to PENDING", claimer)

    def check_current_best(self) -> None:
        value = self.shared.get("Current best")
        if value is None:
            self.problem("handoff.md", "Shared state has no 'Current best' line (use 'none yet' until a result sets it)")
            return
        setters = [d for d in self.discovery_order
                   if self.discoveries[d].fields.get("Implication", "").lower().startswith("new current best:")
                   and not self.discoveries[d].fields.get("Cross-check", "").startswith("CHALLENGED")]
        cited = D_ID.findall(value)
        if value.lower().startswith("none"):
            if setters:
                self.problem("handoff.md", f"Current best says '{value}', but {setters[-1]} set a new current best")
            return
        if not cited:
            self.problem("handoff.md", f"Current best '{value}' must cite the discovery that set it")
            return
        for disc_id in cited:
            if disc_id not in self.discoveries:
                self.problem("handoff.md", f"Current best cites {disc_id}, which is not in discoveries.md")
        if setters and setters[-1] not in cited:
            self.problem("handoff.md", f"Current best is stale: it cites {', '.join(cited)}, but the latest new best is {setters[-1]}")
        for disc_id in cited:
            disc = self.discoveries.get(disc_id)
            if disc and disc.fields.get("Cross-check", "").startswith("CHALLENGED"):
                self.problem("handoff.md", f"Current best cites {disc_id}, which is CHALLENGED")

    def check_open_issues(self) -> None:
        value = self.shared.get("Open consistency issues")
        if value is None:
            self.problem("handoff.md", "Shared state has no 'Open consistency issues' line (use 'none')")
        elif value.lower() != "none":
            self.notes.append(f"open consistency issues recorded in Shared state: {value}")

    def run(self) -> int:
        files = {name: self.root / name for name in ("agents.md", "plan.md", "discoveries.md", "handoff.md")}
        missing = [name for name, path in files.items() if not path.is_file()]
        if missing:
            print(f"CONSISTENCY: missing {', '.join(missing)} in {self.root}")
            return 2
        self.parse_plan(unfenced(files["plan.md"].read_text(encoding="utf-8")))
        self.parse_discoveries(unfenced(files["discoveries.md"].read_text(encoding="utf-8")))
        self.parse_handoff(unfenced(files["handoff.md"].read_text(encoding="utf-8")))
        self.check_agents()
        self.check_handoff_sections()
        self.check_events()
        self.check_retired()
        self.check_plan_sources()
        self.check_discoveries()
        self.check_current_best()
        self.check_open_issues()

        for note in self.notes:
            print(f"note: {note}")
        if self.problems:
            print(f"CONSISTENCY: {len(self.problems)} problem(s)")
            for problem in self.problems:
                print(f"- {problem}")
            print("Fix problems tagged with your own agent; record others under 'Open consistency issues'.")
            return 1
        print(f"CONSISTENCY: OK ({len(self.plan_items)} plan items, {len(self.discoveries)} discoveries, "
              f"{len(self.events)} events, agents {', '.join(self.plan_sections) or 'none'})")
        return 0


def main() -> int:
    sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Check that the four Research Orchestrator files agree.")
    parser.add_argument("target", nargs="?", default=".", help="Project directory")
    args = parser.parse_args()
    return Checker(Path(args.target).resolve()).run()


if __name__ == "__main__":
    sys.exit(main())
