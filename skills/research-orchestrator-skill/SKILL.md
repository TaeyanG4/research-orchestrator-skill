---
name: research-orchestrator-skill
description: "Orchestrate hypothesis-driven research across one or many agent sessions using a scored PLAN queue, shared DISCOVERIES that a different host cross-checks once, adaptive workers, CPU/GPU/Other resource routing, and a durable HANDOFF log. Use when starting or resuming research, coordinating parallel experiments, prioritizing hypotheses, cross-checking conclusions from another host such as Codex or Claude Code, scaling work to available compute, or preserving project continuity across sessions."
---

# Research Orchestrator

Use exactly four project-level coordination files, always with these lowercase names:

```text
agents.md        # stable operating rules
plan.md          # active unfinished work only, separated by agent
discoveries.md   # shared reusable findings, cross-checked once by a different host
handoff.md       # operational history and resumable state
```

Do not create per-agent continuity folders, mode files, or a separate process file. Create `docs/` only when older handoff history becomes too large to scan comfortably.

## 1. Identify the current agent

An agent name is a **work slot**, not the identity of the tool or model running it. The same slot can be continued by Claude Code, Codex, Antigravity, or any other host.

Allowed names, assigned in this order:

```text
Main, A, B, C, ... Z, AA, AB, ... ZZ
```

- `Main` is the default slot. Single-agent work always uses `Main`.
- Each additional concurrent session takes the next unused letter: the second is `A`, the third is `B`, and so on. After `Z` come two-letter names in spreadsheet-column order (`AA`, `AB`, ...). Slots are reused once released, so new letters are needed only when every existing slot is taken at the same time.
- Never use a host, product, or model name (`Claude`, `Codex`, `GPT`, `Gemini`, `Antigravity`, `Opus`, `Sonnet`, ...) or a free-form role name as an agent name.
- Track hosts in fields, never in the name:
  - `Current host` in the agent's active handoff section (`handoff.md`) says which host owns the slot right now. Set it whenever a session takes or resumes the slot.
  - `Host` in each completed-log event (`handoff.md`) says which host did that step.
  - `Host` in each discovery (`discoveries.md`) says which host made it; a different host cross-checks it (section 5).
- Continue the same thread with the same agent name, even when a different host resumes it; only `Current host` changes.
- A slot is **free** when its `Current host` is `unassigned` or `released`, and **taken** otherwise. Liveness is never guessed; it is read from that line.
- If the user assigns a name, use it. Otherwise read only the `Current host` line of each agent section in `handoff.md` and take the first free slot in order (`Main`, `A`, `B`, ...). If none is free, create the next unused letter: add its `## Agent:` plan section, its `### Agent:` handoff section, and its name under `Active agent(s)`.
- When you take or resume a slot, set `Current host: <your host>` first. When you close the session, set `Current host: released` (section 10). A slot left taken by a crashed session may be reclaimed only when the user says so.
- Add agents only when independent useful work exists.

Every ID embeds the owning agent name so concurrent agents never collide:

| Object | Format | Examples |
| --- | --- | --- |
| Plan item | `H-<Agent>-<NN>` | `H-Main-01`, `H-A-07` |
| Discovery | `D-<Agent>-<NNN>` | `D-Main-001`, `D-B-014` |
| Plan / handoff section | `Agent: <Agent>` | `## Agent: Main` |
| Discovery review | `<Host> (<Agent>): <VERDICT>` | `Claude Code (Main): CLOSED` |

Each agent numbers only its own IDs, sequentially, and never reuses a number.

## 2. Read in this order

1. Read `agents.md`.
2. Read all of `discoveries.md`.
3. Read the shared completed/review log in `handoff.md` plus only the current agent's active handoff section.
4. Read only the current agent's detailed section in `plan.md`.

Three narrow exceptions allow looking across other agents' sections:

