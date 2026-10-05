# CV Leakage Study — Handoff

Everything operational is recorded here. Keep unfinished agent-specific detail inside that agent's active section; completed/reviewed work goes into the shared log.

## Shared state

- Active agent(s): Main, A, B
- Current project state: validation fixed to deduplicated GroupKFold; feature work in progress
- Active compute: local CPU (Main, A); local GPU idle
- Important shared artifacts/metrics: GroupKFold baseline CV 0.9030 (experiments/e002_dedup.py)

Agent names are work slots (`Main`, `A`, `B`, ...), never host or model names. A new concurrent session takes the next unused name and adds it to `Active agent(s)`.

## Active handoff — Agent sections

Each research agent reads and edits only its own active handoff section. Do not copy another agent's unfinished plan here.

`Current host` records which host (Claude Code, Codex, Antigravity, ...) currently owns the slot. A slot is free when it reads `unassigned` or `released`. Set it to your host when you take or resume the slot, and to `released` when you close the session. A new session may read only this line of other agents' sections, to find a free slot.

### Agent: Main
- Current host: Claude Code
- Current thread: H-Main-04
- Resumable state: experiments/e004_fold_te.py drafted, not run yet
- Blocker: none
- Next action: run e004 with GroupKFold(5) on deduplicated data

### Agent: A
- Current host: Codex
- Current thread: H-A-03 (cross-check of D-Main-001)
- Resumable state: rerunning experiments/e002_dedup.py with fold seed 11
- Blocker: none
- Next action: record a verdict on D-Main-001, then start H-A-02

### Agent: B
- Current host: released
- Current thread: none
- Resumable state: none
- Blocker: none
- Next action: free slot; the next new session takes it


## Completed / review log

All agents may read this shared log. Append completed work, meaningful resource-routing changes, and discovery-review events here. Entries are append-only.

Use this exact format:

```markdown
### YYYY-MM-DD HH:MM — Main — H-Main-01
- Host: Claude Code | Codex | Antigravity | <other>
- Action: ...
- Result: ...
- Evidence: ...
- Discovery updates: D-Main-001 / none
- Review verdict: <discovery ID> CLOSED | HOLD | CHALLENGED / none
- Files/metrics: ...
- Resource: CPU | GPU | Other | none
- Other executor: Kaggle / none
- New plan items: H-Main-02, H-Main-03 / none
- Next resumable action: ...
```

### 2026-10-05 14:20 — A — H-A-01
- Host: Codex
- Action: compared random KFold with GroupKFold on customer_id groups
- Result: random KFold CV 0.9162 vs GroupKFold CV 0.9027
- Evidence: experiments/e001_group_check.py; outputs/e001.csv
- Discovery updates: D-A-001
- Review verdict: none
- Files/metrics: CV 0.9162 / 0.9027
- Resource: CPU
- Other executor: none
- New plan items: H-A-02
- Next resumable action: wait for a cross-check of D-A-001

### 2026-10-05 15:05 — Main — H-Main-01
- Host: Claude Code
- Action: cross-checked D-A-001 with fold seed 7
- Result: gap reproduced (0.0131)
- Evidence: experiments/e001_group_check.py --seed 7
- Discovery updates: D-A-001
- Review verdict: D-A-001 CLOSED
- Files/metrics: CV 0.9158 / 0.9027
- Resource: CPU
- Other executor: none
- New plan items: H-Main-02
- Next resumable action: test whether exact duplicates explain the gap

### 2026-10-05 16:40 — Main — H-Main-02
- Host: Claude Code
- Action: removed exact duplicate rows and rebuilt GroupKFold folds
- Result: random/group CV gap shrank from 0.0135 to 0.0041
- Evidence: experiments/e002_dedup.py; outputs/e002.csv
- Discovery updates: D-Main-001
- Review verdict: none
- Files/metrics: CV 0.9071 / 0.9030
- Resource: CPU
- Other executor: none
- New plan items: H-Main-03
- Next resumable action: try target encoding on deduplicated data

### 2026-10-05 18:10 — Main — H-Main-03
- Host: Claude Code
- Action: tested global target encoding on deduplicated data
- Result: hypothesis failed; GroupKFold CV dropped from 0.9027 to 0.8991
- Evidence: experiments/e003_target_encoding.py
- Discovery updates: D-Main-002 (negative result)
- Review verdict: none
- Files/metrics: CV 0.8991
- Resource: CPU
- Other executor: none
- New plan items: H-Main-04
- Next resumable action: run fold-aware target encoding (H-Main-04)

## Archived history

When this file becomes hard to scan, move older completed-log detail to `docs/<focused-name>.md` and leave a short summary/link here. Keep shared state, active agent handoffs, and recent completed/review records in this file.
