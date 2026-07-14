---
name: product-blueprint
description: Master skill that turns any requirements input (PDF, Word doc, markdown file, or a plain prompt) into a complete product blueprint. It orchestrates requirements intake, an interactive clarification loop until at least 90% confidence, interactive tech-stack selection, PRD generation, and technical design documentation with diagrams. Use when the user says things like "I want to build X", "here are my requirements", "turn this doc into a PRD", or "help me design this product".
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
| 4. PRD | `prd-writer` | `docs/blueprint/PRD.md` |
| 5. Technical design | `tech-design` | `docs/blueprint/TECHNICAL-DESIGN.md` |

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

## Final deliverable

When Phase 5 completes, present the user a short closing summary:

- One-paragraph product description in plain language.
- Links (file paths) to all five artifacts.
- The 3 highest-risk open assumptions carried into the design.
- Suggested next step (e.g., "want me to scaffold the project from the technical design?").
