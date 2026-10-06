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

## 0. Before you start: ask, then set up

### A new project (no `agents.md` yet)

Ask the user these six questions before creating any file, unless the request already answers them. Ask them together, in one message, and offer the defaults so the user can simply accept them:

1. **Your name** — the name recorded for you in the files, so several people can work on one project (for example `kim`, `user1`). One word of letters, digits, `-`, or `_`.
2. **Platforms** — which hosts will work on this project, and how:
   - `multi`: several platforms at the same time (for example Claude Code and Codex). Discoveries are cross-checked by a different host; cross-host take-over by judgment is allowed.
   - `single`: one platform only. Cross-checks are done by a different slot on the same host.
   - `adaptive`: it depends on the day. Prefer a different host for cross-checks and fall back to a different slot when no other host is active.
3. **Git sync** — how the four coordination files are shared:
   - `push`: commit and push automatically after each linked change and at session close. Needed when people or sessions work on different machines.
   - `commit`: local commits only, never pushed.
   - `off`: no git; sessions share the files on this machine only.
4. **Plan collector** — run a sub-agent that gathers diverse research candidates into `plan.md`?
   - `off` (default), or a platform and model, for example `Claude Code/sonnet` or `Codex/sol` (models such as `opus`, `sonnet`, `fable`, `astra`, `sol`, `luna`).
   - Queue limits: stop collecting at N plan items and resume at M (default `50,5`).
5. **Reviewer** — hand cross-checks of finished work to a reviewer sub-agent so the main agents keep experimenting? `off` (default), or a platform and model, for example `Codex/sol`.
6. **Cross-check fallback** — when the queue runs out and only cross-checks that need another platform remain: `same-host` (run them with a same-platform model) or `wait` (leave them for the other platform). Default: `wait` for `multi`, `same-host` otherwise.

Then initialize with the answers:

```bash
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --user kim --platform multi --platforms "Claude Code, Codex" --git push --collector "Claude Code/sonnet" --queue-limits 50,5 --reviewer "Codex/sol" --fallback wait
```

The settings are written to `agents.md` under `## Project settings`, and `agents.md` is generated to match them — a `single` project gets no cross-host rules, a `push` project gets the git sync steps. Read it before working.

### An existing project

- Read `## Project settings` in `agents.md`; do not ask the setup questions again.
- Ask only for the user's name, unless they already gave it in this session. If `Users` in `handoff.md` lists exactly one name, you may ask to confirm it instead (`Continue as kim?`).
- If the name is new, add it to `Users` in Shared state.

If `agents.md` has no `## Project settings` block, the project predates this version. Ask the six setup questions as for a new project, then run `init_research_orchestrator.py . --reconfigure --force` with the answers as flags; it regenerates only `agents.md`. Then add the lines the consistency check reports as missing in `handoff.md` (`Users`, `Plan collection`, and `Current user` in each slot) and log the migration as an event with heading `none`. Existing plan items, discoveries, and events stay as they are.

### Changing settings

The settings lines in `agents.md` are meant to be edited, by the user or by you on the user's request:

- `Plan collector`, `Plan queue limits`, `Reviewer`, and `Cross-check fallback` take effect immediately; every session reads them at start.
- `Platform mode`, `Platforms`, and `Git sync` change the generated rules. After editing those lines, regenerate the rules — or pass the new values as flags:

```bash
python <skill-root>/scripts/init_research_orchestrator.py . --reconfigure --platform adaptive --git push
```

