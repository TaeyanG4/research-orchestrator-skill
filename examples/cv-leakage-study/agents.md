# CV Leakage Study — Agent Rules

## Agent names

Agent names are work slots, not tool or model identities. Allowed names, assigned in order:

```text
A, B, C, ... Z, AA, AB, ... ZZ
```

- Single-agent work always uses `A`. Each additional concurrent session takes the next unused letter; after `Z`, two-letter names follow in spreadsheet-column order. Released slots are reused before new ones are created.
- Never use a host, product, or model name (`Claude`, `Codex`, `GPT`, `Gemini`, `Antigravity`, ...) as an agent name. Any host may continue any slot.
- A host is the platform (`Claude Code`, `Codex`, `Antigravity`, ...), not the model: two Claude Code sessions running different models are the same host.
- Which host owns a slot is recorded in `handoff.md`: `Current host` in the agent's active section (update it whenever you take or resume the slot) and `Host` in each completed-log event.
- A slot is free when its `Current host` is `unassigned` or `released`. If no name is assigned, read only the `Current host` line of each agent section in `handoff.md` and take the first free slot in order (`A`, `B`, `C`, ...), skipping a free slot that still holds plan items left by a different host unless the user assigns it to you; if none is free, create the next unused letter (plan section, handoff section, and `Active agent(s)`). Set `Current host: <your host>` when you take a slot and `Current host: released` when you close the session. Reclaim a slot a crashed session left taken only when the user says so.
- IDs embed the owner: plan items `H-<Agent>-<NN>` (`H-A-01`, `H-B-07`), discoveries `D-<Agent>-<NNN>` (`D-A-001`, `D-C-014`). Number only your own IDs and never reuse a number.
- The current list of agents lives under `Active agent(s)` in `handoff.md`, not here. This file holds only stable rules.

## Read order

1. `agents.md`
2. all of `discoveries.md`
3. `handoff.md`: shared completed/review log plus only your own active handoff section
4. `plan.md`: only your own detailed `## Agent: <name>` section

A dispatcher, or a session choosing a take-over item, may inspect only task ID, owner, priority, cost, information, resource, parallel-safety, and `Other` executor metadata across plan sections.

## Core rules

- Keep only unfinished active work in `plan.md`; execute highest priority first.
- Before adding a plan item, check it is not a duplicate: search `discoveries.md` (including negative results), the completed log in `handoff.md` and `docs/`, and the other agents' plan item headings and `Hypothesis` lines. Skip settled (`VERIFIED`) or `CHALLENGED` claims and anything already queued; otherwise cite the prior ID and give a real `Improvement`.
- When a plan item finishes, write its operational result to `handoff.md`, record reusable knowledge in `discoveries.md` — always including a negative-result discovery when the hypothesis failed — plan its follow-ups (see "Plan follow-ups" below), then remove the completed plan item.
- Read all discoveries, but do not read another active agent's detailed plan or active handoff unless explicitly asked to review it. The only cross-section peeks allowed are dispatcher metadata, the duplicate check above (headings and `Hypothesis` lines only), the `Current host` and `Current thread` lines when choosing a slot or a take-over source, and the one item you take over.
- Discoveries are cross-checked once by a different host, not by every agent (see "Discovery cross-check" below).
- A discovery may create zero, one, or many new hypotheses; one hypothesis may combine many discoveries.
- When bringing a discovery back into `plan.md`, include `Sources`, `Evidence`, and `Improvement` so the new attempt is justified and materially different.
- Re-score affected plan items when evidence changes.
- Re-read shared files immediately before editing and patch only the relevant section or append a new entry.
- Do not create per-agent continuity folders or a separate process file.
- Create `docs/` only to archive old handoff history when needed.

## Plan follow-ups (zero or more)

Every time you write or update a discovery — a new finding, a negative result, or a cross-check verdict — decide what it changes before picking your next item:

1. Add each next test that could change a decision as a plan item in your own section, with `Sources`, `Evidence`, and `Improvement`, after the duplicate check.
2. Rescore your existing items it affects; remove the ones it made pointless.
3. Zero follow-ups is valid but must be deliberate: write `New plan items: none — <reason>` in the handoff event. A bare `none` is not allowed.

## When your own queue runs out

Look for work in this order before going idle:

1. Re-read your own section (a same-host session may have taken items; the handoff log says so).
2. Claim a `PENDING` cross-check from a different host.
3. Take over an item from a same-host slot (below).
4. Derive new hypotheses from discoveries.
5. If nothing worthwhile is left, note it in your active handoff section, set `Current host: released`, and stop.

