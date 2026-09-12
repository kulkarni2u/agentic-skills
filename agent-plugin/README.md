# agentic-skills — portable Agent Plugin

This is `agentic-skills` packaged to the vendor-neutral
[Agent Plugins 1.0.0](https://agent-plugins.org) standard — a `plugin.json`
manifest plus `skills/` — so the same directory works with any compliant
client (Cursor, VS Code/Copilot, Codex CLI's plugin support, or any other
host that implements the spec), not just Claude Code.

For Claude Code specifically, prefer the repo root instead: it's a native
Claude Code plugin (installable via `/plugin install`, manifest at
[`../.claude-plugin/plugin.json`](../.claude-plugin/plugin.json)). Both
packages expose the same eight skills; install whichever matches your
client, or both.

## What's in here

- `plugin.json` — manifest (`$schema`, `name`, `version`, `description`,
  `author`, `homepage`, `repository`, `keywords`).
- `skills/` — symlinks into the repo's [`../skills`](../skills) directory,
  one per skill (`product-blueprint`, `requirements-intake`,
  `requirements-clarify`, `tech-stack-advisor`, `prd-writer`, `tech-design`,
  `scaffold`, `repo-index`). There is one source of truth for skill content;
  this package doesn't fork it.

There is no `mcp.json` here — every skill is pure instructions/prompting,
none register an MCP server.

## Setup

Install `agent-plugin/` with whatever mechanism your client uses to load an
Agent Plugin directory (consult your client's docs — the spec defines the
package format, not a universal install command). Once loaded, a
spec-compliant client should expose all eight skills listed above.

The `repo-index` skill additionally requires the `repo_index` Python
package bundled alongside it:

```bash
cd <path-to-agentic-skills-repo>/skills/repo-index/scripts
pip install -e .
```

## Gaps / known limitations

Read this before assuming the package is more turnkey than it is:

- **Most skill bodies assume Claude Code's own tools.** Six of the eight
  SKILL.md files (`product-blueprint`, `requirements-intake`,
  `requirements-clarify`, `tech-stack-advisor`, `tech-design`, `scaffold`)
  reference Claude Code mechanisms by name — `AskUserQuestion` for
  structured multi-choice prompts, the `Skill` tool for invoking a
  sub-skill, `TodoWrite` for checklists. These aren't part of the Agent
  Plugins spec and won't exist verbatim in every client. A non-Claude host
  should treat those references as illustrative and substitute its own
  equivalent (a plain clarifying question, a direct sub-skill call, a task
  list), not fail outright.
- **`skills/` is symlinks, not copies.** If you copy `agent-plugin/`
  somewhere else without the rest of the repo, the symlinks won't resolve
  — copy `../skills` alongside it, or dereference the links first
  (`cp -rL`).
- **Untested against a real Agent Plugins client.** This package matches
  the shape described in the published spec (manifest keys, naming
  pattern, Agent Skills frontmatter convention) but hasn't been run
  end-to-end inside an actual compliant client yet — do that before
  treating it as verified, not just schema-shaped.