`--reconfigure` rewrites only `agents.md`, keeps every setting you do not pass, and refuses when the rules themselves were edited by hand (add `--force` after saving those edits). The consistency check notes rules that no longer match their settings. Log any settings change as a handoff event with heading `none`.

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
- A **user** is the person running the session (`kim`, `user1`); see section 0. Record it as `Current user` next to `Current host` in your active handoff section, and as `User` in every event. Reset `Current user` to `none` when you release the slot. User names are never slot names, host names, or model names.
- Never take over an item from a slot that another user is actively running; a released slot of another user may be a take-over source under the usual rules (section 4).
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
- When choosing a slot or a take-over source, a session may read only the `Current host`, `Current user`, and `Current thread` lines of each agent's handoff section (sections 1 and 4).
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
5. **Cross-check fallback** — if `Cross-check fallback` is `same-host`, review a `PENDING` discovery from your own host (section 5); if it is `wait`, leave those for the other host.
6. **New work** — if `Plan collector` is on and the queue is at or below its resume limit, start a collection round (below); otherwise derive zero or more items from discoveries yourself (section 3 checks apply).
7. **Nothing worthwhile left** — record this in your active handoff section, set `Current host: released`, and stop. Do not invent low-value work to stay busy.

In a `single` project, steps 4 and 5 do not apply.

#### Plan collector

`Plan collector` in `agents.md` is `off` or `on — <platform> / <model>`; `Plan queue limits` reads `stop at <N>, resume at <M>`. When it is on, a sub-agent keeps the queue supplied with diverse research candidates:

1. **When** — at session start and after finishing each item, count plan items across all sections. Start a round when the count is at or below the resume limit and `Plan collection` in Shared state reads `idle`.
2. **Who** — only a session on the collector's platform, because it launches a sub-agent with the collector's model (in Claude Code, the Agent tool with the model set). Other sessions skip collection.
3. **Mark** — set `Plan collection: running — <your agent> (since YYYY-MM-DD HH:MM)` before starting, so no second round starts.
4. **Collect** — give the sub-agent all discoveries, every plan item's heading and `Hypothesis`, the project goal, and any sources the user allows. Accept only candidates that are full plan items with `Sources`, `Evidence`, `Improvement`, and honest scores, and that pass the duplicate check. Prefer diversity.
5. **Add** — put accepted items in your own section under your own IDs until the count reaches the stop limit or no worthwhile candidates remain.
6. **Finish** — set `Plan collection: idle` and log one event with heading `none`: `Action: plan collection round (Claude Code / sonnet): added H-A-12, H-A-13`, with those IDs under `New plan items` and `Discovery updates: none — collection, no experiment`.

Between rounds nothing is collected, so the queue drains to the resume limit before the next round. A `running` marker left by a released slot is stale; clear it and log the cleanup.

#### Take over an item from a same-host slot

When your own queue is empty, you may take over a queued item from another slot **on the same host**, even if that session runs a different model. Items queued under a different host stay with that host, so each host's line of reasoning stays independent.

Eligible sources:

- a slot whose `Current host` equals your host and that your own user is running (an active same-host session of yours), or
- a `released` or `unassigned` slot whose most recent completed-log event was made by your host, or that has no completed-log events at all (items seeded by the user carry no host history, so any host may take them).

Items left by a different host in a released slot normally stay with that host. They can move only through a cross-host take-over by judgment (below), or when the user says so.

Never take the item named in the owner's `Current thread`, nor one that holds an `Active compute` claim; those are in progress even when the owner is doing something else while a job runs.

Steps:

1. Choose by metadata only: the highest-`Priority` eligible item (ties by lower `Cost`, then higher `Information`) whose `Resource` you can run now.
2. Re-read `plan.md` immediately before moving it. If the item is gone, another session took it; choose again.
3. **Move it into your own section with your own ID**: cut the block from the source section, give it your next number (`H-C-03` becomes, for example, `H-A-05`), and append the old ID to the title — `### H-A-05 — Fold-aware target encoding (from H-C-03)`. The old ID is retired and never reused.
4. Rescore it against the current discoveries; it is your item now.
5. Append a handoff event: `Action: took over H-C-03 from C (same host) as H-A-05`, with `Discovery updates: none — take-over, no experiment`.

The original owner, on its next re-read of its own section, finds the item gone and the reason in the handoff log.

#### Cross-host take-over by judgment