- A resource dispatcher may inspect only task metadata: task ID, owner, priority, resource, parallel-safety, and `Other` executor.
- Before adding a plan item, any agent may scan only item headings and `Hypothesis` lines to avoid queueing a duplicate (section 3).
- When choosing a slot, a session may read only the `Current host` line of each agent's handoff section (section 1).

Do not read another active agent's detailed evidence, scores, next tests, or resumable state merely for coordination.

## 3. Keep `plan.md` as a scored live queue

Store only active unfinished hypotheses, experiments, reviews, or next actions. Each agent edits only its own section unless explicitly asked otherwise.

Use this exact item shape:

```markdown
### H-Main-01 — Short title
- Sources: D-A-003, D-Main-008 / none
- Hypothesis: ...
- Evidence: ...
- Improvement: ...
- Impact: 0-3
- Information: 0-3
- Confidence: 0-3
- Unblock: 0-3
- Diversity: 0-3
- Cost: 0-3
- Priority: <calculated score>
- Resource: CPU | GPU | EITHER
- Parallel: YES | NO
- Other: NONE | <external executor>
- Next test: ...
```

Field rules:

- `Sources`: zero, one, or many discovery IDs that motivated the item.
- `Hypothesis`: the claim to test.
- `Evidence`: current reason the hypothesis deserves attention. If it comes from discoveries, cite the relevant evidence rather than only the ID.
- `Improvement`: what is being strengthened, changed, or resolved compared with the source discovery or previous attempt. Use `none` only when genuinely not applicable.
- `Next test`: the smallest useful test that can change a decision.

A single discovery may generate many plan items. One plan item may combine many discoveries. A nontrivial cross-check of another host's discovery may itself be a scored plan item.

### Before adding a plan item

Run this check every time, so the same idea is never queued twice or re-tested after it was already settled:

1. **Search `discoveries.md`** for the same claim, including negative results (`Finding: ... does not hold`).
   - `VERIFIED` and the claim is the same → do not add it. Add only a materially different follow-up with `Improvement`.
   - `CHALLENGED` → do not add it until the challenge is resolved.
   - `HOLD` → add it only when the stated condition is now met, and say so in `Evidence`.
   - `PENDING` / `REVIEWING` → prefer cross-checking it (if you are on a different host) over re-running it.
2. **Search the completed log in `handoff.md`** (and `docs/` archives) for a prior attempt. If one exists, cite it in `Sources` or `Evidence` and fill `Improvement` with what is different now.
3. **Scan the other agents' plan sections for the same hypothesis**, reading only each item's heading (`### H-X-NN — title`) and `Hypothesis` line, nothing else. If another agent already has it queued, do not add it. If yours is materially different, add it and cite the other item ID in `Evidence`.
4. **Re-read `plan.md`** immediately before writing (section 9); if the same item appeared meanwhile, keep the earlier one.

A plan item without a real `Improvement` over a settled discovery or a prior attempt is a duplicate, not a new hypothesis.

### Priority scoring

Score each factor from 0 to 3:

- `Impact`: expected value if successful.
- `Information`: uncertainty resolved or future decisions changed.
- `Confidence`: strength of evidence that the direction is worth testing.
- `Unblock`: how much it removes a dependency or bottleneck.
- `Diversity`: how different it is from already explored paths.
- `Cost`: time/compute/risk, where 0 is cheap and 3 is expensive.

Calculate (range 0-24):

```text
Priority = 2*Impact + 2*Information + Confidence + Unblock + Diversity + (3-Cost)
```

Work highest score first unless blocked or explicitly overridden. Break ties by lower `Cost`, then higher `Information`.

Whenever a new discovery or review verdict changes the evidence, rescore affected active items.

## 4. Remove completed work from `plan.md`

When a plan item finishes:

1. Append the action and outcome to `handoff.md`.
2. Record the result in `discoveries.md`: reusable knowledge when useful, and **always** a negative-result discovery (`Finding: <claim> does not hold under <conditions>`) when the hypothesis failed or was disproved.
3. Add any follow-up hypotheses to `plan.md` with fresh scores.
4. Remove the completed item from `plan.md`.

Do not accumulate `[done]` items in `plan.md`. A failed or disproved hypothesis is still completed work and must leave the live queue. Because `discoveries.md` is the one file every agent reads in full, it is also the index of settled ideas: a failed hypothesis that is not recorded there will eventually be proposed again.

## 5. Use `discoveries.md` as shared knowledge with cross-host verification

Every agent reads the whole file. Verification is per **host**, not per agent: a discovery made on one host is checked **once** by a different host. Sessions on the same host share the same blind spots, so they do not re-review each other, and ten sessions never have to review the same finding ten times.

Use this exact shape:

```markdown
## D-A-014 — Short title
- Source: A
- Host: Codex
- Cross-check: VERIFIED
- Finding: ...
- Evidence: ...
- Implication: ...
- Reviews:
  - Claude Code (Main): CLOSED — reproduced independently with ...
```

`Cross-check` is the discovery's verification state:

- `PENDING`: no different host has reviewed it yet. New discoveries start here.
- `REVIEWING <Host> (<Agent>)`: a different-host session has claimed the review, for example `REVIEWING Claude Code (Main)`.
- `VERIFIED`: a different host reviewed it and recorded `CLOSED`.
- `HOLD`: a different host found it plausible but needs specific evidence, a condition change, or an improvement first.
- `CHALLENGED`: a host found a material contradiction, flaw, or missing assumption.

Review lines use `<Host> (<Agent>): <VERDICT> — reason`, where the verdict is `CLOSED`, `HOLD`, or `CHALLENGED`. `Cross-check` mirrors the latest cross-host verdict (`CLOSED` → `VERIFIED`), except that any standing `CHALLENGED` wins until it is resolved.

Rules:

- The source does not review its own discovery; the discovery is its claim.
- Review only discoveries whose `Host` differs from yours and whose `Cross-check` is `PENDING`, or `HOLD` when its stated condition is now met.
- Claim a review by setting `Cross-check: REVIEWING <your host> (<your agent>)` before starting, so two sessions do not review the same discovery. Take over a claim only when the claiming agent's `Current host` reads `released` or `unassigned` (the one line you may read, section 2), or the user says so.
- One cross-host review is enough. Add another only when the discovery is high impact or disputed.
- A `HOLD` or `CHALLENGED` review must state what evidence or change would make the discovery acceptable.
- When the source revises a `HOLD` or `CHALLENGED` discovery with new evidence, it updates `Evidence`, keeps the old reviews, and resets `Cross-check` to `PENDING`.
- If only one host is available, a session in a different slot on the same host may do the cross-check; begin its reason with `same host —`.
- Do not archive `discoveries.md` merely because it grows; merge duplicates instead.

Using discoveries as premises:

- `VERIFIED` discoveries may be used freely.
- `PENDING`, `REVIEWING`, or `HOLD` discoveries may be used, but the plan item's `Evidence` must say the premise is not yet verified. When it is a high-priority premise and you are on a different host, review it first.
- Do not build on a `CHALLENGED` discovery until it is resolved.

### Move a discovery back into the plan

When a discovery in any state suggests new work, create zero, one, or many new plan items as warranted, in the current agent's own section.

Every plan item derived from discoveries must include:

- `Sources`: the discovery IDs.
- `Evidence`: the concrete evidence that makes the new hypothesis worth testing.
- `Improvement`: the missing proof, changed condition, stronger method, or specific weakness the new test will address.

Do not write only `Sources: D-A-014` and repeat the same experiment. Explain why the new attempt is materially better or different. Do not edit another agent's active plan merely because its discovery suggested a direction.

## 6. Scale workers from 2 to practical full load

