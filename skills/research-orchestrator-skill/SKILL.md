---
name: research-orchestrator-skill
description: "Orchestrate hypothesis-driven research across one or many agent sessions using a scored PLAN queue, shared DISCOVERIES with independent per-agent review verdicts, adaptive workers, CPU/GPU/Other resource routing, and a durable HANDOFF log. Use when starting or resuming research, coordinating parallel experiments, prioritizing hypotheses, reviewing another agent's conclusions, scaling work to available compute, or preserving project continuity across sessions."
---

# Research Orchestrator

Use exactly four project-level coordination files:

```text
agents.md        # stable operating rules
plan.md          # active unfinished work only, separated by agent
discoveries.md   # shared reusable findings and per-agent review verdicts
handoff.md       # operational history and resumable state
```

Do not create per-agent continuity folders, mode files, or a separate process file. Create `docs/` only when older handoff history becomes too large to scan comfortably.

## 1. Identify the current agent

Use a stable agent name such as `Main`, `A`, `B`, or a role name.

- Continue the same thread with the same agent name.
- Use different names for concurrent independent sessions.
- Add workers only when independent useful work exists.
- Single-agent and multi-agent work use the same files and rules.

## 2. Read in this order

1. Read `agents.md`.
2. Read all of `discoveries.md`.
3. Read the shared completed/review log in `handoff.md` plus only the current agent's active handoff section.
4. Read only the current agent's detailed section in `plan.md`.

A resource dispatcher may inspect only task metadata across agent sections: task ID, owner, priority, resource, parallel-safety, and `Other` executor. Do not read another active agent's detailed hypothesis merely for coordination.

## 3. Keep `plan.md` as a scored live queue

Store only active unfinished hypotheses, experiments, reviews, or next actions.

Use this exact item shape:

```markdown
### H-A01 — Short title
- Sources: D-003, D-008 / none
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

A single discovery may generate many plan items. One plan item may combine many discoveries.

### Priority scoring

Score each factor from 0 to 3:

- `Impact`: expected value if successful.
- `Information`: uncertainty resolved or future decisions changed.
- `Confidence`: strength of evidence that the direction is worth testing.
- `Unblock`: how much it removes a dependency or bottleneck.
- `Diversity`: how different it is from already explored paths.
- `Cost`: time/compute/risk, where 0 is cheap and 3 is expensive.

Calculate:

```text
Priority = 2*Impact + 2*Information + Confidence + Unblock + Diversity + (3-Cost)
```

Work highest score first unless blocked or explicitly overridden. Break ties by lower `Cost`, then higher `Information`.

Whenever a new discovery or review verdict changes the evidence, rescore affected active items.

## 4. Remove completed work from `plan.md`

When a plan item finishes:

1. Append the action and outcome to `handoff.md`.
2. Add or update reusable knowledge in `discoveries.md` when useful.
3. Add any follow-up hypotheses to `plan.md` with fresh scores.
4. Remove the completed item from `plan.md`.

Do not accumulate `[done]` items in `plan.md`. A failed or disproved hypothesis is still completed work and must leave the live queue.

## 5. Use `discoveries.md` as shared knowledge with independent verdicts

Every agent reads the whole file. A discovery has no single global final state. Each agent records its own judgment.

Use this exact shape:

```markdown
## D-014 — Short title
- Source: Agent A
- Finding: ...
- Evidence: ...
- Implication: ...
- Reviews:
  - Agent A: CLOSED — source experiment supports the finding
  - Agent B: HOLD — promising, but needs stronger evidence on ...
  - Agent C: CHALLENGED — contradiction found in ...
```

Per-agent verdicts:

- `CLOSED`: this agent currently accepts the finding after meaningful review.
- `HOLD`: this agent sees plausible value but does not yet accept or reject it. State what evidence, condition, or improvement would justify revisiting it.
- `CHALLENGED`: this agent found a material contradiction, flaw, or missing assumption.
- no entry: this agent has not reviewed the discovery.

Rules:

- A source agent may record its own `CLOSED`, but that is only that agent's verdict.
- Another agent never inherits someone else's `CLOSED`; when the finding matters, review or reproduce it and write its own verdict.
- `HOLD` preserves promising but incomplete ideas without polluting the active plan.
- If later evidence changes an agent's view, replace that agent's verdict and explain why.
- Do not require every agent to review every discovery; review high-impact premises and discoveries used to justify new plan items.

### Move a discovery back into the plan

When a `CLOSED`, `HOLD`, or `CHALLENGED` discovery suggests new work, create zero, one, or many new plan items as warranted.

Every plan item derived from discoveries must include:

- `Sources`: the discovery IDs.
- `Evidence`: the concrete evidence that makes the new hypothesis worth testing.
- `Improvement`: the missing proof, changed condition, stronger method, or specific weakness the new test will address.

Do not write only `Source: D-014` and repeat the same experiment. Explain why the new attempt is materially better or different.

## 6. Scale workers from 2 to practical full load

When parallel work is useful, start with two independent workers. Add more only while all are true:

- independent high-value plan items remain;
- CPU, GPU, RAM, disk I/O, and remote quotas have headroom;
- added workers do not materially reduce throughput;
- workers are not duplicating work unless deliberate replication is the goal.

There is no fixed maximum. Practical full load is the highest useful concurrency the current machine and available remote compute can sustain without harmful contention.

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

Keep unfinished resumable detail inside the current agent's active handoff section. Put completed work and review events in the shared log.

Use this event shape:

```markdown
### YYYY-MM-DD HH:MM — Agent A — H-A01
- Action: ...
- Result: ...
- Evidence: ...
- Discovery updates: D-014 / none
- Review verdict: A:CLOSED | A:HOLD | A:CHALLENGED | none
- Files/metrics: ...
- Resource: CPU | GPU | Other | none
- Other executor: Kaggle / none
- New plan items: H-A02, H-A03 / none
- Next resumable action: ...
```

When `handoff.md` becomes hard to scan, move older completed log entries to `docs/<focused-name>.md` and leave a short summary/link. Keep shared state, active handoffs, and recent events in the root handoff file.

## 9. Shared-file editing safety

Before changing `plan.md`, `discoveries.md`, or `handoff.md`:

1. Re-read the latest file.
2. Patch only the relevant section or append the new entry.
3. Never overwrite the whole shared file from a stale copy.

This is mandatory when multiple sessions may edit the repository concurrently.

## 10. Initialize a project

Run:

```bash
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name"
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --agents A,B
```

The initializer creates missing files only and never overwrites existing project files.
