---
name: product-blueprint
description: Master skill that turns any requirements input (PDF, Word doc, markdown file, or a plain prompt) into a complete product blueprint. It orchestrates requirements intake, an interactive clarification loop until at least 90% confidence, interactive tech-stack selection, PRD generation, technical design documentation with diagrams, a devil's-advocate stress test of the stack and the design, and optionally scaffolding, test-first implementation, and functional + code review. Use when the user says things like "I want to build X", "here are my requirements", "turn this doc into a PRD", or "help me design this product".
argument-hint: [path-to-requirements-file-or-free-text-idea]
---

# Product Blueprint (Master Skill)

Turn a raw idea or requirements document into a full set of build-ready documents:
a Product Requirements Document (PRD) and a Technical Design Document (TDD) with diagrams,
grounded in requirements that have been clarified with the user and a tech stack the user
has agreed to.

## Pipeline

Run these phases **in order**. Each phase is implemented by a sub-skill that can also be
invoked standalone by the user. Invoke each sub-skill with the Skill tool and pass forward
the artifacts produced by earlier phases.

| Phase | Sub-skill | Output |
|-------|-----------|--------|
| 1. Intake | `requirements-intake` | `docs/blueprint/01-intake.md` |
| 2. Clarify | `requirements-clarify` | `docs/blueprint/02-clarified-requirements.md` |
| 3. Tech stack | `tech-stack-advisor` | `docs/blueprint/03-tech-stack.md` |
| 3a. Challenge stack | `devils-advocate` | hardened `03-tech-stack.md`, `docs/blueprint/DEVILS-ADVOCATE-stack.md` |
| 4. PRD | `prd-writer` | `docs/blueprint/PRD.md` |
| 5. Technical design | `tech-design` | `docs/blueprint/TECHNICAL-DESIGN.md` |
| 5a. Challenge design | `devils-advocate` | hardened `TECHNICAL-DESIGN.md`, `docs/blueprint/DEVILS-ADVOCATE-design.md` |
| 6. Scaffold (optional) | `scaffold` | runnable project skeleton |
| 7. Implement (optional) | `implement` | code + tests, `docs/blueprint/IMPLEMENTATION-LOG.md` |
| 8. Review (after 7) | `review` | `docs/blueprint/REVIEW.md` |

## Orchestration rules

1. **Accept any input form.** The argument may be a file path (`.pdf`, `.docx`, `.md`, `.txt`)
   or free text describing the idea. If no argument was given, ask the user what they want to
   build (one open question) before starting Phase 1.
2. **Never skip the clarification phase.** Even a detailed requirements doc has gaps. Phase 2
   ends only when the confidence score (defined in `requirements-clarify`) is **≥ 90%** or the
   user explicitly says to proceed with stated assumptions.
3. **Everything interactive goes through AskUserQuestion.** Clarification questions and tech
   stack choices are posed as structured multiple-choice questions with an "Other" escape hatch,
   in batches of at most 4 questions per round.
4. **Checkpoint between phases.** After each phase, give the user a 2–3 sentence summary of the
   artifact just produced and continue. If the user pushes back, revise that artifact before
   moving on — later phases must always consume the latest version.
5. **Propagate context.** Each sub-skill reads the artifacts of prior phases from
   `docs/blueprint/`. Do not re-ask questions already answered; treat prior artifacts as the
   source of truth.
6. **Resume support.** If `docs/blueprint/` already contains artifacts from an earlier run,
   ask the user whether to resume from the first missing/stale phase or start over.

7. **Phase 6 is opt-in.** After the technical design, ask the user (AskUserQuestion) whether
   to scaffold the project now. Only invoke `scaffold` if they say yes — documents are the
   core deliverable; code generation is a bonus step.
8. **Brownfield awareness.** If this run is adding to an existing codebase rather than
   starting from scratch, mention that to whichever sub-skill is running — each of Phases
   1, 3, 4, 5, and 7 knows to consult `repo-index` for what's already implemented instead of
   treating everything as new.
9. **Phases 7–8 are opt-in and paired.** After Phase 6 (or Phase 5 on an existing codebase),
   ask whether to implement the P0 requirements now. If yes, run `implement`, then always
   run `review` on the result. If the review verdict is *Request changes*, offer one
   `implement` → `review` fix round per request; never loop without the user's say-so.
10. **Re-index after code changes.** Whenever Phase 7 or 8 finishes — code ready or committed,
    review done, or a fix round applied — make sure `repo-index` was re-run on the project
    (both sub-skills do this; run `repo-index index` yourself if one was cut short), so later
    lookups never see a stale index.
11. **Challenge before building on it.** Always run `devils-advocate` right after Phase 3 (kind
    `decision`, source `03-tech-stack.md`, report `DEVILS-ADVOCATE-stack.md`) and right after
    Phase 5 (kind `design`, source `TECHNICAL-DESIGN.md`, report `DEVILS-ADVOCATE-design.md`).
    It edits the artifact in place with its mitigations, so the next phase reads the hardened
    version. Don't move on while its gate says *Not hardened*: settle the open questions with
    the user, or record their decision to stop (`convergence_waived_by`). If a 3a mitigation
    changes the stack, the PRD and design are written against the changed stack. On resume,
    treat a challenge report older than its artifact as stale and re-run that step.

## Final deliverable

When the pipeline completes, present the user a short closing summary:

- One-paragraph product description in plain language.
- Links (file paths) to all artifacts (and the scaffolded project directory if Phase 6 ran,
  plus the implementation log and review verdict if Phases 7–8 ran).
- The 3 highest-risk open assumptions carried into the design, plus the devil's-advocate
  verdicts for the stack and the design and any risks the user accepted (with their tripwires).
- Suggested next step (scaffold if skipped, `implement` the first P0 requirements, or address
  the review's open findings).