When parallel work is useful, start with two independent agents (`Main` and `A`). Add more only while all are true:

- independent high-value plan items remain;
- CPU, GPU, RAM, disk I/O, and remote quotas have headroom;
- added workers do not materially reduce throughput;
- workers are not duplicating work unless deliberate replication is the goal.

There is no fixed maximum. Practical full load is the highest useful concurrency the current machine and available remote compute can sustain without harmful contention. Scale down when throughput worsens, memory pressure appears, tasks become dependent, or the queue becomes too small.

Reasoning-only sessions may outnumber heavy compute jobs. Do not equate agent count with simultaneous training jobs.

## 7. Route worthwhile work to available compute

Each plan item declares:

```text
Resource: CPU | GPU | EITHER
Parallel: YES | NO
Other: NONE | <external executor>
```

Example: `Other: Kaggle`.

Dispatch rules:

1. If GPU has headroom, run the highest-priority compatible `GPU` or `EITHER` item.
2. If CPU has headroom, run the highest-priority compatible `CPU` or `EITHER` item.
3. If one local resource is busy and the other is idle, fill the idle resource with the best compatible independent item.
4. If local CPU and GPU are saturated, an item with an available `Other` executor may overflow remotely when the workflow, credentials, quotas, and user authorization permit it.
5. Keep blocked, non-parallel-safe, secret-dependent, or local-artifact-dependent work queued locally.

Do not launch low-value experiments merely to keep hardware busy. Priority decides **what** is worth running; resource routing decides **where** it runs.

## 8. Use `handoff.md` as the operational ledger

Keep unfinished resumable detail inside the current agent's active handoff section:

```markdown
### Agent: A
- Current host: Codex
- Current thread: H-A-03
- Resumable state: ...
- Blocker: none
- Next action: ...
```

Put completed work and review events in the shared log, append-only.

Use this event shape:

```markdown
### YYYY-MM-DD HH:MM — Main — H-Main-01
- Host: Claude Code | Codex | Antigravity | <other>
- Action: ...
- Result: ...
- Evidence: ...
- Discovery updates: D-Main-014 / none
- Review verdict: <discovery ID> CLOSED | HOLD | CHALLENGED / none
- Files/metrics: ...
- Resource: CPU | GPU | Other | none
- Other executor: Kaggle / none
- New plan items: H-Main-02, H-Main-03 / none
- Next resumable action: ...
```

Do not copy detailed active hypotheses from `plan.md` into handoff text.

When `handoff.md` becomes hard to scan, move older completed log entries to `docs/<focused-name>.md` (for example `docs/handoff-2026-10.md`) and leave a short summary/link. Keep shared state, active handoffs, and recent events in the root handoff file.

## 9. Shared-file editing safety

Before changing `plan.md`, `discoveries.md`, or `handoff.md`:

1. Re-read the latest file.
2. Patch only the relevant section or append the new entry.
3. Never overwrite the whole shared file from a stale copy.

This is mandatory when multiple sessions may edit the repository concurrently.

## 10. Close a session

Before ending meaningful work:

1. Finish any completed plan-item migration: handoff → discovery (always for a failed hypothesis, otherwise when useful) → follow-up plan items → remove the completed item.
2. Rescore the remaining items in your own plan section.
3. Finish or release any cross-check you claimed (`REVIEWING` → verdict, or back to `PENDING`).
4. Update your active handoff section with the exact next resumable action.
5. Set `Current host: released` so the slot is visibly free for the next session.

## 11. Initialize a project

Run:

```bash
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name"
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --agents 2
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --agents Main,A,B
```

`--agents` takes either a count (`2` → `Main, A`) or a comma-separated list of allowed names. The initializer rejects duplicate or non-standard names, creates missing files only, and never overwrites existing project files. To add an agent to an existing project, add its `## Agent: <name>` plan section, its `### Agent: <name>` handoff section, and its name under `Active agent(s)`.