This applies only when `Platform mode` is `multi` or `adaptive`; a `single` project has one host. By default a different host's items stay with that host, so each host keeps an independent line of reasoning. As an exception, you may take over **one** item queued by a different host when your judgment is that it is clearly worth running now. All of these must hold:

1. **Nothing closer is left**: your own queue, eligible cross-checks, and same-host items are exhausted (steps 1–3 above).
2. **The source slot is idle**: it is `released` or `unassigned`. Never take from a slot whose `Current host` is an active session on another host, and never an item in the owner's `Current thread` or under an `Active compute` claim.
3. **The item is promising**: its `Priority` is at least 15 (out of 24), and it clearly beats the best new hypothesis you could write now. You can state in one line why it is likely to change a decision now — for example, it is a cheap diagnostic that decides whether the remaining items are worth running.
4. **One item at a time**: take one, finish it, then start this list again from step 1. The source host's other items stay where they are.

Move it exactly as in a same-host take-over, and record the judgment in the event:

```text
Action: took over H-C-01 from C (cross-host: Codex → Claude Code; reason: cheap error audit decides whether C's model items are worth running) as H-A-12
```

The user can lower or raise the Priority floor, forbid cross-host take-overs, or approve specific items; an explicit user instruction always wins. The discovery that results records your host in `Host` as usual, so a session on the original host can still cross-check it.

## 5. Use `discoveries.md` as shared knowledge with cross-host verification

Every agent reads the whole file. Verification is per **host**, not per agent: a discovery made on one host is checked **once** by a different host. Sessions on the same host share the same blind spots, so they do not re-review each other, and ten sessions never have to review the same finding ten times.

The reason is sycophancy: a model tends to agree with whoever it is talking to — the user's framing, or the claim it is asked to confirm. A session on a different host shares neither the conversation nor the blind spots of the session that made the discovery, so its verdict is a second opinion rather than an echo. When you review, judge the evidence as if the claim were wrong until it proves otherwise; do not start from the source's conclusion.

How this applies depends on `Platform mode` in `agents.md` (section 0):

- `multi`: always a different host.
- `single`: there is only one host, so a different **slot** reviews, and every review reason starts with `same host —`. Cross-host take-over does not apply.
- `adaptive`: a different host whenever one is available; otherwise `Cross-check fallback` decides.

Two more settings shape cross-checks:

- **Reviewer** (`off` or `on — <platform> / <model>`). When on, a session on the reviewer's platform hands each eligible `PENDING` discovery to a reviewer sub-agent with that model, so the main agents keep experimenting. The session still claims the review under its own slot and writes the line under its own host and slot, naming the model first in the reason: `Codex (B): CLOSED — reviewer sol — reproduced with ...`. All eligibility rules below still apply.
- **Cross-check fallback** (`wait` or `same-host`). When a discovery needs a different host and none is active: `wait` leaves it `PENDING` for that host; `same-host` lets a session on the same host review it once its own queue runs out — with a different model when possible — starting the reason with `same host —`. A session on another host may add a second review later.

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

This is a relay of hypotheses, not only of code. When another host's discovery (its hypothesis H1) reaches you, build your own hypothesis H2 on top of it rather than beside it: the pair (H1, H2) is a line of reasoning neither host would have produced alone, and it often yields a third hypothesis that neither would have proposed. Cite both discoveries in `Sources`, and when you take over an item keep the chain visible with `(from H-…)` in the title.

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

### Claim compute before you launch

`Active compute` in `handoff.md` Shared state is the list of claims on heavy compute. Each claim names the resource, the agent, the plan item, and the start time; claims are separated by `; `:

```text
- Active compute: GPU — A (H-A-04, since 2026-10-05 18:20); CPU — B (H-B-03, since 2026-10-05 18:05)
```

Use `none` when nothing heavy is running. The resource is `CPU`, `GPU`, or `Other` (a remote executor such as Kaggle). When sessions run on more than one machine — several users, or `Git sync: push` across computers — add the machine to the resource: `GPU@kim-desktop — A (H-A-04, since 2026-10-05 18:20)`. Only claims on your own machine block you. Work that needs no heavy compute — reading, reviewing, writing code, small smoke tests — needs no claim.

