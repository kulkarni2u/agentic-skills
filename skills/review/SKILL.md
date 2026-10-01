---
name: review
description: Review an implementation against its requirements — a combined functional review (does it do what the PRD/spec asked, with evidence from tests and real runs) and code review (correctness, security, reliability defects via the code-review skill) of a branch, PR, diff, commit range, or the working tree. Produces a verification matrix, prioritized findings, and an Approve / Approve with follow-ups / Request changes verdict in docs/blueprint/REVIEW.md. Use standalone when the user asks to review, verify, audit, or sign off on a change or PR, or as phase 8 of the product-blueprint pipeline after implement.
argument-hint: [PR number | branch | commit-range | path] [requirements-source]
---

# Review

Judge whether the change does what was asked and is safe to merge. Scripts do the bookkeeping
(scope, matrix skeleton, verdict rules, report); you supply evidence and judgment.

```
REV="python3 <this-skill-dir>/scripts/review.py"
IMPL="python3 <this-skill-dir>/../implement/scripts/implement.py"
CR="python3 <this-skill-dir>/../code-review/scripts/code_review.py"
```

Work in a scratch directory for `change.diff`, `scope.json`, `decisions.json`, and `bundle.json`.

## 1. Scope

`$REV scope [range | branch | commit] [--base B] --out change.diff > scope.json` (no target = working
tree). For a PR, fetch its diff and pass `--diff pr.diff`. The JSON lists changed files, FRs claimed
in `IMPLEMENTATION-LOG.md`, stubs on added lines, and `untraced` code files (scope-creep candidates).

No PRD, log, or user spec? Ask via **AskUserQuestion**: code-only review, point to requirements, or
type them now. Never invent acceptance criteria.

## 2. Functional review

1. `$REV matrix --scope scope.json [--ids …] > matrix.json` — one row per acceptance criterion for
   the claimed FRs (others land in `out_of_scope`, not failed). Stubbed "done" FRs come pre-failed.
2. `$IMPL check > checks.json` — the observed test/lint/typecheck results. Never claim a green you
   didn't see; anything that can't run goes in `not_verified` with the reason.
3. Fill every `verdict` (Met / Partially met / Not met / Not verifiable) and `evidence`
   (`file::test`, `file:line`, or observed output). For each row:
   - Find the test that would fail if the behavior broke; flag tautologies, mocks of the thing
     under test, and missing negative cases. When cheap, prove it with a mutation check in a
     scratch `git worktree`, never the user's tree.
   - Cover PRD edge cases and error paths; measure NFRs or mark Not verifiable with what it'd take.
   - Exercise user-facing flows (the `run` skill, or start the app) — primary path plus one failure.
4. Judge each `untraced` file: scope creep, or legitimate support code. Compare API shapes, data
   model, boundaries, and security model with `TECHNICAL-DESIGN.md`; record deviations in `drift`.

## 3. Code review

Run the `code-review` skill on `change.diff`: `$CR slice change.diff`, write `decisions.json` per
its contract, `$CR gate decisions.json > gate.json`. Add a test-quality pass matched to the logged
approach (TDD: branches and error paths covered; BDD: scenarios map 1:1 to criteria; DDD: invariants
enforced inside aggregates) and check against
[../implement/references/coding-standards.md](../implement/references/coding-standards.md) (repo
rules first). Report only issues with a concrete failure scenario; skip style nits.

## 4. Verdict and report

Assemble `bundle.json`: `title`, `base`, `head`, `requirements_sources`, `summary` (3–5 lines),
`matrix` (filled rows), `gate`, `checks`, `test_quality`, `drift`, `not_verified` (string lists), and
any extra `commands` (`{command, result}`). Then:

`$REV render bundle.json --date <today> [--out docs/blueprint/REVIEW.md]`

The verdict is computed, not chosen: **Request changes** if any Must row is Not met, any code-review
blocker, or any failed check; **Approve with follow-ups** for warnings, Partially met / Not
verifiable rows, non-Must misses, or drift; otherwise **Approve**. `$REV verdict bundle.json` shows
it without writing. Give the user the verdict, matrix counts, blocker count, and top 3 issues.

## 5. Finish

- Read-only: no edits to the user's tree, PR comments, or approvals unless asked.
- Run `$IMPL reindex` when done, again after any fix round or PR checkout (writing `.repo-index/`
  is tooling state, not a code edit).
- Standalone: ask (AskUserQuestion) whether to post findings to the PR, hand Not met rows and
  blockers to `implement`, or stop. In the pipeline: return control to `product-blueprint`.
