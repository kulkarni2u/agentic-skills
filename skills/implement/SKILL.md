---
name: implement
description: Implement requirements into working, tested code, choosing one primary methodology per unit of work — TDD, BDD, or DDD — based on the nature of the requirement. Accepts FR IDs, a P0 slice, a user story, a spec file, or a plain prompt. Use standalone when the user asks to implement, build, code, or fix a feature or requirement, or as phase 7 of the product-blueprint pipeline (after scaffold).
argument-hint: [FR-ids | user story | path-to-spec | free-text requirement] [--approach tdd|bdd|ddd]
---

# Implement

Turn requirements into working code, test-first, one vertical slice at a time, traced to FR IDs.
Mechanical steps run through the bundled helper; spend judgment on design and tests.

`IMPL="python3 <this-skill-dir>/scripts/implement.py"` — every subcommand prints JSON.

| Step | Command |
|---|---|
| Requirements + acceptance criteria | `$IMPL requirements [--ids FR-1,FR-2] [--must] [--prd PATH]` |
| Repo rules, CI files, test/lint/typecheck commands, BDD tooling | `$IMPL detect [root]` |
| Approach scoring (TDD/BDD/DDD) | `$IMPL approach --id FR-2` or `$IMPL approach "<text>"` |
| Run the repo's checks | `$IMPL check [root] [--only test,lint]` (exit 1 = red) |
| Leftover stubs / skipped tests | `$IMPL stubs <paths>` or `$IMPL stubs --diff change.diff` |
| Traceability log (+ README checklist tick on `done`) | `$IMPL log set FR-1 --approach tdd --tests … --code … --status done` |
| Refresh the code index | `$IMPL reindex [root]` |

## 1. Inputs

Run `requirements` on `docs/blueprint/PRD.md` (or the spec given) to get the in-scope rows; with no
argument, take `requirements --must` minus the FRs `log show` already marks `done`. A row with no acceptance
criteria: derive them and mark each *(assumption)*; if even that's impossible, suggest
`requirements-clarify` / `prd-writer` and ask whether to proceed. Read `TECHNICAL-DESIGN.md` and
`03-tech-stack.md` for the slice being built.

Run `detect`, then read every file it lists under `rules` — they override the defaults in
[references/coding-standards.md](references/coding-standards.md), which you also follow. Brownfield:
query `repo-index` for existing code before writing any function. Never add a framework or
dependency (including a BDD tool) without asking.

## 2. Choose the approach

A user-specified approach is final. Otherwise run `approach` per FR: it scores rubric signals
(pure logic / bug fix → TDD; user workflow / API / Given-When-Then phrasing → BDD; business rules /
lifecycle / domain language → DDD; ties break DDD > BDD > TDD; no signal → TDD). Sanity-check the
result against the design (a state diagram for the entity favours DDD), then state the choice and
a one-line why. If `split` is true, or you overrule the score, ask via **AskUserQuestion**. A hybrid
(e.g. DDD model + BDD acceptance) is fine; name the primary.

## 3. Build, one slice at a time

Order slices by dependency in a task list. Each slice:

- **TDD** — one failing test; confirm it fails on the assertion, not an import/syntax error; minimal
  code to pass; refactor on green; then edge cases and error paths.
- **BDD** — acceptance criteria → Given/When/Then scenarios in domain language, using the tool in
  `detect.bdd_tools` or else `given_…_when_…_then_…` tests in the existing framework. Watch the
  acceptance test fail, then drive inner units with TDD until it passes.
- **DDD** — glossary of domain terms first (use them in code, tests, logs); aggregates, invariants,
  value objects, events, repository interfaces from the ER model; failing aggregate-level tests per
  invariant/transition; domain code with no infrastructure imports; then services and adapters.

A slice is done only when `check` passes (report its real output) and `stubs` on the slice's files
is clean. Then `log set` the FR with approach, tests (`file::name`), code files, status
(`done`/`partial`/`blocked`), and any assumptions.

## 4. Guardrails

- Never weaken, delete, or skip a test to get green; if a test is wrong, fix it visibly and say why.
- Keep diffs in scope — no drive-by refactors. Raise design deviations instead of making them.
- Blocked (missing decision, failing dependency, ambiguous criterion) → `log set --status blocked`
  with the reason, then move on or ask.
- Don't commit or push unless asked.

## 5. Finish

Once the code is ready — committed or not — run `reindex` and confirm `status` is `indexed` or
`skipped` (no Python); git hooks alone miss uncommitted work. On `unavailable`, run its `fix`.

Report: FRs and status, approach per FR with the why, observed `check` results, index status,
open assumptions. Standalone: offer the `review` skill. In the pipeline: return control to
`product-blueprint`.
