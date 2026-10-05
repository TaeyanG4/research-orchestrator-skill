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
handoff.md       # event log (who, when, which host, artifacts) and each slot's resume point
```

Do not create per-agent continuity folders, mode files, or a separate process file. Create `docs/` only when older handoff history becomes too large to scan comfortably.

## 1. Identify the current agent

An agent name is a **work slot**, not the identity of the tool or model running it. The same slot can be continued by Claude Code, Codex, Antigravity, or any other host.

Allowed names, assigned in this order:

```text
A, B, C, ... Z, AA, AB, ... ZZ
```

- `A` is the first slot. Single-agent work always uses `A`.
- Each additional concurrent session takes the next unused letter: the second is `B`, the third is `C`, and so on. After `Z` come two-letter names in spreadsheet-column order (`AA`, `AB`, ...). Slots are reused once released, so new letters are needed only when every existing slot is taken at the same time.
- Never use a host, product, or model name (`Claude`, `Codex`, `GPT`, `Gemini`, `Antigravity`, `Opus`, `Sonnet`, ...) or a free-form role name as an agent name.
- A **host** is the platform the session runs on (`Claude Code`, `Codex`, `Antigravity`, ...), not the model. Two Claude Code sessions running different models are the same host.
- Track hosts in fields, never in the name:
  - `Current host` in the agent's active handoff section (`handoff.md`) says which host owns the slot right now. Set it whenever a session takes or resumes the slot.
  - `Host` in each completed-log event (`handoff.md`) says which host did that step.
  - `Host` in each discovery (`discoveries.md`) says which host made it; a different host cross-checks it (section 5).
- Continue the same thread with the same agent name, even when a different host resumes it; only `Current host` changes.
- A slot is **free** when its `Current host` is `unassigned` or `released`, and **taken** otherwise. Liveness is never guessed; it is read from that line.
- If the user assigns a name, use it. Otherwise read only the `Current host` line of each agent section in `handoff.md` and take the first free slot in order (`A`, `B`, `C`, ...). Skip a free slot that still holds plan items left by a different host — those stay with that host (section 4) unless the user assigns you the slot. If none is free, create the next unused letter: add its `## Agent:` plan section, its `### Agent:` handoff section, and its name under `Active agent(s)`.
- When you take or resume a slot, set `Current host: <your host>` first. When you close the session, set `Current host: released` (section 10). A slot left taken by a crashed session may be reclaimed only when the user says so.
- Add agents only when independent useful work exists.

Every ID embeds the owning agent name so concurrent agents never collide:

| Object | Format | Examples |
| --- | --- | --- |
| Plan item | `H-<Agent>-<NN>` | `H-A-01`, `H-B-07` |
| Discovery | `D-<Agent>-<NNN>` | `D-A-001`, `D-C-014` |
| Plan / handoff section | `Agent: <Agent>` | `## Agent: A` |
| Discovery review | `<Host> (<Agent>): <VERDICT>` | `Claude Code (A): CLOSED` |

Each agent numbers only its own IDs, sequentially, and never reuses a number.

## 2. Read in this order

1. Read `agents.md`.
2. Read all of `discoveries.md`.
3. Read the shared state and completed/review log in `handoff.md` plus only the current agent's active handoff section.
4. Read only the current agent's detailed section in `plan.md`.
5. Run the consistency check (section 9) before starting work.

Four narrow exceptions allow looking across other agents' sections:

- A resource dispatcher, or a session choosing a take-over item, may inspect only task metadata: task ID, owner, priority, cost, information, resource, parallel-safety, and `Other` executor.
- Before adding a plan item, any agent may scan only item headings and `Hypothesis` lines to avoid queueing a duplicate (section 3).
- When choosing a slot or a take-over source, a session may read only the `Current host` and `Current thread` lines of each agent's handoff section (sections 1 and 4).
- When taking over an item (same host, or cross-host by judgment), a session reads that one item in full once it has chosen it by metadata (section 4).

