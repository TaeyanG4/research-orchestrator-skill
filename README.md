<p align="center">
  <img src="assets/readme/hero.png" alt="Research Orchestrator" width="100%">
</p>

# Research Orchestrator

A lightweight, hypothesis-driven research workflow for one or many AI agent sessions.

It keeps the system deliberately small: **four shared Markdown files**, a scored hypothesis queue, independent peer review, adaptive workers, and CPU/GPU/Other resource routing.

## What it solves

- Keep long-running research resumable across sessions.
- Let multiple agents explore independently without sharing unfinished reasoning.
- Turn completed experiments into shared discoveries instead of an ever-growing plan.
- Re-check another agent's conclusions instead of inheriting them automatically.
- Preserve promising but incomplete ideas with `HOLD` instead of forcing accept/reject decisions.
- Convert discoveries back into new hypotheses with explicit evidence and improvements.
- Scale from two workers to the practical full load of the current machine and available remote compute.

<p align="center">
  <img src="assets/readme/core-workflow.png" alt="Research Orchestrator core workflow" width="100%">
</p>

## The four files

<p align="center">
  <img src="assets/readme/document-roles.png" alt="Research Orchestrator document roles" width="100%">
</p>

| File | Purpose |
| --- | --- |
| `agents.md` | Stable rules for reading, editing, scoring, review, and resource routing. |
| `plan.md` | **Only active unfinished work.** Each agent owns a section and works from a scored queue. |
| `discoveries.md` | Shared reusable findings. Every agent reads it and records its own `CLOSED`, `HOLD`, or `CHALLENGED` verdict. |
| `handoff.md` | Operational history, active resumable state, artifacts, metrics, blockers, and next actions. |

Completed plan items **leave `plan.md`**. Their execution history goes to `handoff.md`, reusable knowledge goes to `discoveries.md`, and any follow-up hypotheses return to `plan.md` with fresh scores.

## Quick start

Initialize the four project files:

```bash
python skills/research-orchestrator-skill/scripts/init_research_orchestrator.py . -n "My Project"
```

Start with multiple independent agents:

```bash
python skills/research-orchestrator-skill/scripts/init_research_orchestrator.py . -n "My Project" --agents A,B
```

The initializer creates missing files only. Existing files are never overwritten.

---

# Install

This repository is packaged so the same Skill can be used from **Claude Code, Codex, and Google Antigravity**.

## Claude Code

### Recommended: install as a plugin from GitHub

Inside Claude Code:

```text
/plugin marketplace add TaeyanG4/research-orchestrator-skill
/plugin install research-orchestrator@research-orchestrator
```

Start a new Claude Code session after the first install.

### Project-only Skill install

Copy the Skill directory to:

```text
<project>/.claude/skills/research-orchestrator-skill/
```

Claude Code discovers a `SKILL.md` in that directory automatically.

## Codex

### Recommended: add the GitHub marketplace

From a terminal:

```bash
codex plugin marketplace add TaeyanG4/research-orchestrator-skill
codex
```

Then open:

```text
/plugins
```

Choose the **Research Orchestrator** marketplace/source and install `research-orchestrator`.

### Direct Skill install

Repo-scoped:

```text
<project>/.codex/skills/research-orchestrator-skill/
```

User-scoped:

```text
~/.codex/skills/research-orchestrator-skill/
```

Copy the repository's `skills/research-orchestrator-skill/` directory to one of those locations.

## Google Antigravity

Project/workspace scope:

```text
<project>/.agents/skills/research-orchestrator-skill/
```

Global scope:

```text
~/.gemini/config/skills/research-orchestrator-skill/
```

Copy `skills/research-orchestrator-skill/` into the chosen location. Antigravity discovers the `SKILL.md` automatically.

For older Antigravity CLI builds that still use the legacy CLI-specific global directory, use:

```text
~/.gemini/antigravity-cli/skills/research-orchestrator-skill/
```

---

# Core workflow

## 1. Discoveries create hypotheses

Every agent reads all of `discoveries.md`. A discovery can create **zero, one, or many** new hypotheses, and one new hypothesis can combine several discoveries.

A discovery's review verdict is per agent:

```markdown
## D-014 — Random CV may leak groups
- Source: Agent A
- Finding: duplicated groups cross random folds
- Evidence: e014_group_check.py; random CV 0.9162 vs group CV 0.9027
- Implication: current validation may be optimistic
- Reviews:
  - Agent A: CLOSED — source experiment consistently reproduces the effect
  - Agent B: HOLD — likely useful, but exact duplicates must be separated first
  - Agent C: CHALLENGED — effect disappears after a deduplication control
```

Meaning:

- `CLOSED`: this agent currently accepts the finding.
- `HOLD`: plausible and worth preserving, but more evidence or a specific improvement is needed.
- `CHALLENGED`: this agent found a material contradiction, flaw, or missing assumption.
- no entry: the agent has not reviewed it.

One agent's `CLOSED` never becomes another agent's verdict automatically.

## 2. New work enters the scored PLAN queue

