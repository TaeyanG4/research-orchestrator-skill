# CV Leakage Study — Discoveries

Shared reusable findings live here. Every agent reads this file.

Verification is per **host**, not per agent: a discovery made on one host (for example Codex) is cross-checked **once** by a different host (for example Claude Code). Sessions on the same host do not re-review each other.

Discovery IDs use `D-<Agent>-<NNN>`, numbered by the agent that creates the discovery, for example `D-Main-001` or `D-A-014`.

Use this exact format:

```markdown
## D-A-001 — Short title
- Source: A
- Host: Codex
- Cross-check: VERIFIED
- Finding: ...
- Evidence: ...
- Implication: ...
- Reviews:
  - Claude Code (Main): CLOSED — reproduced independently with ...
```

`Cross-check` states:

- `PENDING`: no different host has reviewed it yet. New discoveries start here, with an empty `Reviews:` list.
- `REVIEWING <Host> (<Agent>)`: a different-host session has claimed the review.
- `VERIFIED`: a different host reviewed it and recorded `CLOSED`.
- `HOLD`: a different host needs specific evidence, a condition change, or an improvement first.
- `CHALLENGED`: a host found a material contradiction, flaw, or missing assumption.

Rules:

- The source does not review its own discovery.
- Review only discoveries whose `Host` differs from yours and whose `Cross-check` is `PENDING` (or `HOLD` when its condition is now met). Claim it first with `REVIEWING <your host> (<your agent>)`.
- One cross-host review is enough; add another only for high-impact or disputed discoveries.
- Review lines use `<Host> (<Agent>): CLOSED | HOLD | CHALLENGED — reason`. `HOLD` and `CHALLENGED` must say what would make the discovery acceptable.
- When the source revises a `HOLD` or `CHALLENGED` discovery, it updates `Evidence`, keeps the old reviews, and resets `Cross-check` to `PENDING`.
- If only one host is available, a different slot on the same host may cross-check; begin its reason with `same host —`.
- Use `VERIFIED` discoveries freely. A plan item built on a `PENDING`, `REVIEWING`, or `HOLD` discovery must say so in its `Evidence`. Do not build on `CHALLENGED` discoveries until resolved.

Negative results are discoveries too. When a hypothesis fails or is disproved, record it here (`Finding: <claim> does not hold under <conditions>`) so no agent proposes it again. Before adding a plan item, every agent searches this file first.

A discovery may generate many plan hypotheses, and one hypothesis may combine many discoveries. When moving an idea back into `plan.md`, always include the source IDs plus the concrete `Evidence` and `Improvement` that justify the new attempt.

Do not archive this file merely because it grows; merge duplicate discoveries instead.

---

## D-A-001 — Random CV leaks customer groups
- Source: A
- Host: Codex
- Cross-check: VERIFIED
- Finding: rows from the same customer_id land in both training and validation folds under random KFold
- Evidence: experiments/e001_group_check.py; random KFold CV 0.9162 vs GroupKFold CV 0.9027
- Implication: random CV is optimistic by about 0.013; use GroupKFold for model selection
- Reviews:
  - Claude Code (Main): CLOSED — reproduced with fold seed 7; gap 0.0131

## D-Main-001 — Exact duplicates explain most of the gap
- Source: Main
- Host: Claude Code
- Cross-check: REVIEWING Codex (A)
- Finding: removing exact duplicate rows shrinks the random/group CV gap from 0.0135 to 0.0041
- Evidence: experiments/e002_dedup.py; outputs/e002.csv
- Implication: deduplicate before building GroupKFold folds
- Reviews:

## D-Main-002 — Global target encoding does not hold under GroupKFold
- Source: Main
- Host: Claude Code
- Cross-check: PENDING
- Finding: global target encoding does not hold under GroupKFold on deduplicated data (CV 0.9027 → 0.8991)
- Evidence: experiments/e003_target_encoding.py
- Implication: do not retry global target encoding; only fold-aware encoding is worth testing
- Reviews:
