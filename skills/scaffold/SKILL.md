---
name: scaffold
description: Generate a runnable project skeleton from a technical design document — directory structure, tooling config, data model stubs, API route stubs, CI pipeline, and a development README — using the tech stack the user agreed to. Use standalone when the user asks to scaffold, bootstrap, or set up a project, or as phase 6 of the product-blueprint pipeline.
argument-hint: [path-to-technical-design-doc] [target-directory]
---

# Scaffold

Turn the technical design into a compiling, runnable project skeleton — structure and
stubs, not the product itself.

## Inputs

Prefer `docs/blueprint/TECHNICAL-DESIGN.md` and `docs/blueprint/03-tech-stack.md`;
otherwise the argument. If there is no design doc and no stack decision, ask the user
whether to run `tech-design`/`tech-stack-advisor` first or scaffold from a stack they
name on the spot — don't pick a stack silently.

**Target directory**: second argument if given; otherwise ask via AskUserQuestion —
offer (a) a new subdirectory named after the product, (b) the current repo root
(only if it isn't already a project), or (c) a path they type. Never overwrite an
existing non-empty directory without explicit confirmation. If the target is an existing
non-empty Python project, use `repo-index` to inventory what's already defined there before
generating stubs, so you don't propose module/function names that collide with real code.

## What to generate

Derive everything from the design doc — components become modules, ER entities become
model stubs, the API table becomes route stubs. Generate:

1. **Project structure** — the directory layout implied by the architecture (one module
   per component; monorepo layout only if the design says multiple deployables).
2. **Tooling** — package manifest(s), lockfile via the real installer, formatter + linter
   config, `.gitignore`, `.env.example` listing every secret/config the design mentions
   (never real values).
3. **Data layer** — schema/migration files or ORM models matching the ER diagram: fields,
   types, relations, and indexes called out in the design.
4. **API stubs** — one handler per endpoint in the design's API table, returning
   501/TODO with the request/response types defined, plus auth middleware wired but
   permissive in dev.
5. **Tests** — the test framework configured with one passing smoke test per component,
   so `test` runs green from the first commit.
6. **CI** — a GitHub Actions workflow running install → lint → test on push/PR.
7. **README.md** — how to install, configure, run, and test; link back to the blueprint
   docs; a checklist of the P0 requirements as unimplemented TODOs with their FR IDs.

Prefer official generators (`npm create vite`, `django-admin startproject`, `cargo new`,
etc.) and then adapt, rather than hand-writing boilerplate the ecosystem maintains.

## Verify before reporting

The skeleton must actually work. Run: dependency install, lint, test suite, and — where
feasible — start the dev server or build once and confirm it comes up (then stop it).
Fix failures; do not hand over a red skeleton. If sandbox/network limits block a step,
say exactly which step and why instead of claiming success.

## Report

If the generated (or target) project is Python, initialize `git` in it if it isn't already
a repo, then invoke `repo-index` to build its index and install the auto-index git hooks
(`install-hooks`) — so the codebase is searchable and stays that way from the first commit.

Tell the user: the directory tree (top two levels), the commands to run it, what is
stubbed vs working, and the first 3 FR IDs you'd implement next. Standalone: offer to
start implementing the P0 requirements. In the pipeline: return control to
`product-blueprint` for the closing summary.
