---
name: requirements-clarify
description: Interactive brainstorming and clarification loop for product requirements. Asks the user structured clarification questions in rounds until at least 90% confident in what they want to build, then writes a clarified requirements document. Use standalone when requirements are vague or contested, or as phase 2 of the product-blueprint pipeline.
argument-hint: [path-to-intake-or-requirements-doc]
---

# Requirements Clarify

Close the gap between what the user said and what they actually want, through an
interactive question loop that ends only at **≥ 90% confidence**.

## Inputs

Prefer `docs/blueprint/01-intake.md` if it exists; otherwise use the argument (file or
free text). If neither exists, invoke the `requirements-intake` skill first.

If this is a brownfield feature, use `repo-index` to check what's already implemented before
asking a question the codebase already answers (e.g. an existing auth module settles part of
"Security & compliance" below without a round-trip to the user).

## The confidence rubric

Score each dimension 0–10, based on whether you could defend a concrete design decision
for it without guessing:

| Dimension | What "10" means |
|---|---|
| Problem & users | You can name the user personas and the pain being solved |
| Core workflows | You can walk the primary user journey end to end |
| Scope boundary | You know what v1 excludes, not just includes |
| Data & integrations | You know what data is stored and which external systems are touched |
| Scale & performance | You know expected user count, data volume, latency tolerance |
| Security & compliance | You know auth model and any regulatory constraints |
| Platform & delivery | You know web/mobile/CLI/API, and hosting expectations |
| Success criteria | You know how the user will judge the product works |

**Confidence % = (sum of scores / 80) × 100.** Recompute after every round and show the
user the number and which dimensions are still weak.

## The question loop

Repeat until confidence ≥ 90% (or the user says "proceed with assumptions"):

1. Pick the **lowest-scoring dimensions** and draft questions that would raise them most.
2. Ask via **AskUserQuestion**: max 4 questions per round, each with 2–4 concrete options
   (put your recommended option first, labeled "(Recommended)") — the tool adds "Other"
   automatically. Options must be real alternatives, not "yes/no/maybe".
3. Fold answers back into the requirement statements. If an answer contradicts an earlier
   one, surface the contradiction and ask which wins.
4. Brainstorm actively, don't just interrogate: when an answer opens a design opportunity or
   risk the user hasn't considered, say so in one or two sentences before the next round.
5. Guardrail: if confidence is still < 90% after **5 rounds**, stop, list the residual
   unknowns as explicit assumptions, and ask the user to either answer them free-form or
   approve the assumptions.

Never pad rounds with questions whose answers wouldn't change the design. If the intake was
already detailed and confidence starts ≥ 90%, do one confirmation round summarizing your
understanding and asking the user to confirm or correct — then finish.

## Output

Write `docs/blueprint/02-clarified-requirements.md`:

```markdown
# Clarified Requirements
- **Confidence**: NN% (dimension scores listed)
- **One-line summary**

## Users & problem
## Functional requirements   (FR-n, each testable, priority MoSCoW: Must/Should/Could/Won't)
## Non-functional requirements   (NFR-n, with concrete numbers where known)
## Scope: v1 vs later
## Assumptions   (numbered, each marked user-approved or inferred)
## Decision log   (Q → user's answer, one line each)
```

Report to the user: final confidence, what changed most from the original input, and any
approved assumptions. Standalone: offer `tech-stack-advisor` next. In the pipeline: return
control to `product-blueprint`.
