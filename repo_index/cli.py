"""CLI entry point for repo-index."""

import sys
import os
from .storage import RepoIndex
from .parser import parse_source, extract_nodes


def index_repo(repo_path: str, index_path: str = ".repo-index/index.db"):
    """Index an entire repository."""
    repo_index = RepoIndex(index_path)

    for root, _dirs, files in os.walk(repo_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, repo_path)

            try:
                with open(file_path, "r", encoding="utf8", errors="replace") as f:
                    source = f.read()
                repo_index.add_file(rel_path, source)
                print(f"Indexed: {rel_path}")
            except Exception as e:
                print(f"Error indexing {rel_path}: {e}", file=sys.stderr)

    methods_count = repo_index.conn.execute("SELECT COUNT(*) FROM methods").fetchone()[0]
    constants_count = repo_index.conn.execute("SELECT COUNT(*) FROM constants").fetchone()[0]
    variables_count = repo_index.conn.execute("SELECT COUNT(*) FROM variables").fetchone()[0]
    print(f"\nIndex complete! {methods_count} methods, "
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


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: repo-index <command> [args]")
        print("Commands:")
        print("  index <repo_path>   - Index a repository")
        print("  search <query>      - Search the index")
        print("  search <query> -t <type>  - Search by type (methods|constants|variables|all)")
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

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