Use one consistent hypothesis format:

```markdown
### H-B07 — Separate duplicate leakage from group leakage
- Sources: D-014, D-021
- Hypothesis: exact duplicates explain most of the apparent group leakage
- Evidence: D-014 weakens after deduplication; D-021 identifies repeated rows
- Improvement: isolate exact duplicates before constructing candidate groups
- Impact: 3
- Information: 3
- Confidence: 2
- Unblock: 3
- Diversity: 2
- Cost: 1
- Priority: 21
- Resource: CPU
- Parallel: YES
- Other: NONE
- Next test: compare random CV and GroupKFold after exact-duplicate removal
```

When a discovery is brought back into the plan, `Sources`, `Evidence`, and `Improvement` make the reason explicit. Do not simply rerun the same idea under a new task ID.

### Priority formula

Score each factor from 0 to 3:

```text
Priority = 2*Impact + 2*Information + Confidence + Unblock + Diversity + (3-Cost)
```

Run the highest score first unless blocked or explicitly overridden. Break ties by lower cost, then higher information value.

## 3. Adaptive workers use available compute

Start with **two workers** when parallelism is useful. Add more only while independent high-value work and compute headroom remain. There is no fixed worker ceiling; stop at the machine's practical full load before contention lowers throughput.

Each plan item declares:

```text
Resource: CPU | GPU | EITHER
Parallel: YES | NO
Other: NONE | <external executor>
```

Example:

```text
Other: Kaggle
```

Routing rule:

1. Idle GPU -> highest-priority compatible GPU/EITHER work.
2. Idle CPU -> highest-priority compatible CPU/EITHER work.
3. One busy, one idle -> fill the idle local resource with independent worthwhile work.
4. Both saturated -> eligible work may overflow to `Other` when the executor is available, suitable, and authorized.
5. Never run low-value work merely to keep hardware busy.

## 4. Completed work leaves PLAN

On completion:

```text
PLAN item
   |
   +--> HANDOFF       execution/result/history
   +--> DISCOVERIES   reusable knowledge/review
   +--> PLAN          new follow-up hypotheses, if any
   `--> removed       old completed item disappears from PLAN
```

`plan.md` should answer only one question: **what should this agent work on next?**

## 5. HANDOFF stays resumable

Use one event format:

```markdown
### 2026-10-05 21:10 — Agent B — H-B07
- Action: removed exact duplicates and rebuilt group candidates
- Result: random/group CV gap shrank from 0.0135 to 0.0041
- Evidence: experiments/e027_dedup_groups.py; outputs/e027.csv
- Discovery updates: D-014, D-028
- Review verdict: B:HOLD
- Files/metrics: CV 0.9071 / 0.9030
- Resource: CPU
- Other executor: none
- New plan items: H-B08, H-B09
- Next resumable action: test near-duplicate clusters
```

When `handoff.md` becomes hard to scan, archive older completed entries under `docs/` and keep the current state plus recent history in the root file.

---

# Repository layout

```text
research-orchestrator-skill/
├── README.md
├── LICENSE
├── plugin.json
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── .codex-plugin/
│   └── plugin.json
├── .agents/plugins/
│   └── marketplace.json
├── assets/readme/
│   ├── hero.png
│   ├── core-workflow.png
│   └── document-roles.png
└── skills/
    └── research-orchestrator-skill/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── scripts/init_research_orchestrator.py
        ├── templates/
        │   ├── AGENTS.md.template
        │   ├── PLAN.md.template
        │   ├── DISCOVERIES.md.template
        │   └── HANDOFF.md.template
        └── assets/icon.svg
```

# Design principles

- **Minimal shared state:** four coordination documents, not a hierarchy of worker folders.
- **Independent exploration:** unfinished agent plans stay separated.
- **Shared evidence:** completed findings flow through discoveries.
- **Per-agent judgment:** `CLOSED`, `HOLD`, and `CHALLENGED` are independent review verdicts.
- **Live queue only:** completed work does not accumulate in plan.
- **Evidence-backed retries:** a discovery returning to plan must state its evidence and improvement.
- **Adaptive concurrency:** worker count follows useful work and actual resource headroom.
- **Serialized shared edits:** re-read before patching shared files to reduce concurrent overwrite risk.

# Validation

The release is checked for:

- valid Skill frontmatter;
- consistent PLAN / DISCOVERIES / HANDOFF field names;
- matching review verdicts (`CLOSED`, `HOLD`, `CHALLENGED`);
- matching resource metadata (`CPU`, `GPU`, `EITHER`, `Other`);
- no stale legacy skill-name references;
- initializer behavior that preserves existing project files;
- valid JSON plugin/marketplace manifests.

# License

MIT.

## References for host-specific installation

- Claude Code Agent Skills / plugin marketplace: https://github.com/anthropics/skills
- Codex skills: https://developers.openai.com/blog/eval-skills
- Codex plugin packaging: https://developers.openai.com/plugins/build/plugins
- Google Antigravity Skills: https://codelabs.developers.google.com/getting-started-with-antigravity-skills