Do not read another active agent's detailed evidence, scores, next tests, or resumable state merely for coordination.

## 3. Keep `plan.md` as a scored live queue

Store only active unfinished hypotheses, experiments, reviews, or next actions — plan items and nothing else; project-wide values such as the current best belong in `handoff.md` Shared state (section 9). Each agent edits only its own section, except when taking over an item from a same-host slot (section 4) or when explicitly asked otherwise.

Use this exact item shape:

```markdown
### H-A-01 — Short title
- Sources: D-B-003, D-A-008 / none
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

1. **Search `discoveries.md`** for the same claim. Every completed experiment leaves a discovery (section 4), so this one search covers everything already tried — positive, negative (`Finding: ... does not hold`), and inconclusive (`Finding: inconclusive — ...`).
   - `VERIFIED` and the claim is the same → do not add it. Add only a materially different follow-up with `Improvement`.
   - `CHALLENGED` → do not add it until the challenge is resolved.
   - `HOLD` → add it only when the stated condition is now met, and say so in `Evidence`.
   - `PENDING` / `REVIEWING` → prefer cross-checking it (if you are on a different host) over re-running it.
   - Negative or inconclusive → add it only with an `Improvement` that addresses why it failed or did not settle.
2. **Scan the other agents' plan sections for the same hypothesis**, reading only each item's heading (`### H-X-NN — title`) and `Hypothesis` line, nothing else. If another agent already has it queued, do not add it. If yours is materially different, add it and cite the other item ID in `Evidence`.
3. **Re-read `plan.md`** immediately before writing (section 9); if the same item appeared meanwhile, keep the earlier one.

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

## 4. Finish an item, plan what follows, and keep going

When a plan item finishes:

1. Record the result in `discoveries.md` — **always**, whatever the outcome. Every completed experiment or test creates or updates exactly one discovery:
   - positive: `Finding: <claim>`
   - negative: `Finding: <claim> does not hold under <conditions>`
   - inconclusive: `Finding: inconclusive — <what was tried and why it did not settle>`
   A cross-check updates the reviewed discovery instead of creating a new one.
2. Append a handoff event that points to that discovery (section 8).
3. Plan the follow-ups from that discovery (below).
4. Remove the completed item from `plan.md`.

Do not accumulate `[done]` items in `plan.md`. A failed or disproved hypothesis is still completed work and must leave the live queue. Because `discoveries.md` is the one file every agent reads in full, it is the **only** index of what has been tried and learned: an experiment that leaves no discovery will eventually be proposed again. Only steps that are not experiments — taking over an item, changing resource routing, closing a session — leave no discovery.

### Plan follow-ups from every discovery (zero or more)

Every time you write or update a discovery — a new finding, a negative result, or a cross-check verdict — decide explicitly what it changes before picking your next item:

1. **What next test could change a decision now?** Write each one as a new plan item in your own section, with `Sources` (the discovery), `Evidence` (the concrete numbers or observations), and `Improvement` (what this test does that earlier ones did not). Each must pass the duplicate check (section 3).
2. **Which of your existing items does it affect?** Rescore them; remove items it made pointless and name each one in the handoff event's `Action` as `removed H-A-05 — <reason>`.
3. **Zero follow-ups is a valid answer**, but it must be deliberate. Record it as `New plan items: none — <reason>` in the handoff event (for example `none — result closes this direction` or `none — H-B-02 already covers it`).

One discovery may yield many items, and one item may combine several discoveries. Prefer the few items that would change a decision over many small variations.

### When your own queue runs out

Before going idle, look for work in this order:

1. **Your own section** — re-read it first; a same-host session may have taken items from it (the handoff log says so).
2. **Cross-checks** — claim a `PENDING` discovery from a different host (section 5).
3. **Take over from a same-host slot** — see below.
4. **Cross-host take-over by judgment** — only one promising item, under the conditions below.
5. **New hypotheses** — derive zero or more items from discoveries (section 3 checks apply).
6. **Nothing worthwhile left** — record this in your active handoff section, set `Current host: released`, and stop. Do not invent low-value work to stay busy.