**Taking over from a same-host slot.** A host is the platform, so this works across sessions and models of the same host. Items queued under a different host stay with that host.

- Eligible sources: a slot whose `Current host` equals yours, or a `released`/`unassigned` slot whose latest completed-log event came from your host. Never take the item in the owner's `Current thread`.
- Pick by metadata only: highest `Priority` (ties: lower `Cost`, then higher `Information`) that you can run now.
- Re-read `plan.md`, then move the block into your own section with your next ID and the old ID in the title: `### H-A-05 — <title> (from H-C-03)`. The old ID is retired.
- Rescore it, and log `Action: took over H-C-03 from C (same host) as H-A-05` in the handoff.

## Discovery cross-check

A discovery made on one host (for example Codex) is checked **once** by a session on a different host (for example Claude Code). Sessions on the same host never re-review each other, and the source never reviews its own discovery.

Two different words are used, in two different places. Do not mix them up:

- **Verdict** — what the reviewer writes on its own line under `Reviews:`. Only `CLOSED`, `HOLD`, or `CHALLENGED`.
- **State** — the discovery's `Cross-check:` field, which everyone reads to see where it stands.

| Reviewer's verdict (`Reviews:` line) | Resulting state (`Cross-check:`) | Meaning |
| --- | --- | --- |
| — | `PENDING` | No different host has reviewed it yet |
| — | `REVIEWING <Host> (<Agent>)` | A different-host session has claimed the review |
| `CLOSED` | `VERIFIED` | The reviewer accepts it. **This is the normal pass.** |
| `HOLD` | `HOLD` | Plausible, but specific evidence or an improvement is needed first |
| `CHALLENGED` | `CHALLENGED` | A contradiction, flaw, or missing assumption was found. **This is a failure, not a pass.** |

`CLOSED` is never written in `Cross-check:`, and `VERIFIED` is never written as a verdict.

A passing review looks like this:

```markdown
- Host: Codex
- Cross-check: VERIFIED
- Reviews:
  - Claude Code (A): CLOSED — reproduced independently with ...
```

To review:

1. Pick a discovery whose `Host` differs from yours and whose `Cross-check` is `PENDING` (or `HOLD` whose stated condition is now met).
2. Claim it: set `Cross-check: REVIEWING <your host> (<your agent>)`. Do not take a discovery someone else has claimed unless that agent's `Current host` reads `released` or `unassigned`, or the user says so.
3. Add your line `<your host> (<your agent>): CLOSED | HOLD | CHALLENGED — reason`. For `HOLD` or `CHALLENGED`, say what would make it acceptable.
4. Set `Cross-check` to the matching state from the table. If an earlier `CHALLENGED` review is still unresolved, the state stays `CHALLENGED` even after a later `CLOSED`.
5. If you stop before finishing, set `Cross-check` back to `PENDING`.

One cross-host review is enough; add another only for high-impact or disputed discoveries. When the source revises a `HOLD` or `CHALLENGED` discovery, it updates `Evidence` and resets `Cross-check` to `PENDING`. If only one host is available, a different slot on the same host may review, starting its reason with `same host —`.

## Priority scoring

Score 0-3 on Impact, Information, Confidence, Unblock, Diversity, and Cost (0 cheap, 3 expensive).

```text
Priority = 2*Impact + 2*Information + Confidence + Unblock + Diversity + (3-Cost)
```

Range 0-24. Break ties by lower Cost, then higher Information.

Each plan item also declares:

```text
Resource: CPU | GPU | EITHER
Parallel: YES | NO
Other: NONE | <external executor>
# Example: Other: Kaggle
```

## Adaptive workers

When parallel work is useful, start with two agents (`A`, `B`) and add more only while independent high-value work and compute headroom remain. Stop at practical full load before contention reduces throughput.

- Fill idle GPU with the highest-priority compatible GPU/EITHER item.
- Fill idle CPU with the highest-priority compatible CPU/EITHER item.
- Use the idle local resource while the other is busy.
- When local CPU and GPU are saturated, use an available `Other` executor only for worthwhile compatible work and only when authorization/quotas permit it.
- Scale down when memory pressure, I/O contention, duplicated work, or lower throughput appears.

## Close a session

Finish completed plan-item migrations, rescore your remaining items, finish or release any cross-check you claimed, update your active handoff section with the exact next resumable action, and set `Current host: released`.
