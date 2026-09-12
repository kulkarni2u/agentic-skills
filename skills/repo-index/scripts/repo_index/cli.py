"""CLI entry point for repo-index."""

import os
import subprocess
import sys

from .storage import RepoIndex
from .parser import parse_source, extract_nodes

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".repo-index", "__pycache__", ".venv", "venv",
    "node_modules", "dist", "build",
}

HOOK_NAMES = ("post-checkout", "post-commit", "post-merge", "post-rewrite", "pre-push")
HOOK_MARKER_BEGIN = "# >>> repo-index auto-index (managed by `repo-index install-hooks`) >>>"
HOOK_MARKER_END = "# <<< repo-index auto-index <<<"
HOOK_SNIPPET = (
    f"{HOOK_MARKER_BEGIN}\n"
    '( cd "$(git rev-parse --show-toplevel)" '
    '&& repo-index index . .repo-index/index.db >/dev/null 2>&1 & )\n'
    f"{HOOK_MARKER_END}\n"
)


def index_repo(repo_path: str, index_path: str = ".repo-index/index.db"):
    """Index an entire repository. Rebuilds from scratch every call, so
    re-running (e.g. from a git hook) never accumulates duplicate rows."""
    repo_index = RepoIndex(index_path)
    repo_index.clear()

    indexed = 0
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [
            d for d in dirs
            if d not in DEFAULT_EXCLUDE_DIRS and not d.endswith(".egg-info")
        ]
        for filename in files:
            if not filename.endswith(".py"):
                continue
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, repo_path)

            try:
                with open(file_path, "r", encoding="utf8", errors="replace") as f:
                    source = f.read()
                repo_index.add_file(rel_path, source)
                indexed += 1
                print(f"Indexed: {rel_path}")
            except Exception as e:
                print(f"Error indexing {rel_path}: {e}", file=sys.stderr)

    methods_count = repo_index.conn.execute("SELECT COUNT(*) FROM methods").fetchone()[0]
    constants_count = repo_index.conn.execute("SELECT COUNT(*) FROM constants").fetchone()[0]
    variables_count = repo_index.conn.execute("SELECT COUNT(*) FROM variables").fetchone()[0]
    print(f"\nIndex complete! {indexed} files, {methods_count} methods, "
          f"{constants_count} constants, "
          f"{variables_count} variables")
    repo_index.close()


def search_index(index_path: str, query: str, search_type: str = "all"):
    """Search the repo index."""
    repo_index = RepoIndex(index_path)

    results = repo_index.search(query, search_type)

    if not results:
        print(f"No results found for '{query}'")
        return

    print(f"Found {len(results)} results for '{query}':\n")
    for r in results:
        print(f"  [{r['type']}] {r['name']} in {r['file_path']} (parent: {r['parent']})")

    repo_index.close()


def _git_hooks_dir(repo_path: str) -> str:
    """Resolve the .git/hooks directory for repo_path, honoring worktrees."""
    try:
        git_dir = subprocess.check_output(
            ["git", "-C", repo_path, "rev-parse", "--git-dir"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"Error: {repo_path!r} is not a git repository", file=sys.stderr)
        sys.exit(1)

    return os.path.join(repo_path, git_dir, "hooks")


def install_hooks(repo_path: str = "."):
    """Install git hooks that re-run `repo-index index` after any operation
    that can change the working tree: checkout/branch switch, commit,
    merge/pull, rebase, and push."""
    hooks_dir = _git_hooks_dir(repo_path)
    os.makedirs(hooks_dir, exist_ok=True)

    for name in HOOK_NAMES:
        hook_path = os.path.join(hooks_dir, name)
        if os.path.exists(hook_path):
            with open(hook_path, "r") as f:
                content = f.read()
            if HOOK_MARKER_BEGIN in content:
                print(f"Skipped {name} (already installed)")
                continue
            with open(hook_path, "a") as f:
                f.write("\n" + HOOK_SNIPPET)
        else:
            with open(hook_path, "w") as f:
                f.write("#!/bin/sh\n" + HOOK_SNIPPET)
            os.chmod(hook_path, 0o755)
        print(f"Installed hook: {name}")

    print(
        "\nrepo-index will now auto-refresh .repo-index/index.db in the background "
        "after checkout, commit, merge/pull, rebase, and push."
    )


def uninstall_hooks(repo_path: str = "."):
    """Remove the repo-index snippet from any hooks install_hooks added it to."""
    hooks_dir = _git_hooks_dir(repo_path)

    for name in HOOK_NAMES:
        hook_path = os.path.join(hooks_dir, name)
        if not os.path.exists(hook_path):
            continue
        with open(hook_path, "r") as f:
            content = f.read()
        if HOOK_MARKER_BEGIN not in content:
            continue
        start = content.index(HOOK_MARKER_BEGIN)
        end = content.index(HOOK_MARKER_END) + len(HOOK_MARKER_END)
        new_content = (content[:start] + content[end:]).rstrip("\n") + "\n"
        if new_content.strip() in ("#!/bin/sh", ""):
            os.remove(hook_path)
            print(f"Removed hook: {name}")
        else:
            with open(hook_path, "w") as f:
                f.write(new_content)
            print(f"Cleaned repo-index snippet from: {name}")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: repo-index <command> [args]")
        print("Commands:")
        print("  index <repo_path>            - Index a repository")
        print("  search <query>               - Search the index")
        print("  search <query> -t <type>     - Search by type (methods|constants|variables|all)")
        print("  install-hooks [repo_path]    - Auto re-index on checkout/commit/merge/rebase/push")
        print("  uninstall-hooks [repo_path]  - Remove those git hooks")
        sys.exit(1)

    command = sys.argv[1]

    if command == "index":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
        index_path = sys.argv[3] if len(sys.argv) > 3 else ".repo-index/index.db"
        index_repo(repo_path, index_path)

    elif command == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        search_type = "all"
        if len(sys.argv) > 4 and sys.argv[3] == "-t":
            search_type = sys.argv[4] if len(sys.argv) > 4 else "all"
        index_path = sys.argv[5] if len(sys.argv) > 5 else ".repo-index/index.db"
        search_index(index_path, query, search_type)

    elif command == "install-hooks":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
        install_hooks(repo_path)

    elif command == "uninstall-hooks":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
        uninstall_hooks(repo_path)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
