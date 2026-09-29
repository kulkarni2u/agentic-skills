---
name: review
description: Review an implementation against its requirements — a combined functional review (does it do what the PRD/spec asked, with evidence from tests and real runs) and code review (correctness, security, reliability defects via the code-review skill) of a branch, PR, diff, commit range, or the working tree. Produces a verification matrix, prioritized findings, and an Approve / Approve with follow-ups / Request changes verdict in docs/blueprint/REVIEW.md. Use standalone when the user asks to review, verify, audit, or sign off on a change or PR, or as phase 8 of the product-blueprint pipeline after implement.
argument-hint: [PR number | branch | commit-range | path] [requirements-source]
---

# Review

Judge whether the change does what was asked and whether it is safe to merge. Orchestrates
`code-review` for diff-level defects; this skill adds the requirements lens. Evidence over
opinion.

## Scope & sources

1. **Change set**: first argument — PR number (`gh pr diff`), branch or range (`git diff <base>...HEAD`,
   base = default branch merge-base), a path, or the working tree if none. Save it to a scratch
   `change.diff`; note base, head, and files changed.
2. **Requirements**, in order of preference: `docs/blueprint/PRD.md` (FR/NFR IDs, acceptance criteria),
   `docs/blueprint/IMPLEMENTATION-LOG.md` (which FRs are claimed done, with tests and files),
   `docs/blueprint/TECHNICAL-DESIGN.md` (design contract), the PR description, or a spec the user gave.
   Review the FRs the change *claims*; list the rest as out of scope, not failed.
3. **No requirement source?** Ask via **AskUserQuestion**: (a) code-only review, (b) point me at
   requirements, (c) I'll type them now. Never invent acceptance criteria.

## Functional review

Build the matrix, one row per in-scope requirement (split FRs with multiple criteria):

`ID | Acceptance criterion | Evidence | Verdict | Notes`

- **Evidence** is `test_file::test_name`, a code path (`file:line`), or observed output. Verdict is
  **Met** / **Partially met** / **Not met** / **Not verifiable** (say what is missing to verify).
- **Run it.** Execute the full test suite, lint, and type check, plus any commands the requirement
  implies. Record commands and results as *observed*; label everything else *inferred*. If something
  cannot run (network, credentials, sandbox), say so — never report a green you did not see.
- **Tests must bite.** For each criterion, find the test that would fail if the behavior broke.
  Flag tautological assertions, over-mocked collaborators (the mock is the thing under test),
  missing negative cases, and criteria with no test. When cheap, prove it with a mutation check
  (break the behavior, run the test, expect red) — only in a scratch `git worktree`, never the
  user's working tree.
- **Edge cases & error paths** named in the PRD (empty, duplicate, unauthorized, over-limit,
  malformed) each need a row or a note.
- **Stubs**: grep changed files for `TODO`, `FIXME`, `NotImplemented`, `501`, `pass`-only bodies,
  skipped/xfail tests. Any hit under an FR marked done in the log is **Not met**.
- **NFRs**: check measurable ones (latency, limits, coverage, security headers) with a real
  measurement; otherwise **Not verifiable** plus what it would take (load test, staging).
- **Scope creep**: behavior, endpoints, or schema in the diff traceable to no requirement.
- **Design drift**: compare API shapes, data model, component boundaries, and the security model
  with `TECHNICAL-DESIGN.md`; each deviation is a finding (undocumented drift) or a design-doc update.
- **Exercise the app** for user-facing FRs when feasible: use the `run` skill (or start the server /
  CLI), walk the primary flow and one failure path, and record what you saw.

## Code review

Invoke the `code-review` skill on the same diff — `slice` → your decisions → `gate` (see its
`SKILL.md`; do not reimplement it) — then merge its blockers/warnings/info into this report.
Then a short **test-quality pass**, matched to the approach in the log:

- **TDD**: unit tests cover branches and error paths of new logic, not just the happy path.
- **BDD**: scenarios map 1:1 to acceptance criteria and read as behavior, not implementation.
- **DDD**: invariants are enforced inside aggregates/entities, not scattered in services or handlers.

Skip style nits. Every finding states a concrete failure scenario ("input X causes Y, so Z").

## Verdict

- **Request changes** — any *Must* requirement **Not met**, or any code-review blocker.
- **Approve with follow-ups** — no blockers, but warnings, Partially met Should/Could items, or
  Not verifiable items that need a tracked follow-up.
- **Approve** — all in-scope requirements Met (or Not verifiable only for stated, low-risk reasons)
  and no blockers or warnings.

## Output

Write `docs/blueprint/REVIEW.md` (or the path the user gives):

```markdown
# Review: <change / PR title>
| Verdict | <verdict> | Base..Head | <refs> | Date | <date> | Requirements | <sources> |

## 1. Summary
Three to five lines: what the change does, the verdict, and the reasons that decided it.

## 2. Verification matrix
## 3. Code findings
Blockers → warnings → info, each `file:line — title`, failure scenario, remediation.
## 4. Test quality
## 5. Scope creep & design drift
## 6. Not verified
What was not checked and why; commands that could not run.
## 7. Commands run
Command → observed result.
```

Then give a short chat summary: verdict, matrix counts by verdict, blocker count, top 3 issues.

## Guardrails

Read-only by default: no edits to the user's tree (mutation checks run in a scratch worktree), no PR comments, approvals,
or external posting unless the user explicitly asks. Offer both after reporting.
Do not restate findings you could not reproduce or reason to a failure scenario.

## After reviewing

Standalone: ask (AskUserQuestion) whether to post the findings to the PR, hand the Not met rows and
blockers to `implement` to fix, or stop. In the pipeline: return control to `product-blueprint`
for the closing summary.
