---
name: prd-writer
description: Write a complete Product Requirements Document (PRD) from clarified requirements — covering problem, users, user stories, functional and non-functional requirements, scope, success metrics, and release phases. Use standalone when the user asks for a PRD, or as phase 4 of the product-blueprint pipeline.
argument-hint: [path-to-requirements-doc]
---

# PRD Writer

Produce a PRD a product team could execute against without hallway conversations.

## Inputs

Prefer `docs/blueprint/02-clarified-requirements.md` (and `03-tech-stack.md` for
feasibility framing); otherwise the argument. If requirements look thin — no user
definition, no scope boundary, fewer than ~5 concrete requirements — recommend running
`requirements-clarify` first and ask the user whether to do that or write the PRD with
assumptions clearly marked. Do not silently invent substance.

## Writing rules

- Every requirement is **testable**: a reviewer can answer "was this met?" yes or no.
- Requirements say **what**, not **how** — implementation belongs in the technical design.
  (A "Technical context" one-liner referencing the chosen stack is fine.)
- Keep IDs stable: reuse FR-n/NFR-n numbering from the clarified requirements doc.
- Mark anything not user-confirmed as *(assumption)*.
- Target length: 2–6 pages. A PRD nobody reads is a PRD that doesn't exist.

## Template

Write `docs/blueprint/PRD.md`:

```markdown
# PRD: <Product name>
| Status | Draft | Author | Claude + <user> | Date | <date> |

## 1. Overview
One paragraph: the problem, the audience, and what this product does about it.

## 2. Problem & opportunity
What hurts today, for whom, and why now.

## 3. Users & personas
2–4 personas: who they are, their goal, their current workaround.

## 4. User stories & workflows
Primary journeys as "As a <persona>, I want <action> so that <outcome>",
grouped by workflow, priority-tagged (P0/P1/P2).

## 5. Functional requirements
Table: ID | Requirement | Priority (MoSCoW) | Acceptance criteria

## 6. Non-functional requirements
Table: ID | Category | Requirement (with numbers: latency, uptime, scale…)

## 7. Scope
### In scope (v1)   ### Out of scope (explicitly)   ### Later phases

## 8. Success metrics
3–5 measurable indicators with targets and how they'll be measured.

## 9. Release plan
Phases/milestones with the requirement IDs each delivers.

## 10. Risks & open questions
## 11. Appendix: decision log & assumptions
```

## After writing

Summarize for the user: product one-liner, counts of P0 stories and Must requirements,
and any assumptions carried in. Standalone: offer `tech-design` next. In the pipeline:
return control to `product-blueprint`.