#### Take over an item from a same-host slot

When your own queue is empty, you may take over a queued item from another slot **on the same host**, even if that session runs a different model. Items queued under a different host stay with that host, so each host's line of reasoning stays independent.

Eligible sources:

- a slot whose `Current host` equals your host (an active same-host session), or
- a `released` or `unassigned` slot whose most recent completed-log event was made by your host, or that has no completed-log events at all (items seeded by the user carry no host history, so any host may take them).

Items left by a different host in a released slot normally stay with that host. They can move only through a cross-host take-over by judgment (below), or when the user says so.

Never take the item named in the owner's `Current thread`; that one is in progress.

Steps:

1. Choose by metadata only: the highest-`Priority` eligible item (ties by lower `Cost`, then higher `Information`) whose `Resource` you can run now.
2. Re-read `plan.md` immediately before moving it. If the item is gone, another session took it; choose again.
3. **Move it into your own section with your own ID**: cut the block from the source section, give it your next number (`H-C-03` becomes, for example, `H-A-05`), and append the old ID to the title — `### H-A-05 — Fold-aware target encoding (from H-C-03)`. The old ID is retired and never reused.
4. Rescore it against the current discoveries; it is your item now.
5. Append a handoff event: `Action: took over H-C-03 from C (same host) as H-A-05`, with `Discovery updates: none — take-over, no experiment`.

The original owner, on its next re-read of its own section, finds the item gone and the reason in the handoff log.

#### Cross-host take-over by judgment

By default a different host's items stay with that host, so each host keeps an independent line of reasoning. As an exception, you may take over **one** item queued by a different host when your judgment is that it is clearly worth running now. All of these must hold:

1. **Nothing closer is left**: your own queue, eligible cross-checks, and same-host items are exhausted (steps 1–3 above).
2. **The source slot is idle**: it is `released` or `unassigned`. Never take from a slot whose `Current host` is an active session on another host, and never the owner's `Current thread`.
3. **The item is promising**: its `Priority` is at least 15 (out of 24), and it clearly beats the best new hypothesis you could write now. You can state in one line why it is likely to change a decision now — for example, it is a cheap diagnostic that decides whether the remaining items are worth running.
4. **One item at a time**: take one, finish it, then start this list again from step 1. The source host's other items stay where they are.

Move it exactly as in a same-host take-over, and record the judgment in the event:

```text
Action: took over H-C-01 from C (cross-host: Codex → Claude Code; reason: cheap error audit decides whether C's model items are worth running) as H-A-12
```

The user can lower or raise the Priority floor, forbid cross-host take-overs, or approve specific items; an explicit user instruction always wins. The discovery that results records your host in `Host` as usual, so a session on the original host can still cross-check it.

## 5. Use `discoveries.md` as shared knowledge with cross-host verification

Every agent reads the whole file. Verification is per **host**, not per agent: a discovery made on one host is checked **once** by a different host. Sessions on the same host share the same blind spots, so they do not re-review each other, and ten sessions never have to review the same finding ten times.

Use this exact shape:

```markdown
## D-B-014 — Short title
- Source: B
- Host: Codex
- Cross-check: VERIFIED
- Finding: ...
- Evidence: ...
- Implication: ...
- Reviews:
  - Claude Code (A): CLOSED — reproduced independently with ...
```

`Cross-check` is the discovery's verification state:

- `PENDING`: no different host has reviewed it yet. New discoveries start here.
- `REVIEWING <Host> (<Agent>)`: a different-host session has claimed the review, for example `REVIEWING Claude Code (A)`.
- `VERIFIED`: a different host reviewed it and recorded `CLOSED`.
- `HOLD`: a different host found it plausible but needs specific evidence, a condition change, or an improvement first.
- `CHALLENGED`: a host found a material contradiction, flaw, or missing assumption.

