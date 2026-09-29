---
name: implement
description: Implement requirements into working, tested code, choosing one primary methodology per unit of work — TDD, BDD, or DDD — based on the nature of the requirement. Accepts FR IDs, a P0 slice, a user story, a spec file, or a plain prompt. Use standalone when the user asks to implement, build, code, or fix a feature or requirement, or as phase 7 of the product-blueprint pipeline (after scaffold).
argument-hint: [FR-ids | user story | path-to-spec | free-text requirement] [--approach tdd|bdd|ddd]
---

# Implement

Turn requirements into working code, test-first, using the one methodology that fits
each unit of work. Small vertical slices, proven by tests, traced back to FR IDs.

## Inputs

Prefer `docs/blueprint/PRD.md`, `docs/blueprint/TECHNICAL-DESIGN.md`, and
`docs/blueprint/03-tech-stack.md`; the
argument selects the scope (FR IDs, a P0 slice, a story, a spec file, or free text).
No argument but a scaffold README checklist exists: take the first P0 items. If the
requirement has no acceptance criteria, derive them and mark each *(assumption)*; if the
input is too thin to derive testable criteria, suggest `requirements-clarify` or
`prd-writer` first and ask whether to proceed on assumptions.

**Brownfield**: before writing any function, use `repo-index` to find existing code that
already does it. Detect the test runner, lint/typecheck commands, and directory layout from
the repo (manifest, CI config, existing tests) and follow them. Never introduce a new
framework or dependency without asking.

## Choose the approach

Pick ONE primary approach per unit (an FR or a cohesive group). Score the signals; the
approach with the most matching rows wins.

| Signal in the requirement / design | Approach |
|---|---|
| Pure input→output logic, parsing, calculation, algorithm, utility | TDD |
| Bug fix or regression | TDD (failing regression test first) |
| Clear spec, few collaborators, no user-visible workflow | TDD |
| Acceptance criteria phrased as user/system behavior; API endpoint; UI or CLI flow | BDD |
| Spans several components; stakeholders would read the scenarios | BDD |
| Many business rules/invariants on the same entities; state transitions | DDD |
| State diagram or lifecycle in the design; ER model with aggregates/relations | DDD |
| Domain vocabulary is contested or overloaded across the PRD | DDD |

Tie-breakers: rules/lifecycle beats workflow (DDD > BDD); workflow beats plumbing
(BDD > TDD); when still tied, choose the simpler (TDD). A hybrid is allowed —
e.g. DDD to model the core, BDD for the acceptance layer — but name one primary and say
what the secondary covers.

A user-specified approach (`--approach` or in prose) is final. Otherwise state the choice
and rationale per unit in one or two lines before coding. Ask via **AskUserQuestion** only
when signals are genuinely split between two approaches or the user asked you to choose.

## Plan

Split the work into small vertical slices (one behavior end to end), ordered by
dependency. Create a task list, one task per slice, and work one slice at a time. Each
slice ends green: full test suite plus lint/typecheck pass before the next begins.

## Loops

**TDD** — one failing test at a time. Run it and confirm it fails for the *right reason*
(assertion, not import/syntax error). Write the minimal code to pass. Refactor only on
green. Repeat: edge cases, error paths, then the next behavior.

**BDD** — turn acceptance criteria into Given/When/Then scenarios, outside-in.
Use the repo's BDD tool if present (Cucumber, behave, pytest-bdd, SpecFlow); otherwise write
tests named `given_…_when_…_then_…` in the existing framework — don't add a BDD
dependency without asking. Write the acceptance test first and watch it fail, then drive
the inner units with TDD until it passes. Scenarios use domain language, not implementation
detail.

**DDD** — first write a short glossary of domain terms (ubiquitous language; use these
names in code, tests, and logs). Identify bounded contexts, aggregates and their
invariants, entities, value objects, domain events, and repository interfaces from the ER
model. Write failing aggregate-level tests for each invariant and transition, then
implement the domain model with no infrastructure imports. Only then add application
services, repository implementations, and adapters (API/DB), tested at their own layer.

## Coding standards

Precedence, highest first: the repo's own rules (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`,
style guides, linter/formatter config), then `TECHNICAL-DESIGN.md`, then the defaults below.
Read the repo's rules before the first slice; when a default conflicts with them, theirs wins.

- **Design conformance**: API paths, request/response shapes, status codes, data model fields,
  and component boundaries match the technical design. A needed deviation is raised with the
  user and logged, not made silently.
- **Security**: validate and bound every external input at the boundary; parameterized queries,
  no string-built SQL/shell/HTML; enforce authN/authZ server-side on every new entry point per
  the design's security model; secrets from config/env only, never in code, tests, or logs;
  no PII or tokens in logs or error messages.
- **Error handling**: fail fast at boundaries with specific, actionable errors; never swallow
  exceptions or return silent defaults; map domain errors to the API's documented error shape;
  release resources deterministically (context managers, `finally`, `defer`, `using`).
- **Readability**: names from the domain glossary / PRD vocabulary; small functions with one
  job; no magic numbers — named constants; comments explain *why*, not *what*; match the
  surrounding code's comment density and idiom.
- **Structure**: dependencies point inward (domain ← application ← adapters); inject
  collaborators rather than constructing them inline, so tests don't need global patching;
  prefer composition and the simplest thing that passes — no speculative abstractions,
  config flags, or extension points no requirement asks for (YAGNI); no copy-paste — reuse
  or extract once there's a second real caller.
- **Performance**: meet the NFR numbers that apply to the slice (latency, limits, payload
  size); avoid N+1 queries and unbounded loads/collections; paginate list endpoints.
- **Observability**: log at boundaries and on failures with enough context to debug
  (request/entity IDs), at the repo's existing log levels; add the metrics/traces the design
  names.
- **Tests**: deterministic (no real clock, network, or randomness without control), isolated,
  fast; assert behavior, not implementation; mock only at architectural boundaries.

## Guardrails

- Never weaken, delete, or skip a test to get green; if a test is wrong, say why and fix it visibly.
- Never leave a 501/TODO stub behind for an FR you report as done.
- Run the full suite and lint/typecheck after each slice; report the real output.
- Keep diffs minimal and in scope; no drive-by refactors or unrelated files.
- Follow existing conventions over personal preference.
- Don't commit or push unless asked.
- If blocked (missing decision, failing dependency, ambiguous criterion), mark the FR `blocked`, record why, and move on or ask.

## Traceability

Write or update `docs/blueprint/IMPLEMENTATION-LOG.md`:

```markdown
| FR | Approach | Tests (file::name) | Code | Status | Notes / assumptions |
```

Status is `done`, `partial`, or `blocked`. Record every *(assumption)* and any derived
acceptance criteria. If the scaffold README has a P0 checklist, tick the items completed.

## Refresh the index

Once the code is ready — last slice green, whether or not it has been committed — re-run
`repo-index index <repo-root>` in the foreground and confirm it finished. The auto-index git
hooks only fire on git operations and run in the background, so they miss uncommitted work
and may not have finished when `review` starts looking things up. If the hooks aren't
installed yet, run `repo-index install-hooks <repo-root>` too. repo-index scans only `.py`
files; for a repo with none, skip this step and say so in the report.

## Report

Tell the user: FRs completed and their status, approach per FR with the one-line why,
test counts and results actually observed (pass/fail/skipped, lint/typecheck), whether the
index was refreshed, and open
issues or assumptions needing a decision. Standalone: offer the `review` skill next. In the
pipeline: return control to `product-blueprint` for the closing summary.