1. Before launching, re-read `handoff.md` and check **both** the claims and the real usage on the machine (for example `nvidia-smi` for GPU memory and load, the task manager or `top` for CPU and RAM). Two sessions can both see an idle GPU; the claim is what stops them from launching together.
2. Add your claim and launch in the same step.
3. Remove your claim in the same step that records the job's end — finished, failed, or killed.

### When the resource you need is busy

Do not launch alongside a job that already holds the resource, unless your item is `Parallel: YES` **and** the measured free memory and load clearly fit it; in that case add your own claim next to the existing one. Otherwise wait, and while waiting do the most valuable work that does not need that resource, in this order:

1. **Run on another resource**: your highest-priority item that fits an idle resource (an `EITHER` item on the free device, or an `Other` executor when permitted).
2. **Work that needs no heavy compute**: claim a cross-check from a different host; prepare the waiting experiment (write the script, test it on a tiny sample); analyse recent results and plan follow-ups; rescore your queue; run the consistency check.
3. **Nothing useful left**: set `Blocker: waiting for GPU (held by A for H-A-04 since 18:20)` in your active handoff section and check again at an interval that matches the running job's expected length — not in a tight loop.

When the resource frees, clear your `Blocker`, add your claim, and launch.

### Stale claims

A claim is stale when its agent's slot is `released` or `unassigned`, when its item is no longer in `plan.md`, or when the job is verifiably not running. Remove your own stale claims at once. A stale claim held by a released slot may be removed by anyone; log it in your next event (`Action: cleared stale GPU claim of C for H-C-02`). If the claiming agent is still active, do not remove its claim — add it to `Open consistency issues` instead.

Do not release your slot while a job you launched is still running: keep `Current host`, describe the job in `Resumable state`, and keep the claim.

## 8. Use `handoff.md` as the event log and resume point

`discoveries.md` holds **what is known**; `handoff.md` holds **what happened and where to resume**. Each fact has one home, and the other files point to it instead of repeating it:

| Information | Home | Elsewhere |
| --- | --- | --- |
| Claim, numbers, interpretation | `discoveries.md` (`Finding`, `Evidence`, `Implication`) | handoff `Result` points to the discovery ID |
| Verification state and reasons | `discoveries.md` (`Cross-check`, `Reviews`) | handoff `Review verdict` names the ID and verdict only |
| Who, when, which host and user, what was done | `handoff.md` event | — |
| Files produced or changed | `handoff.md` `Artifacts` (paths only) | discovery `Evidence` cites the files that reproduce the claim |
| What to test next | `plan.md` (`Next test`) | handoff names the plan item ID |
| Where a slot stands right now | `handoff.md` active section | — |

Keep each slot's resume point in its active handoff section:

