---
name: code-review
description: Use when reviewing a patch, pull request, commit, or unified diff for actionable defects across any programming language or framework.
---

# Jev-Style Code Review

Review changed behavior through bounded decisions and deterministic reporting policy. Prefer a few evidence-backed findings.

## Workflow

1. Establish scope and base. Read repository instructions, callers, tests, and contracts.
2. Run relevant repository-native checks. Keep observed tool results separate from semantic review.
3. Slice a unified diff into review units:

   ```bash
   python3 skills/code-review/scripts/code_review.py slice change.diff > hunks.json
   ```

   Use `-` for stdin. Resolve the script relative to this `SKILL.md` when installed elsewhere.
4. Inspect enough surrounding code to test each hypothesis. Skip generated, locked, formatting-only, and weak-signal changes unless requested.
5. Use the decision contract below. Scores are bounded inputs, not calibrated probabilities unless the provider was validated on representative data.
6. Gate the candidates:

   ```bash
   python3 skills/code-review/scripts/code_review.py gate decisions.json > review.json
   ```

   It is advisory by default. Use `--fail-on` only when the user requests CI gating.
7. Report blockers before warnings. With no findings, say so and name verification limits.

## Decision contract

Each entry in `{"decisions": [...]}` contains `condition` (Noul), `classification` (Choice), and `severity` (Score):

```json
{
  "path": "src/auth.ts",
  "line": 42,
  "condition": {"probability": 0.94, "confidence": 0.91},
  "classification": {
    "category": "security",
    "issue_type": "authorization-bypass",
    "confidence": 0.93
  },
  "severity": {"value": 9.0, "confidence": 0.90},
  "title": "User-controlled flag bypasses authorization",
  "evidence": "The query flag selects an arbitrary account ID.",
  "impact": "An authenticated user can change another account.",
  "remediation": "Authorize cross-account updates using trusted server-side roles."
}
```

Use slug-style `issue_type` values. Categories include `correctness`, `security`, `reliability`, `resource-management`, `concurrency`, `persistence`, `integration`, `performance`, `api-contract`, and `maintainability`.

## Evidence rules

- Tie findings to changed behavior and a concrete failure mode at the nearest supporting changed line.
- Confirm assumptions from code, tests, configuration, or authoritative contracts. State unresolved uncertainty.
- Do not report style preferences, speculative future risks, or tool output you did not observe.
- Keep remediation proportional; do not require unrelated refactors.
- Review is read-only by default. Do not edit code, post comments, request changes, or update external systems without explicit authorization.

## Policy quick reference

| Stage | Default decision |
|---|---|
| Triage | Suppress probability below `0.25` or triage confidence below `0.50` |
| Classification | Suppress confidence below `0.60` |
| Blocker | Severity at least `7.0` and all confidence values at least `0.80` |
| Warning | Severity at least `4.0` and severity confidence at least `0.65` |
| Info | Valid evidence-backed candidate below warning thresholds |

## Common mistakes

- Reviewing only the hunk when surrounding control flow changes the conclusion.
- Treating model confidence as measured calibration.
- Mixing deterministic analyzer failures with model-inferred findings.
- Posting duplicate findings for the same root cause; keep the clearest instance and describe the blast radius.
