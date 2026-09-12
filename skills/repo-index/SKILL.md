---
name: repo-index
description: IDE-like code indexer that creates a searchable SQLite index of methods and constants from any repository, and can keep itself fresh automatically via git hooks. Use when asked to index a codebase, to search for where a method/constant is defined across a large repo without opening an IDE, or when another skill needs a fast lookup into an existing codebase instead of manual grep.
argument-hint: [index|search|install-hooks|uninstall-hooks] [repo-path-or-query]
---

# repo-index Skill

IDE-like code indexer that creates a searchable SQLite index of methods, constants, and variables from any repository.

## Overview

The `repo-index` skill indexes Python code structures (methods, constants, variables) from a repository and stores them in a SQLite database at `.repo-index/index.db`. This enables fast grep-like searches across codebases, similar to IDE indexing (VSCode/IntelliJ).

Only `.py` files are scanned; `.git/`, `.repo-index/`, `node_modules/`, `__pycache__/`,
`venv`/`.venv/`, `dist/`, `build/`, and `*.egg-info/` are skipped. Every `index` run rebuilds
the database from scratch, so it's always safe (and expected) to run repeatedly — see
"Keep the index fresh automatically" below to have that happen on its own.

## Installation

```bash
cd <path-to-agentic-skills-plugin-root>/skills/repo-index/scripts
pip install -e .
```

## Quick Start

### Index a repository

```bash
repo-index index /path/to/your-repo
```

This creates `.repo-index/index.db` in the repository root.

### Search the index

```bash
repo-index search "MAX"          # Find constants like MAX_CONNECTIONS
repo-index search "connect"      # Find methods like connect(), disconnect()
repo-index search "query" -t methods  # Search only methods
repo-index search "query" -t constants  # Search only constants
```

### Keep the index fresh automatically (recommended)

Rather than remembering to re-run `index` by hand, install git hooks once per repo so the
index rebuilds itself in the background after anything that can change the working tree —
branch switch, commit, merge/pull, rebase, or push:

```bash
repo-index install-hooks /path/to/your-repo
```

This writes (or appends to, if they already do something else) `post-checkout`,
`post-commit`, `post-merge`, `post-rewrite`, and `pre-push` in that repo's `.git/hooks/`.
Each just re-runs `repo-index index . .repo-index/index.db` in the background so the git
command itself isn't slowed down. Re-running `install-hooks` is a no-op for hooks it
already installed. To remove them: `repo-index uninstall-hooks /path/to/your-repo` — it
strips only the repo-index snippet, leaving any pre-existing custom hook content intact.

When this skill is invoked on a repo for the first time, run `install-hooks` for the user
(mention it in your report) instead of leaving the index to go stale after the next commit.

### Programmatic use (Python agents)

```python
from repo_index.storage import RepoIndex

# Open the index
ri = RepoIndex(".repo-index/index.db")

# Search for methods
results = ri.search("connect", "methods")
for r in results:
    print(f"Method: {r['name']} in {r['file_path']}")

# Search for constants
results = ri.search("MAX", "constants")

# Close when done
ri.close()
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `repo-index index <repo_path>` | Index a repository |
| `repo-index search "<query>"` | Search the index |
| `repo-index search "<query>" -t methods` | Search methods only |
| `repo-index search "<query>" -t constants` | Search constants only |
| `repo-index search "<query>" -t variables` | Search variables only |
| `repo-index install-hooks [repo_path]` | Auto re-index after checkout/commit/merge/rebase/push |
| `repo-index uninstall-hooks [repo_path]` | Remove those git hooks |

## Indexed Structures

The skill extracts and indexes:

- **Methods**: Function definitions (`def function_name()`)
- **Constants**: Uppercase variable assignments (`MAX_CONNECTIONS = 100`)
- **Variables**: (Future expansion - currently empty from parser)

All indexed data stored in SQLite tables: `methods`, `constants`, `variables`, `files`

## File Structure

```
agentic-skills/                # plugin root
└── skills/repo-index/
    ├── SKILL.md
    └── scripts/
        ├── setup.py           # Package configuration
        └── repo_index/
            ├── __init__.py    # Package init
            ├── cli.py         # CLI entry point
            ├── parser.py      # AST-based code parser
            └── storage.py     # SQLite storage

<your-indexed-repo>/
└── .repo-index/          # Created when indexing a repo
    └── index.db          # SQLite database
```

## Search Examples

```bash
# Find constants containing "TIMEOUT"
repo-index search "TIMEOUT"

# Find methods containing "load"
repo-index search "load" -t methods

# Find all indexed items
repo-index search ""  # (empty query returns all)
```

## Use Cases

- Quick code navigation without opening an IDE
- Agents finding where methods/constants are defined across multiple repos
- Refactoring support - find all usages of a method/variable
- Code review - quickly check if a pattern exists in the codebase