```markdown
### Agent: B
- Current host: Codex
- Current user: lee
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
- User: <user name>
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

### Sync through git

Follow `Git sync` in `agents.md` (section 0):

- `off` — do not run git for the coordination files. Sessions share state only through the files on this machine.
- `commit` — right after each linked change (the table below) and at session close, commit the coordination files you changed: `git add` only the changed files among `agents.md`, `plan.md`, `discoveries.md`, `handoff.md`, and `docs/`, then `git commit -m "ro(<agent>/<user>): <short action>"`. Never push.
- `push` — as `commit`, and also:
  1. run `git pull --rebase` before editing a shared file and before launching a heavy job, so you see the latest items, claims, and slots;
  2. push right after each commit;
  3. if the push is rejected, `git pull --rebase`, keep both sides of any conflict in the coordination files (never drop another agent's lines), and push again; if a conflict touches anything else, stop and ask the user.

In `commit` and `push` mode the project must already be a git repository (with a remote, for `push`). If it is not, never run `git init` or add a remote yourself: switch `Git sync` to `off` (edit the line in `agents.md` and run `--reconfigure`, which does this automatically), log the change as an event with heading `none`, and report it to the user so they can set up the repository and turn sync back on. In every mode: never force-push or rewrite history; commit only the coordination files unless the user asks to include code or results; never commit secrets, credentials, or large data. Several users on different machines need `push`; without it they cannot see each other's slots, items, or compute claims.

### Change linked files in the same step

Some changes touch more than one file. Make all parts of the change before doing anything else, so no file ever describes a state the others do not:

| Change | Do all of these together |
| --- | --- |
| Finish an item | discovery → handoff event → follow-up items → remove the item from `plan.md` |
| Take over an item (same host or cross-host) | move the block in `plan.md` → handoff event, with the reason for a cross-host take-over |
| Add or create a slot | `## Agent:` plan section + `### Agent:` handoff section + `Active agent(s)` |
| A new user's first session | add the name to `Users` in Shared state |
| New best result | discovery whose `Implication` starts with `new current best:` → `Current best` in Shared state citing it |
| Launch a heavy job | claim in `Active compute` → launch |
| Plan collection round | `Plan collection: running — …` → add items → `Plan collection: idle` → handoff event |
| Heavy job ends | record the result (or the failure) → remove the claim from `Active compute` |
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
- `Active compute` claims in the wrong format, held by a released slot, or for an item no longer in `plan.md`;
- invalid settings (collector, reviewer, queue limits, fallback), a `Plan collection` marker left by a released slot, and rules that no longer match an edited `Platform mode` or `Git sync`;
- `Cross-check` states that do not match their review lines, and claims held by a released slot.

Fix what you own: your own sections, structure (a missing empty section for a listed agent), and Shared state values with a cited discovery. Never invent or delete another agent's items. For a problem in another agent's section, add a line under `Open consistency issues` in Shared state (`- H-B-01 named as queued for B but missing from plan.md (found by A)`); the owner, or the user, resolves it and removes the line. Do not start new work while the checker reports a problem in your own sections. If a report is wrong, record it under `Open consistency issues` with `(disputed — <why>)` and continue; the user settles it.

## 10. Close a session

Before ending meaningful work:

1. Finish any completed plan-item migration: discovery (always) → handoff event → follow-up plan items → remove the completed item.
2. Rescore the remaining items in your own plan section.
3. Finish or release any cross-check you claimed (`REVIEWING` → verdict, or back to `PENDING`).
4. Update your active handoff section: `Resumable state` and `Next action`.
5. Run the consistency check and fix your own problems.
6. Remove your `Active compute` claims for jobs that have ended. If a job you launched is still running, keep its claim, your `Current host`, and your `Current user`, describe the job in `Resumable state`, and go to step 8 without releasing.
7. Otherwise set `Current host: released` and `Current user: none` so the slot is visibly free for the next session.
8. If `Git sync` is `commit` or `push`, commit the coordination files you changed; with `push`, push them too (section 9).

## 11. Initialize a project

Run:

```bash
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --user kim --platform single --platforms "Claude Code" --git off
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --agents 2 --user kim --platform multi --platforms "Claude Code, Codex" --git push
python <skill-root>/scripts/init_research_orchestrator.py . -n "Project Name" --agents A,B,C --user kim --platform adaptive --git commit
```

Ask the setup questions first (section 0). Without flags the defaults are `--platform adaptive`, `--platforms "Claude Code, Codex"`, `--git off`, `--collector off`, `--queue-limits 50,5`, `--reviewer off`, `--fallback` (`wait` for `multi`, `same-host` otherwise), and no user yet. `--agents` takes either a count (`2` → `A, B`) or a comma-separated list of allowed names. The initializer rejects duplicate or non-standard names, creates missing files only, and never overwrites existing project files. To add an agent to an existing project, add its `## Agent: <name>` plan section, its `### Agent: <name>` handoff section, and its name under `Active agent(s)`.
