# CV Leakage Study — Handoff

Everything operational is recorded here. Keep unfinished agent-specific detail inside that agent's active section; completed/reviewed work goes into the shared log.

## Shared state

- Active agent(s): A, B, C
- Current project state: validation fixed to deduplicated GroupKFold; feature work in progress
- Active compute: local CPU (A, B); local GPU idle
- Important shared artifacts/metrics: GroupKFold baseline CV 0.9030 (experiments/e002_dedup.py)

Agent names are work slots (`A`, `B`, `C`, ...), never host or model names. A new concurrent session takes the next unused name and adds it to `Active agent(s)`.

## Active handoff — Agent sections

Each research agent reads and edits only its own active handoff section. Do not copy another agent's unfinished plan here.

`Current host` records which host (Claude Code, Codex, Antigravity, ...) currently owns the slot. A slot is free when it reads `unassigned` or `released`; a free slot that still holds plan items left by a different host is skipped unless the user assigns it. Set it to your host when you take or resume the slot, and to `released` when you close the session. Other sessions may read only the `Current host` and `Current thread` lines of your section: to find a free slot, or to take over a queued item other than your `Current thread` when their own queue runs out (same host only).

### Agent: A
- Current host: Claude Code
- Current thread: H-A-04
- Resumable state: experiments/e004_fold_te.py drafted, not run yet
- Blocker: none
- Next action: run e004 with GroupKFold(5) on deduplicated data

### Agent: B
- Current host: Codex
- Current thread: H-B-03 (cross-check of D-A-001)
- Resumable state: rerunning experiments/e002_dedup.py with fold seed 11
- Blocker: none
- Next action: record a verdict on D-A-001, then start H-B-02

### Agent: C
- Current host: released
- Current thread: none
- Resumable state: none; H-C-02 was taken over by A as H-A-04
- Blocker: none
- Next action: free slot; the next new session takes it


## Completed / review log

All agents may read this shared log. Append completed work, meaningful resource-routing changes, and discovery-review events here. Entries are append-only.

Use this exact format:

```markdown
### YYYY-MM-DD HH:MM — A — H-A-01
- Host: Claude Code | Codex | Antigravity | <other>
- Action: ...
- Result: ...
- Evidence: ...
- Discovery updates: D-A-001 / none
- Review verdict: <discovery ID> CLOSED | HOLD | CHALLENGED / none
- Files/metrics: ...
- Resource: CPU | GPU | Other | none
- Other executor: Kaggle / none
- New plan items: H-A-02, H-A-03 / none — <reason>
- Next resumable action: ...
```

`New plan items` is never a bare `none`; zero follow-ups always gives a reason. When you take over an item from a same-host slot, log it as its own event with `Action: took over H-C-03 from C (same host) as H-A-05`.

### 2026-10-05 14:20 — B — H-B-01
- Host: Codex
- Action: compared random KFold with GroupKFold on customer_id groups
- Result: random KFold CV 0.9162 vs GroupKFold CV 0.9027
- Evidence: experiments/e001_group_check.py; outputs/e001.csv
- Discovery updates: D-B-001
- Review verdict: none
- Files/metrics: CV 0.9162 / 0.9027
- Resource: CPU
- Other executor: none
- New plan items: H-B-02
- Next resumable action: wait for a cross-check of D-B-001

### 2026-10-05 15:05 — A — H-A-01
- Host: Claude Code
- Action: cross-checked D-B-001 with fold seed 7
- Result: gap reproduced (0.0131)
- Evidence: experiments/e001_group_check.py --seed 7
- Discovery updates: D-B-001
- Review verdict: D-B-001 CLOSED
- Files/metrics: CV 0.9158 / 0.9027
- Resource: CPU
- Other executor: none
- New plan items: H-A-02
- Next resumable action: test whether exact duplicates explain the gap

### 2026-10-05 16:40 — A — H-A-02
- Host: Claude Code
- Action: removed exact duplicate rows and rebuilt GroupKFold folds
- Result: random/group CV gap shrank from 0.0135 to 0.0041
- Evidence: experiments/e002_dedup.py; outputs/e002.csv
- Discovery updates: D-A-001
- Review verdict: none
- Files/metrics: CV 0.9071 / 0.9030
- Resource: CPU
- Other executor: none
- New plan items: H-A-03
- Next resumable action: try target encoding on deduplicated data

### 2026-10-05 17:30 — C — H-C-01
- Host: Claude Code
- Action: audited categorical encoders for leakage under GroupKFold
- Result: features/encode.py fits every encoder on the full training set before the fold split
- Evidence: features/encode.py; notes/encoding_audit.md
- Discovery updates: none
- Review verdict: none
- Files/metrics: none
- Resource: CPU
- Other executor: none
- New plan items: H-C-02
- Next resumable action: session closing; slot C released with H-C-02 queued

### 2026-10-05 18:10 — A — H-A-03
- Host: Claude Code
- Action: tested global target encoding on deduplicated data
- Result: hypothesis failed; GroupKFold CV dropped from 0.9027 to 0.8991
- Evidence: experiments/e003_target_encoding.py
- Discovery updates: D-A-002 (negative result)
- Review verdict: none
- Files/metrics: CV 0.8991
- Resource: CPU
- Other executor: none
- New plan items: none — fold-aware encoding is already queued as H-C-02
- Next resumable action: own queue is empty; look for work in the documented order

### 2026-10-05 18:20 — A — H-A-04
- Host: Claude Code
- Action: took over H-C-02 from C (same host) as H-A-04
- Result: moved into A's section and rescored to 17 against D-A-001 and D-A-002
- Evidence: C is released and its latest event (H-C-01) came from Claude Code; no PENDING cross-check from another host was available
- Discovery updates: none
- Review verdict: none
- Files/metrics: none
- Resource: none
- Other executor: none
- New plan items: H-A-04
- Next resumable action: run fold-aware target encoding (H-A-04)

## Archived history

When this file becomes hard to scan, move older completed-log detail to `docs/<focused-name>.md` and leave a short summary/link here. Keep shared state, active agent handoffs, and recent completed/review records in this file.