Review lines use `<Host> (<Agent>): <VERDICT> — reason`, where the verdict is `CLOSED`, `HOLD`, or `CHALLENGED`. `Cross-check` mirrors the latest cross-host verdict (`CLOSED` → `VERIFIED`), except that any standing `CHALLENGED` wins until it is resolved.

Rules:

- The source does not review its own discovery; the discovery is its claim.
- Review only discoveries whose `Host` differs from yours and whose `Cross-check` is `PENDING`, or `HOLD` when its stated condition is now met.
- Claim a review by setting `Cross-check: REVIEWING <your host> (<your agent>)` before starting, so two sessions do not review the same discovery. Take over a claim only when the claiming agent's `Current host` reads `released` or `unassigned` (lines you may read, section 2), or the user says so.
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

Do not write only `Sources: D-B-014` and repeat the same experiment. Explain why the new attempt is materially better or different. Do not edit another agent's active plan merely because its discovery suggested a direction.

## 6. Scale workers from 2 to practical full load

When parallel work is useful, start with two independent agents (`A` and `B`). Add more only while all are true:

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

## 8. Use `handoff.md` as the event log and resume point

`discoveries.md` holds **what is known**; `handoff.md` holds **what happened and where to resume**. Each fact has one home, and the other files point to it instead of repeating it:

| Information | Home | Elsewhere |
| --- | --- | --- |
| Claim, numbers, interpretation | `discoveries.md` (`Finding`, `Evidence`, `Implication`) | handoff `Result` points to the discovery ID |
| Verification state and reasons | `discoveries.md` (`Cross-check`, `Reviews`) | handoff `Review verdict` names the ID and verdict only |
| Who, when, which host, what was done | `handoff.md` event | — |
| Files produced or changed | `handoff.md` `Artifacts` (paths only) | discovery `Evidence` cites the files that reproduce the claim |
| What to test next | `plan.md` (`Next test`) | handoff names the plan item ID |
| Where a slot stands right now | `handoff.md` active section | — |

Keep each slot's resume point in its active handoff section:

```markdown
### Agent: B
- Current host: Codex
- Current thread: H-B-03
- Resumable state: ...
- Blocker: none
- Next action: ...
```

- `Resumable state` is the half-done work that exists nowhere else: a drafted script, a running job, a partial output.
- `Next action` names plan item IDs (`H-B-03, then H-B-02`) or a step that is not a plan item (recording a verdict). It does not restate a plan item's `Next test`.
- This section is the only place for "what next"; events do not carry their own next-step line.

Put completed work and review events in the shared log, append-only. Use this event shape:

```markdown
### YYYY-MM-DD HH:MM — A — H-A-01
- Host: Claude Code | Codex | Antigravity | <other>
- Action: ...
- Result: <one line>; see <discovery ID>
- Artifacts: <paths> / none
- Discovery updates: D-A-014 / none — <reason>
- Review verdict: <discovery ID> CLOSED | HOLD | CHALLENGED / none
- Resource: CPU | GPU | Other | none
- Other executor: Kaggle / none
- New plan items: H-A-02, H-A-03 / none — <reason>
```

- The heading's last part is the plan item the event **completed**. Write `none` there for a step that completes nothing (a routing change, a session close) and the new ID for a take-over.
- `Result` is one line. For an experiment it points to the discovery (`see D-A-001`) instead of restating its numbers.
- `Artifacts` lists paths only — scripts, outputs, logs. Metrics and their meaning go in the discovery.
- `Discovery updates` and `New plan items` are never a bare `none`; each carries a reason. `Discovery updates: none` is allowed only for steps that are not experiments (section 4), for example `none — take-over, no experiment`.

Do not copy detailed active hypotheses from `plan.md` into handoff text.

