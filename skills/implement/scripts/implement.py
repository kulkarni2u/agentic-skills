#!/usr/bin/env python3
"""Deterministic helpers for the implement skill: requirements, toolchain, checks, log, index."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, Sequence


LOG_PATH = "docs/blueprint/IMPLEMENTATION-LOG.md"
PRD_PATH = "docs/blueprint/PRD.md"
LOG_COLUMNS = ("FR", "Approach", "Tests (file::name)", "Code", "Status", "Notes / assumptions")
LOG_KEYS = ("id", "approach", "tests", "code", "status", "notes")
STATUSES = ("done", "partial", "blocked")
APPROACHES = ("tdd", "bdd", "ddd")
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".repo-index", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", "target", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "vendor",
}
DOC_SUFFIXES = {".md", ".rst", ".txt", ".adoc"}
REQ_ID = re.compile(r"\b(?:FR|NFR)-\d+(?:\.\d+)?\b")
OUTPUT_TAIL_LINES = 40

RULE_FILES = (
    "CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
    "STYLEGUIDE.md", "STYLE.md", ".editorconfig", ".eslintrc", ".eslintrc.js", ".eslintrc.json",
    ".eslintrc.cjs", "eslint.config.js", "eslint.config.mjs", ".prettierrc", ".prettierrc.json",
    "ruff.toml", ".ruff.toml", ".flake8", "mypy.ini", "pyrightconfig.json", "tsconfig.json",
    ".golangci.yml", ".golangci.yaml", "rustfmt.toml", "clippy.toml", ".rubocop.yml", "checkstyle.xml",
)
BDD_TOOLS = {
    "behave": "behave", "pytest-bdd": "pytest-bdd", "@cucumber/cucumber": "cucumber-js",
    "cucumber": "cucumber", "jest-cucumber": "jest-cucumber", "SpecFlow": "specflow",
    "Reqnroll": "reqnroll", "godog": "godog",
}
DEPENDENCY_FILES = (
    "pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "requirements-dev.txt",
    "package.json", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile",
)

# Each rubric row is one signal; an approach scores one point per row that matches.
APPROACH_SIGNALS: dict[str, dict[str, str]] = {
    "tdd": {
        "pure-logic": r"\b(calculat|comput|pars|convert|validat|algorithm|sort|rank|scor|round|"
                      r"encod|decod|hash|checksum|transform|formula|serializ)\w*",
        "bug-fix": r"\b(bug|fix|regression|crash|incorrect|wrong|broken)\w*",
    },
    "bdd": {
        "user-workflow": r"\b(as an? \w+|user|click|page|screen|form|sign[- ]?up|log[- ]?in|"
                         r"checkout|onboard\w*|notif\w*|e-?mail|ui|cli|command)\b",
        "api-endpoint": r"\b(endpoint|api|request|response|http|webhook|rest|graphql|"
                        r"status code|(get|post|put|patch|delete) /)\b",
        "scenario-phrasing": r"\bgiven\b.*\bwhen\b|\bwhen\b.*\bthen\b",
    },
    "ddd": {
        "business-rules": r"\b(must not|cannot|only if|unless|invariant|policy|rule|constraint|"
                          r"at most|at least|eligib\w*|quota|limit)\b",
        "lifecycle": r"\b(state machine|state transition|transition\w*|lifecycle|"
                     r"(approv|reject|cancel|expir|archiv|publish|refund|suspend)\w*|pending|draft)\b",
        "domain-language": r"\b(aggregate|entity|value object|domain event|bounded context|ledger|"
                           r"ubiquitous)\b",
    },
}
TIE_ORDER = ("ddd", "bdd", "tdd")

STUB_PATTERNS = {
    "todo": re.compile(r"\b(TODO|FIXME|XXX|HACK)\b"),
    "not-implemented": re.compile(
        r"NotImplemented(Error|Exception)?\b|todo!\(|unimplemented!\(|not implemented", re.I
    ),
    "http-501": re.compile(r"\b501\b"),
    "skipped-test": re.compile(
        r"@(pytest\.mark\.)?(skip|xfail)\b|unittest\.skip|\b(it|describe|test)\.(skip|todo)\(|"
        r"\bx(it|describe)\(|t\.Skip\(|#\[ignore\]|@Disabled\b|@Ignore\b|\[Ignore\]"
    ),
}
EMPTY_BODY = re.compile(r"^\s*(pass|\.\.\.)\s*$")
DEF_LINE = re.compile(r"^\s*(async\s+)?def\s.*:\s*$")


# ---------------------------------------------------------------- requirements

def _split_row(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [cell.strip().replace("\\|", "|") for cell in cells]


def _tables(text: str) -> Iterable[tuple[list[str], list[list[str]]]]:
    lines = text.splitlines()
    index = 0
    while index < len(lines) - 1:
        if lines[index].lstrip().startswith("|") and re.match(r"^\s*\|?\s*:?-{3,}", lines[index + 1]):
            header = _split_row(lines[index])
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                rows.append(_split_row(lines[index]))
                index += 1
            yield header, rows
        else:
            index += 1


def _column(header: Sequence[str], *names: str) -> int | None:
    for position, title in enumerate(header):
        if any(name in title.lower() for name in names):
            return position
    return None


def split_criteria(text: str) -> list[str]:
    parts = re.split(r"<br\s*/?>|;|\s(?=\d+[.)]\s)|\s[-•]\s", text)
    return [part.strip(" .") for part in parts if part.strip(" .")]


def parse_requirements(text: str) -> list[dict[str, Any]]:
    """Extract FR/NFR rows from every markdown table that has an ID column."""
    found: dict[str, dict[str, Any]] = {}
    for header, rows in _tables(text):
        id_col = _column(header, "id")
        if id_col is None:
            continue
        text_col = _column(header, "requirement", "description", "story")
        priority_col = _column(header, "priority", "moscow")
        criteria_col = _column(header, "acceptance")
        category_col = _column(header, "category")
        for row in rows:
            if id_col >= len(row) or not REQ_ID.fullmatch(row[id_col]):
                continue

            def cell(col: int | None) -> str:
                return row[col] if col is not None and col < len(row) else ""

            criteria = cell(criteria_col)
            found[row[id_col]] = {
                "id": row[id_col],
                "requirement": cell(text_col),
                "priority": cell(priority_col),
                "category": cell(category_col),
                "acceptance": split_criteria(criteria) if criteria else [],
                # NFR tables usually carry no priority column; treat those NFRs as binding.
                "must": is_must(cell(priority_col)) or (row[id_col].startswith("NFR") and not cell(priority_col)),
            }
    return list(found.values())


def is_must(priority: str) -> bool:
    value = priority.strip().lower()
    return value.startswith("must") or value in {"m", "p0"}


def select_requirements(reqs: list[dict[str, Any]], ids: str | None, must_only: bool) -> list[dict[str, Any]]:
    wanted = {item.strip() for item in ids.split(",")} if ids else None
    return [r for r in reqs if (wanted is None or r["id"] in wanted) and (not must_only or r["must"])]


# ---------------------------------------------------------------- approach

def score_approach(text: str) -> dict[str, Any]:
    lowered = text.lower()
    signals = {
        approach: sorted(name for name, pattern in rows.items() if re.search(pattern, lowered))
        for approach, rows in APPROACH_SIGNALS.items()
    }
    scores = {approach: len(names) for approach, names in signals.items()}
    best = max(scores.values())
    if best == 0:
        primary = "tdd"
    else:
        primary = next(approach for approach in TIE_ORDER if scores[approach] == best)
    ranked = sorted(scores.values(), reverse=True)
    return {
        "primary": primary,
        "scores": scores,
        "signals": signals,
        # A tie between two signalled approaches means the rubric cannot decide; ask the user.
        "split": ranked[1] > 0 and ranked[0] == ranked[1],
    }


# ---------------------------------------------------------------- toolchain

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def walk_files(root: Path, suffixes: set[str] | None = None) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        for name in filenames:
            path = Path(dirpath) / name
            if suffixes is None or path.suffix in suffixes:
                yield path


def _make_targets(root: Path) -> set[str]:
    return set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", _read(root / "Makefile"), re.M))


def _node_commands(root: Path) -> dict[str, str]:
    try:
        scripts = json.loads(_read(root / "package.json") or "{}").get("scripts", {})
    except json.JSONDecodeError:
        return {}
    runner = next(
        (tool for lock, tool in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lockb", "bun"))
         if (root / lock).exists()),
        "npm",
    )
    commands: dict[str, str] = {}
    if "test" in scripts and "no test specified" not in scripts["test"]:
        commands["test"] = f"{runner} test"
    if "lint" in scripts:
        commands["lint"] = f"{runner} run lint"
    for name in ("typecheck", "type-check", "types", "tsc"):
        if name in scripts:
            commands["typecheck"] = f"{runner} run {name}"
            break
    if "typecheck" not in commands and (root / "tsconfig.json").exists():
        commands["typecheck"] = "npx tsc --noEmit"
    return commands


def _python_commands(root: Path) -> dict[str, str]:
    config = "\n".join(_read(root / name) for name in ("pyproject.toml", "setup.cfg", "tox.ini"))
    test_files = [p for p in walk_files(root, {".py"}) if p.name.startswith("test_") or p.name.endswith("_test.py")]
    if not test_files and not (root / "pyproject.toml").exists() and not (root / "setup.py").exists():
        return {}
    commands: dict[str, str] = {}
    configured = "pytest" in config or (root / "pytest.ini").exists() or (root / "conftest.py").exists()
    if configured or shutil.which("pytest"):
        # The pytest entry point carries its own interpreter, which may not be the python3 on PATH.
        commands["test"] = "pytest -q" if shutil.which("pytest") else "python3 -m pytest -q"
    elif test_files:
        dirs = sorted({str(p.parent.relative_to(root)) for p in test_files})
        commands["test"] = " && ".join(f"python3 -m unittest discover -s {d} -t {d}" for d in dirs)
    if "[tool.ruff" in config or (root / "ruff.toml").exists() or (root / ".ruff.toml").exists():
        commands["lint"] = "ruff check ."
    elif (root / ".flake8").exists() or "[flake8]" in config:
        commands["lint"] = "flake8"
    if "[tool.mypy" in config or "[mypy" in config or (root / "mypy.ini").exists():
        commands["typecheck"] = "mypy ."
    elif (root / "pyrightconfig.json").exists() or "[tool.pyright" in config:
        commands["typecheck"] = "pyright"
    return commands


def _other_commands(root: Path) -> dict[str, str]:
    if (root / "Cargo.toml").exists():
        return {"test": "cargo test", "lint": "cargo clippy --all-targets -- -D warnings",
                "typecheck": "cargo check --all-targets"}
    if (root / "go.mod").exists():
        lint = "golangci-lint run" if any(root.glob(".golangci.*")) else "go vet ./..."
        return {"test": "go test ./...", "lint": lint, "typecheck": "go build ./..."}
    if (root / "pom.xml").exists():
        return {"test": "mvn -q test"}
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        return {"test": "./gradlew test" if (root / "gradlew").exists() else "gradle test"}
    return {}


def detect(root: Path) -> dict[str, Any]:
    """Find repo rules and the repo-native test/lint/typecheck commands, most specific first."""
    commands: dict[str, str] = {}
    targets = _make_targets(root)
    make_names = {"test": ("test",), "lint": ("lint",), "typecheck": ("typecheck", "type-check", "types")}
    for kind, names in make_names.items():
        for name in names:
            if name in targets:
                commands[kind] = f"make {name}"
                break
    for source in (_node_commands, _python_commands, _other_commands):
        for kind, command in source(root).items():
            commands.setdefault(kind, command)

    deps = "\n".join(_read(root / name) for name in DEPENDENCY_FILES)
    deps += "".join("\n" + _read(p) for p in root.glob("*.csproj"))
    bdd = sorted({tool for marker, tool in BDD_TOOLS.items() if re.search(rf"(?<![\w/@-]){re.escape(marker)}\b", deps)})
    rules = [name for name in RULE_FILES if (root / name).exists()]
    rules += sorted(
        str(p.relative_to(root)) for p in walk_files(root) if p.name in {"CLAUDE.md", "AGENTS.md"}
        and str(p.relative_to(root)) not in rules
    )
    return {
        "root": str(root),
        "commands": commands,
        "rules": rules,
        "ci": sorted(str(p.relative_to(root)) for p in root.glob(".github/workflows/*.y*ml")),
        "bdd_tools": bdd,
        "feature_files": any(walk_files(root, {".feature"})),
        "python": any(walk_files(root, {".py"})),
    }


def run_checks(root: Path, only: Sequence[str] | None, timeout: int) -> dict[str, Any]:
    commands = detect(root)["commands"]
    results = []
    for kind in ("test", "lint", "typecheck"):
        if kind not in commands or (only and kind not in only):
            continue
        started = time.monotonic()
        try:
            proc = subprocess.run(commands[kind], shell=True, cwd=root, capture_output=True,
                                  text=True, timeout=timeout)
            code, output = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as exc:
            # TimeoutExpired carries bytes even when text=True was requested.
            partial = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
            code, output = 124, f"timed out after {timeout}s\n{partial}"
        results.append({
            "kind": kind,
            "command": commands[kind],
            "exit_code": code,
            "passed": code == 0,
            "duration_s": round(time.monotonic() - started, 2),
            "tail": "\n".join(str(output).splitlines()[-OUTPUT_TAIL_LINES:]),
        })
    return {"passed": bool(results) and all(r["passed"] for r in results), "results": results}


# ---------------------------------------------------------------- stubs

def added_lines(diff_text: str) -> dict[str, list[tuple[int, str]]]:
    """Map each file in a unified diff to its added (line number, text) pairs."""
    files: dict[str, list[tuple[int, str]]] = {}
    path: str | None = None
    line_no = 0
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            path = None if target == "/dev/null" else re.sub(r"^b/", "", target)
            if path:
                files.setdefault(path, [])
        elif line.startswith("@@"):
            match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", line)
            line_no = int(match.group(1)) if match else 0
        elif path is not None and line.startswith("+"):
            files[path].append((line_no, line[1:]))
            line_no += 1
        elif path is not None and not line.startswith("-") and not line.startswith("\\"):
            line_no += 1
    return files


def scan_lines(path: str, lines: Sequence[tuple[int, str]], previous: dict[int, str]) -> list[dict[str, Any]]:
    hits = []
    for line_no, text in lines:
        for kind, pattern in STUB_PATTERNS.items():
            if pattern.search(text):
                hits.append({"path": path, "line": line_no, "kind": kind, "text": text.strip()[:160]})
        if EMPTY_BODY.match(text) and DEF_LINE.match(previous.get(line_no - 1, "")):
            hits.append({"path": path, "line": line_no, "kind": "empty-body", "text": text.strip()})
    return hits


def scan_stubs(paths: Sequence[str], diff_text: str | None) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if diff_text is not None:
        for path, lines in added_lines(diff_text).items():
            if Path(path).suffix not in DOC_SUFFIXES:
                context = dict(lines)
                hits += scan_lines(path, lines, context)
        return hits
    for raw in paths:
        base = Path(raw)
        for file in ([base] if base.is_file() else walk_files(base)):
            if file.suffix in DOC_SUFFIXES or file.stat().st_size > 1_000_000:
                continue
            numbered = list(enumerate(_read(file).splitlines(), start=1))
            hits += scan_lines(str(file), numbered, dict(numbered))
    return hits


# ---------------------------------------------------------------- log

def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def read_log(path: Path) -> list[dict[str, str]]:
    for header, rows in _tables(_read(path)):
        if header and header[0].strip().upper() == "FR":
            return [dict(zip(LOG_KEYS, row + [""] * (len(LOG_KEYS) - len(row)))) for row in rows]
    return []


def write_log(path: Path, rows: list[dict[str, str]]) -> None:
    table = ["| " + " | ".join(LOG_COLUMNS) + " |", "|" + "---|" * len(LOG_COLUMNS)]
    table += ["| " + " | ".join(_escape(row.get(key, "")) for key in LOG_KEYS) + " |" for row in rows]
    existing = _read(path)
    if not existing:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Implementation Log\n\n" + "\n".join(table) + "\n", encoding="utf-8")
        return
    lines = existing.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"^\|\s*FR\s*\|", line)), None)
    if start is None:
        path.write_text(existing.rstrip("\n") + "\n\n" + "\n".join(table) + "\n", encoding="utf-8")
        return
    end = start
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    path.write_text("\n".join(lines[:start] + table + lines[end:]) + "\n", encoding="utf-8")


def tick_checklist(readme: Path, req_id: str) -> int:
    text = _read(readme)
    pattern = re.compile(rf"^(\s*[-*]\s+)\[ \](?=.*\b{re.escape(req_id)}\b)", re.M)
    updated, count = pattern.subn(r"\1[x]", text)
    if count:
        readme.write_text(updated, encoding="utf-8")
    return count


def upsert_log(path: Path, req_id: str, fields: dict[str, str | None], readme: Path | None) -> dict[str, Any]:
    if fields.get("status") and fields["status"] not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    approach = fields.get("approach")
    if approach and not set(re.split(r"[+/, ]+", approach.lower())) <= set(APPROACHES):
        raise ValueError(f"approach must be built from {', '.join(APPROACHES)} (e.g. ddd+bdd)")
    rows = read_log(path)
    row = next((r for r in rows if r["id"] == req_id), None)
    if row is None:
        row = {key: "" for key in LOG_KEYS}
        row["id"] = req_id
        rows.append(row)
    row.update({key: value for key, value in fields.items() if value is not None})
    write_log(path, rows)
    ticked = tick_checklist(readme, req_id) if readme and row["status"] == "done" and readme.exists() else 0
    return {"row": row, "ticked": ticked}


# ---------------------------------------------------------------- index

def reindex(root: Path) -> tuple[int, dict[str, Any]]:
    if not any(walk_files(root, {".py"})):
        return 0, {"status": "skipped", "reason": "no .py files; repo-index only indexes Python"}
    exe = shutil.which("repo-index")
    if exe is None:
        package = Path(__file__).resolve().parents[2] / "repo-index" / "scripts"
        return 3, {"status": "unavailable", "fix": f"pip install -e {package}"}
    proc = subprocess.run([exe, "index", str(root), str(root / ".repo-index" / "index.db")],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return 1, {"status": "failed", "output": (proc.stdout + proc.stderr)[-2000:]}
    hooks = "no-git"
    hook_file = root / ".git" / "hooks" / "post-commit"
    if (root / ".git").is_dir():
        if "repo-index auto-index" in _read(hook_file):
            hooks = "present"
        else:
            subprocess.run([exe, "install-hooks", str(root)], capture_output=True, text=True, check=False)
            hooks = "installed"
    return 0, {"status": "indexed", "hooks": hooks, "output": proc.stdout.strip()[-500:]}


# ---------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic helpers for the implement skill.")
    sub = parser.add_subparsers(dest="command", required=True)

    req = sub.add_parser("requirements", help="extract FR/NFR rows and acceptance criteria as JSON")
    req.add_argument("--prd", default=PRD_PATH)
    req.add_argument("--ids", help="comma-separated IDs to keep")
    req.add_argument("--must", action="store_true", help="only Must / P0 requirements")

    approach = sub.add_parser("approach", help="score TDD/BDD/DDD signals for a requirement")
    approach.add_argument("text", nargs="?", help="requirement text (default: --id from the PRD)")
    approach.add_argument("--id", dest="req_id")
    approach.add_argument("--prd", default=PRD_PATH)

    det = sub.add_parser("detect", help="repo rules, CI files, test/lint/typecheck commands, BDD tooling")
    det.add_argument("root", nargs="?", default=".")

    check = sub.add_parser("check", help="run the detected test/lint/typecheck commands")
    check.add_argument("root", nargs="?", default=".")
    check.add_argument("--only", help="comma-separated subset of test,lint,typecheck")
    check.add_argument("--timeout", type=int, default=900)

    stubs = sub.add_parser("stubs", help="find TODO/501/not-implemented/skipped-test markers")
    stubs.add_argument("paths", nargs="*", default=[])
    stubs.add_argument("--diff", help="scan only lines added in this unified diff (- for stdin)")

    log = sub.add_parser("log", help="read or upsert IMPLEMENTATION-LOG.md rows")
    log.add_argument("action", choices=("show", "set"))
    log.add_argument("req_id", nargs="?")
    log.add_argument("--log", default=LOG_PATH)
    log.add_argument("--approach")
    log.add_argument("--tests")
    log.add_argument("--code")
    log.add_argument("--status")
    log.add_argument("--notes")
    log.add_argument("--readme", default="README.md", help="checklist to tick when status is done")

    idx = sub.add_parser("reindex", help="re-run repo-index in the foreground; install hooks if missing")
    idx.add_argument("root", nargs="?", default=".")
    return parser


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "requirements":
            reqs = parse_requirements(_read(Path(args.prd)))
            if not reqs:
                raise ValueError(f"no FR/NFR table rows found in {args.prd}")
            _emit({"requirements": select_requirements(reqs, args.ids, args.must)})
        elif args.command == "approach":
            text = args.text
            if text is None:
                if not args.req_id:
                    raise ValueError("pass requirement text or --id")
                match = select_requirements(parse_requirements(_read(Path(args.prd))), args.req_id, False)
                if not match:
                    raise ValueError(f"{args.req_id} not found in {args.prd}")
                text = " ".join([match[0]["requirement"], *match[0]["acceptance"]])
            _emit(score_approach(text))
        elif args.command == "detect":
            _emit(detect(Path(args.root).resolve()))
        elif args.command == "check":
            only = args.only.split(",") if args.only else None
            result = run_checks(Path(args.root).resolve(), only, args.timeout)
            _emit(result)
            if not result["results"]:
                return 2
            return 0 if result["passed"] else 1
        elif args.command == "stubs":
            diff = None
            if args.diff:
                diff = sys.stdin.read() if args.diff == "-" else _read(Path(args.diff))
            elif not args.paths:
                raise ValueError("pass paths to scan or --diff")
            hits = scan_stubs(args.paths, diff)
            _emit({"count": len(hits), "hits": hits})
        elif args.command == "log":
            path = Path(args.log)
            if args.action == "show":
                _emit({"rows": read_log(path)})
            else:
                if not args.req_id:
                    raise ValueError("log set needs a requirement ID")
                fields = {"approach": args.approach, "tests": args.tests, "code": args.code,
                          "status": args.status, "notes": args.notes}
                _emit(upsert_log(path, args.req_id, fields, Path(args.readme)))
        elif args.command == "reindex":
            code, payload = reindex(Path(args.root).resolve())
            _emit(payload)
            return code
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
