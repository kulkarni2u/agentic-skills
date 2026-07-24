# agentic-skills

A collection of Claude Code skills for turning raw product ideas into build-ready documentation.

## Product Blueprint suite

One master skill orchestrates six sub-skills. Every sub-skill is also independently
user-invocable — run just the piece you need.

```mermaid
graph LR
    A[/product-blueprint/] --> B[/requirements-intake/]
    B --> C[/requirements-clarify/]
    C --> D[/tech-stack-advisor/]
    D --> E[/prd-writer/]
    E --> F[/tech-design/]
    F -. optional .-> G[/scaffold/]
```

| Skill | What it does | Output |
|---|---|---|
| **`/product-blueprint`** | Master pipeline: idea/doc in → PRD + technical design out | all of the below |
| `/requirements-intake` | Ingests requirements from PDF, Word, markdown, text, or a plain prompt; classifies knowns, ambiguities, and gaps | `docs/blueprint/01-intake.md` |
| `/requirements-clarify` | Interactive brainstorming loop — asks structured clarification questions in rounds until ≥ 90% confidence (scored on an 8-dimension rubric) | `docs/blueprint/02-clarified-requirements.md` |
| `/tech-stack-advisor` | Recommends a tech stack via interactive questions (team skills, ops appetite, budget), layer by layer with trade-offs | `docs/blueprint/03-tech-stack.md` |
| `/prd-writer` | Writes a testable, prioritized Product Requirements Document | `docs/blueprint/PRD.md` |
| `/tech-design` | Writes a Technical Design Document with Mermaid diagrams (architecture, sequences, ER, deployment) and FR/NFR traceability | `docs/blueprint/TECHNICAL-DESIGN.md` |
| `/scaffold` | Generates a runnable project skeleton from the technical design — structure, tooling, model & API stubs, tests, CI — and verifies it installs, lints, and tests green | project directory |

### Usage

```
/product-blueprint requirements.pdf
/product-blueprint "a mobile app that tracks my houseplants' watering schedules"
/requirements-clarify docs/spec.md      # just run the clarification loop
/tech-stack-advisor                     # just get stack advice
/scaffold docs/blueprint/TECHNICAL-DESIGN.md ./my-app   # just scaffold the project
```

### Installation

- **This repo**: skills live in `.claude/skills/` and load automatically when you open the
  repo in Claude Code.
- **Any project**: copy the skill folders into that project's `.claude/skills/`.
- **Globally**: copy them into `~/.claude/skills/` to use in every project.