When `handoff.md` becomes hard to scan, move older completed log entries to `docs/<focused-name>.md` (for example `docs/handoff-2026-10.md`) and leave a short summary/link. Keep shared state, active handoffs, and recent events in the root handoff file.

## 9. Keep the four files consistent

### Shared-file editing safety

Before changing `plan.md`, `discoveries.md`, or `handoff.md`:

1. Re-read the latest file.
2. Patch only the relevant section or append the new entry.
3. Never overwrite the whole shared file from a stale copy.

This is mandatory when multiple sessions may edit the repository concurrently.

### Change linked files in the same step

Some changes touch more than one file. Make all parts of the change before doing anything else, so no file ever describes a state the others do not:

| Change | Do all of these together |
| --- | --- |
| Finish an item | discovery → handoff event → follow-up items → remove the item from `plan.md` |
| Take over an item (same host or cross-host) | move the block in `plan.md` → handoff event, with the reason for a cross-host take-over |
| Add or create a slot | `## Agent:` plan section + `### Agent:` handoff section + `Active agent(s)` |
| New best result | discovery whose `Implication` starts with `new current best:` → `Current best` in Shared state citing it |
| Queue an item | add it to `plan.md`; any handoff line that names it comes after, never before |

### Project-wide values live only in Shared state

Values that describe the whole project — the current best model or "champion", the baseline metric, the validation scheme in use — live only in the `## Shared state` block of `handoff.md`. `plan.md` holds plan items and nothing else: no champion lines, status headers, or notes outside item blocks.

`Current best` always cites the discovery that established it, for example `- Current best: fold-aware TE, GroupKFold CV 0.9112 (D-A-005)`. When a result beats it, the new discovery's `Implication` starts with `new current best:` and `Current best` is updated in the same step. A `Current best` that does not cite the latest such discovery is stale.

### Run the consistency check

Run the bundled checker at session start, after a take-over, and before closing:

```bash
python <skill-root>/scripts/check_project.py .
```

It reports, among other things:

- an agent listed in `Active agent(s)` without a matching plan or handoff section, or the reverse;
- a plan item that handoff names as current, next, or newly queued but that is missing from `plan.md` and was never completed or taken over;
- a finished item still in `plan.md`, a retired `(from H-…)` ID still present, or duplicate IDs;
- a referenced discovery that does not exist;
- shared-state lines in `plan.md`, or a `Current best` that is missing its citation or is stale;
- `Cross-check` states that do not match their review lines, and claims held by a released slot.

Fix what you own: your own sections, structure (a missing empty section for a listed agent), and Shared state values with a cited discovery. Never invent or delete another agent's items. For a problem in another agent's section, add a line under `Open consistency issues` in Shared state (`- H-B-01 named as queued for B but missing from plan.md (found by A)`); the owner, or the user, resolves it and removes the line. Do not start new work while the checker reports a problem in your own sections. If a report is wrong, record it under `Open consistency issues` with `(disputed — <why>)` and continue; the user settles it.

## 10. Close a session

Before ending meaningful work:

1. Finish any completed plan-item migration: discovery (always) → handoff event → follow-up plan items → remove the completed item.
2. Rescore the remaining items in your own plan section.
3. Finish or release any cross-check you claimed (`REVIEWING` → verdict, or back to `PENDING`).
4. Update your active handoff section: `Resumable state` and `Next action`.
5. Run the consistency check and fix your own problems.
6. Set `Current host: released` so the slot is visibly free for the next session.

## 11. Initialize a project

Run:

```bash
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name"
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --agents 2
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --agents A,B,C
```

`--agents` takes either a count (`2` → `A, B`) or a comma-separated list of allowed names. The initializer rejects duplicate or non-standard names, creates missing files only, and never overwrites existing project files. To add an agent to an existing project, add its `## Agent: <name>` plan section, its `### Agent: <name>` handoff section, and its name under `Active agent(s)`.
