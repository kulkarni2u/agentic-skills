# agentic-skills

A Claude Code plugin marketplace with skills for turning raw product ideas into
build-ready documentation, and for indexing a codebase for fast lookup.

## Installation

This repo is both a marketplace and the plugin it hosts. From within Claude Code:

```
/plugin marketplace add kulkarni2u/agentic-skills
/plugin install agentic-skills@agentic-skills
```

Once installed, every skill below is available, namespaced as
`/agentic-skills:<skill-name>` (e.g. `/agentic-skills:product-blueprint`).

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
| **`/agentic-skills:product-blueprint`** | Master pipeline: idea/doc in → PRD + technical design out | all of the below |
| `/agentic-skills:requirements-intake` | Ingests requirements from PDF, Word, markdown, text, or a plain prompt; classifies knowns, ambiguities, and gaps | `docs/blueprint/01-intake.md` |
| `/agentic-skills:requirements-clarify` | Interactive brainstorming loop — asks structured clarification questions in rounds until ≥ 90% confidence (scored on an 8-dimension rubric) | `docs/blueprint/02-clarified-requirements.md` |
| `/agentic-skills:tech-stack-advisor` | Recommends a tech stack via interactive questions (team skills, ops appetite, budget), layer by layer with trade-offs | `docs/blueprint/03-tech-stack.md` |
| `/agentic-skills:prd-writer` | Writes a testable, prioritized Product Requirements Document | `docs/blueprint/PRD.md` |
| `/agentic-skills:tech-design` | Writes a Technical Design Document with Mermaid diagrams (architecture, sequences, ER, deployment) and FR/NFR traceability | `docs/blueprint/TECHNICAL-DESIGN.md` |
| `/agentic-skills:scaffold` | Generates a runnable project skeleton from the technical design — structure, tooling, model & API stubs, tests, CI — and verifies it installs, lints, and tests green | project directory |

### Usage

```
/agentic-skills:product-blueprint requirements.pdf
/agentic-skills:product-blueprint "a mobile app that tracks my houseplants' watering schedules"
/agentic-skills:requirements-clarify docs/spec.md      # just run the clarification loop
/agentic-skills:tech-stack-advisor                     # just get stack advice
/agentic-skills:scaffold docs/blueprint/TECHNICAL-DESIGN.md ./my-app   # just scaffold the project
```

## repo-index skill

`/agentic-skills:repo-index` indexes a repository's methods and constants into a searchable
SQLite database, similar to IDE indexing. Requires the bundled `repo_index` Python package
(`pip install -e .` from `skills/repo-index/scripts/` — see `skills/repo-index/SKILL.md` for
details).

## Portable Agent Plugin (any compliant client)

Not on Claude Code? [`agent-plugin/`](agent-plugin/) packages these same eight skills to the
vendor-neutral [Agent Plugins 1.0.0](https://agent-plugins.org) standard (`plugin.json` +
`skills/`) instead of a client-specific format. See
[`agent-plugin/README.md`](agent-plugin/README.md) for setup and a list of known gaps.
