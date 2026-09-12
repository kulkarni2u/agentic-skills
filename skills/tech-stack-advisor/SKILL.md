---
name: tech-stack-advisor
description: Recommend a technology stack through interactive questions posed to the user. Weighs requirements, team skills, scale, and constraints, presents options per layer with trade-offs, and records the agreed stack with rationale. Use standalone when the user asks "what stack should I use", or as phase 3 of the product-blueprint pipeline.
argument-hint: [path-to-requirements-doc-or-project-description]
---

# Tech Stack Advisor

Arrive at a tech stack the user actually agrees with — through questions, not decree.

## Inputs

Prefer `docs/blueprint/02-clarified-requirements.md`, then `01-intake.md`, then the argument.
With no input at all, first ask what they're building (one question), then proceed.

If the target is an existing repo, use `repo-index` to see what's already in use (framework
entry points, ORM/config modules, existing constants naming a queue or cache) before treating
any layer as an open choice — a layer already committed to in code is "constrained", not a
question for Step 1 or Step 3.

## Step 1 — Context questions

Requirements rarely capture the human factors that should drive stack choice. Ask via
**AskUserQuestion** (one round, up to 4 questions), skipping anything already answered:

- **Team experience** — languages/frameworks the team already knows (multiSelect).
- **Operational appetite** — managed/serverless vs self-hosted vs Kubernetes-level control.
- **Budget posture** — free/OSS-only, modest SaaS spend, or cost-insensitive.
- **Existing estate** — clouds, databases, or systems this must live alongside.

## Step 2 — Derive the decision drivers

From requirements + answers, write down (internally) the 3–5 drivers that dominate the
choice — e.g. "solo dev, ship in 6 weeks", "10M rows/day ingest", "HIPAA", "team is
Python-only". Every recommendation must trace back to a driver.

## Step 3 — Interactive selection per layer

For each **relevant** layer, present 2–4 candidate options via **AskUserQuestion**
(batch up to 4 layers per round; put your recommendation first labeled "(Recommended)";
use the option description to state the trade-off in one sentence):

1. Language & runtime
2. Backend framework
3. Frontend framework (skip for API-only/CLI products)
4. Database & data layer
5. Auth
6. Hosting & infrastructure
7. Notable third-party services (payments, email, search, queues, AI/LLM APIs…)

Rules:
- Skip layers the requirements make irrelevant; never ask for the sake of asking.
- Honor hard constraints from requirements silently (if the doc mandates Postgres, don't
  re-open it — record it as "constrained").
- Prefer boring, well-documented technology unless a driver demands otherwise.
- If the user picks an option you consider a mistake given the drivers, say why in two
  sentences and ask once to confirm — then respect their choice.

## Step 4 — Output

Write `docs/blueprint/03-tech-stack.md`:

```markdown
# Tech Stack
- **Decision drivers**: bullet list

| Layer | Choice | Why (tied to a driver) | Alternatives considered |
|---|---|---|---|

## Risks & mitigations   (e.g. single-vendor lock-in, team ramp-up)
## Estimated monthly cost at launch scale   (rough order of magnitude)
```

Report the chosen stack in one short paragraph. Standalone: offer `prd-writer` or
`tech-design` next. In the pipeline: return control to `product-blueprint`.
