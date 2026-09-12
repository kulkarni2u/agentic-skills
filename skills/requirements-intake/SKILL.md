---
name: requirements-intake
description: Ingest product requirements from any source — PDF, Word document, markdown, plain text file, or a free-text user prompt — and normalize them into a structured intake summary that lists what is known, what is ambiguous, and what is missing. Use standalone when the user shares a requirements document and wants it analyzed, or as phase 1 of the product-blueprint pipeline.
argument-hint: [path-to-file-or-free-text-requirements]
---

# Requirements Intake

Normalize raw requirements input into a structured, analyzable summary.

## Step 1 — Acquire the source

Determine the input type from the argument (or from context if invoked by `product-blueprint`):

- **PDF**: use the Read tool (it renders PDF pages). For PDFs over 10 pages read in ranges.
- **Word (.docx)**: extract text with `pandoc <file> -t markdown` if pandoc is available,
  otherwise `python3 -c` with the `zipfile` module to pull `word/document.xml` and strip tags.
- **Markdown / plain text**: Read directly.
- **Free text prompt**: use the user's words verbatim as the source.
- **Nothing provided**: ask the user (one open question via AskUserQuestion with an "Other"
  free-text path) to describe what they want to build or point to a file.

If a file path doesn't exist, list likely matches (Glob) and confirm with the user rather
than guessing.

**Existing codebase?** If the requirements describe adding to a repo that already has code
(not a greenfield idea), invoke the `repo-index` skill to build/refresh `.repo-index/index.db`
and search it for the areas the requirements touch, instead of grepping by hand. Cite what
you find (or don't find) as context under Constraints or Gaps in Step 3.

## Step 2 — Extract and classify

Read the full source before summarizing. Classify every substantive statement into:

1. **Goals** — the problem being solved and for whom.
2. **Functional requirements** — features and behaviors, each restated as a single testable sentence.
3. **Non-functional requirements** — performance, scale, security, compliance, availability, budget.
4. **Constraints** — mandated technologies, deadlines, integrations, team skills.
5. **Explicit non-goals** — anything the source rules out.
6. **Ambiguities** — statements with multiple reasonable interpretations (quote them).
7. **Gaps** — questions the source never answers (users, scale, platform, auth, data, monetization…).

Do not invent requirements. If the source is a one-line idea, most content will land in Gaps —
that is the correct outcome, not a failure.

## Step 3 — Write the intake summary

Write `docs/blueprint/01-intake.md` (create directories as needed) with these sections:

```markdown
# Requirements Intake
- **Source**: <file path or "user prompt">, <date>
- **One-line summary**: <what the user wants to build>

## Goals
## Functional requirements   (numbered FR-1, FR-2, …)
## Non-functional requirements   (numbered NFR-1, …)
## Constraints
## Non-goals
## Ambiguities   (quote + the competing interpretations)
## Gaps   (numbered open questions)
## Initial confidence: NN%   (per the rubric in the requirements-clarify skill)
```

## Step 4 — Report

Tell the user: the one-line summary, counts per section, the top 3 ambiguities/gaps, and the
initial confidence score. If invoked standalone, offer to continue with `requirements-clarify`;
if invoked by `product-blueprint`, return control to the pipeline.
