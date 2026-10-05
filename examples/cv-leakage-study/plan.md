# CV Leakage Study — Plan

Keep only active unfinished work here. Completed work moves to `handoff.md` and to `discoveries.md` (always for a failed hypothesis, otherwise when reusable).

Each agent edits only its own `## Agent: <name>` section. Plan item IDs use `H-<Agent>-<NN>`, for example `H-Main-01` or `H-A-07`.

Before adding an item, confirm it is not already settled in `discoveries.md` (including negative results), already attempted in the `handoff.md` log, or already queued under another agent (check headings and `Hypothesis` lines only). A repeat needs a real `Improvement` and a citation of the earlier ID.

Priority formula:

```text
Priority = 2*Impact + 2*Information + Confidence + Unblock + Diversity + (3-Cost)
```

All factors are 0-3. Cost is 0 for cheap and 3 for expensive.

Use this exact item format:

```markdown
### H-Main-01 — Short title
- Sources: D-A-001, D-Main-004 / none
- Hypothesis: ...
- Evidence: ...
- Improvement: ...
- Impact: 0-3
- Information: 0-3
- Confidence: 0-3
- Unblock: 0-3
- Diversity: 0-3
- Cost: 0-3
- Priority: ...
- Resource: CPU | GPU | EITHER
- Parallel: YES | NO
- Other: NONE | <external executor>
- Next test: ...
```

Example external executor: `Other: Kaggle`.

## Agent: Main

### H-Main-04 — Fold-aware target encoding
- Sources: D-Main-002, D-Main-001
- Hypothesis: target encoding fit inside each GroupKFold training fold improves CV without leakage
- Evidence: D-Main-002 shows global target encoding leaks (GroupKFold CV 0.9027 → 0.8991); D-Main-001 (not yet verified, REVIEWING Codex (A)) says deduplicated data is the right base
- Improvement: encoding is fit only on training folds of deduplicated data, unlike the global encoding tested in H-Main-03
- Impact: 3
- Information: 2
- Confidence: 2
- Unblock: 1
- Diversity: 2
- Cost: 1
- Priority: 17
- Resource: CPU
- Parallel: YES
- Other: NONE
- Next test: GroupKFold(5) CV with fold-aware encoding against the 0.9030 baseline

## Agent: A

### H-A-03 — Cross-check D-Main-001
- Sources: D-Main-001
- Hypothesis: exact duplicate rows explain most of the random/group CV gap
- Evidence: D-Main-001 (Claude Code) reports the gap shrinking from 0.0135 to 0.0041 after deduplication; not yet verified
- Improvement: independent rerun by a different host on a fresh fold seed
- Impact: 2
- Information: 3
- Confidence: 2
- Unblock: 3
- Diversity: 1
- Cost: 0
- Priority: 19
- Resource: CPU
- Parallel: YES
- Other: NONE
- Next test: rerun experiments/e002_dedup.py with fold seed 11 and compare the gap

### H-A-02 — GPU boosting under GroupKFold
- Sources: D-A-001
- Hypothesis: the GPU gradient-boosting model keeps its lead over the baseline under GroupKFold
- Evidence: D-A-001 (VERIFIED) shows random CV overstated every earlier model comparison by about 0.013
- Improvement: re-evaluates on deduplicated GroupKFold folds instead of random KFold
- Impact: 3
- Information: 3
- Confidence: 1
- Unblock: 1
- Diversity: 2
- Cost: 2
- Priority: 17
- Resource: GPU
- Parallel: YES
- Other: Kaggle
- Next test: 5-fold GroupKFold run; overflow to Kaggle if the local GPU is busy

## Agent: B

_No active items. Slot released; the next new session may take it._
