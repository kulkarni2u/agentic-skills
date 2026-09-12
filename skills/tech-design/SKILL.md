---
name: tech-design
description: Write a technical design document with Mermaid diagrams — system architecture, component breakdown, data model, API design, sequence flows, deployment, and security — from a PRD or requirements. Use standalone when the user asks for a technical design, architecture doc, or system diagrams, or as phase 5 of the product-blueprint pipeline.
argument-hint: [path-to-prd-or-requirements-doc]
---

# Technical Design Writer

Produce a Technical Design Document (TDD) an engineer could start building from tomorrow.

## Inputs

Prefer `docs/blueprint/PRD.md` and `docs/blueprint/03-tech-stack.md`; fall back to
`02-clarified-requirements.md` or the argument. If no tech stack has been decided, either
run `tech-stack-advisor` (ask the user) or, if the user declines, pick a defensible default
stack and flag it prominently as unratified.

If a significant architectural fork exists that the inputs don't settle (e.g. monolith vs
services, sync vs event-driven, multi-tenant strategy), ask via **AskUserQuestion** before
writing — architecture is expensive to redo.

If designing onto an existing codebase, use `repo-index` to inventory current components,
entry points, and data-layer modules before drawing the architecture diagram — the design
should show what's actually there plus what's new, not a guess at the former.

## Diagram rules

All diagrams are **Mermaid** in fenced ```mermaid blocks so they render on GitHub and in
Claude artifacts. Include the diagrams the system actually needs — typically:

- **System architecture** (`graph TB`): clients, services, data stores, external systems.
- **Sequence diagrams** (`sequenceDiagram`): the 2–4 most important/complex flows
  (e.g. signup+auth, the core domain action, a webhook/async path).
- **ER diagram** (`erDiagram`): entities, key fields, relationships.
- **Deployment diagram** (`graph LR` with subgraphs per environment/network zone).
- **State diagram** (`stateDiagram-v2`) only if a core entity has a meaningful lifecycle.

Keep each diagram under ~15 nodes; split rather than cram. Label every edge.

## Template

Write `docs/blueprint/TECHNICAL-DESIGN.md`:

```markdown
# Technical Design: <Product name>
| Status | Draft | Author | Claude + <user> | Date | <date> | PRD | ./PRD.md |

## 1. Summary & goals
What we're building technically, and the NFR targets that shape the design.

## 2. Architecture overview
Mermaid system architecture diagram + a paragraph per major component:
responsibility, technology (from the stack doc), and why it exists.

## 3. Key flows
Sequence diagram + narrative per critical flow, noting failure handling.

## 4. Data model
ER diagram + table-by-table notes (ownership, indexes, retention, PII flags).

## 5. API design
Style (REST/GraphQL/RPC) and an endpoint/operation table:
Method | Path | Purpose | Auth | Request/Response shape (representative, not exhaustive).

## 6. Security
AuthN/AuthZ model, secrets handling, data protection, threat notes for the top 3 risks.

## 7. Deployment & operations
Deployment diagram, environments, CI/CD outline, observability (logs/metrics/alerts),
backup & recovery.

## 8. Scalability & performance
How the design meets each NFR number; the first bottleneck and its escape plan.

## 9. Alternatives considered
2–3 real forks in the road and why this path won.

## 10. Traceability
Table mapping FR/NFR IDs → the component/section that satisfies them. Every Must
requirement must appear; if one has no home, the design is incomplete — fix it.

## 11. Open questions & follow-ups
```

## After writing

Verify every Mermaid block parses (balanced quotes, no stray `<>` in labels; if `mmdc` or
another checker is available, run it — otherwise re-read each block carefully). Then report:
component count, diagram list, and the top 3 design risks. Standalone: offer to scaffold the
project. In the pipeline: return control to `product-blueprint` for the closing summary.
