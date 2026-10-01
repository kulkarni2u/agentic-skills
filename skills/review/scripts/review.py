#!/usr/bin/env python3
"""Deterministic helpers for the review skill: scope, verification matrix, verdict, report."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


IMPLEMENT_SCRIPT = Path(__file__).resolve().parents[2] / "implement" / "scripts" / "implement.py"
VERDICTS = ("Met", "Partially met", "Not met", "Not verifiable")
REQUEST_CHANGES = "Request changes"
FOLLOW_UPS = "Approve with follow-ups"
APPROVE = "Approve"
REVIEW_PATH = "docs/blueprint/REVIEW.md"


def _load_implement():
    spec = importlib.util.spec_from_file_location("implement_helpers", IMPLEMENT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {IMPLEMENT_SCRIPT}; the implement skill must sit beside review")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


impl = _load_implement()


# ---------------------------------------------------------------- scope

def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def default_base() -> str:
    try:
        return _git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    except ValueError:
        for candidate in ("origin/main", "origin/master", "main", "master"):
            if subprocess.run(["git", "rev-parse", "--verify", "-q", candidate], capture_output=True).returncode == 0:
                return candidate
    raise ValueError("cannot find a default branch; pass --base")


def resolve_diff(target: str | None, base: str | None) -> tuple[str, str, str]:
    """Return (base, head, diff text) for a range, a branch/commit, or the working tree."""
    if target is None:
        return "HEAD", "working tree", _git("diff", "HEAD")
    if ".." in target:
        left, _, right = target.partition("...") if "..." in target else target.partition("..")
        return left or "HEAD", right or "HEAD", _git("diff", target)
    chosen = base or default_base()
    return chosen, target, _git("diff", f"{chosen}...{target}")


def changed_files(diff_text: str) -> list[str]:
    files = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            files.append(line.split(" b/", 1)[-1])
    return files


def build_scope(diff_text: str, base: str, head: str, log_path: Path) -> dict[str, Any]:
    files = changed_files(diff_text)
    rows = impl.read_log(log_path)
    traced = " ".join(f"{row['tests']} {row['code']}" for row in rows)
    code_files = [f for f in files if Path(f).suffix not in impl.DOC_SUFFIXES and not f.startswith("docs/")]
    return {
        "base": base,
        "head": head,
        "files": files,
        "claimed": [{"id": r["id"], "status": r["status"], "approach": r["approach"]} for r in rows],
        "stubs": impl.scan_stubs([], diff_text),
        # Changed code the log never mentions: a scope-creep candidate for the reviewer to judge.
        "untraced": [f for f in code_files if f not in traced and Path(f).name not in traced],
    }


# ---------------------------------------------------------------- matrix

def build_matrix(reqs: Sequence[Mapping[str, Any]], log_rows: Sequence[Mapping[str, str]],
                 stubs: Sequence[Mapping[str, Any]], ids: set[str] | None) -> dict[str, Any]:
    by_id = {row["id"]: row for row in log_rows}
    in_scope = ids if ids is not None else (set(by_id) or {r["id"] for r in reqs})
    rows: list[dict[str, Any]] = []
    for req in reqs:
        if req["id"] not in in_scope:
            continue
        log = by_id.get(req["id"], {})
        stub_hits = [
            f"{hit['path']}:{hit['line']} {hit['kind']}" for hit in stubs
            if hit["path"] in log.get("code", "") or Path(hit["path"]).name in log.get("code", "")
        ]
        criteria = req["acceptance"] or [req["requirement"]]
        for criterion in criteria:
            row = {
                "id": req["id"],
                "criterion": criterion,
                "must": req["must"],
                "evidence": log.get("tests", ""),
                "verdict": None,
                "notes": "" if req["acceptance"] else "no acceptance criteria in the PRD",
            }
            if stub_hits and log.get("status") == "done":
                row["verdict"] = "Not met"
                row["notes"] = "claimed done but stubbed: " + "; ".join(stub_hits)
            rows.append(row)
    return {"matrix": rows, "out_of_scope": sorted(r["id"] for r in reqs if r["id"] not in in_scope)}


# ---------------------------------------------------------------- verdict

def decide(bundle: Mapping[str, Any]) -> dict[str, Any]:
    matrix = bundle.get("matrix") or []
    unfilled = [f"{row.get('id')}: {row.get('criterion')}" for row in matrix if row.get("verdict") not in VERDICTS]
    if unfilled:
        raise ValueError("matrix rows without a valid verdict: " + "; ".join(unfilled[:5]))
    findings = (bundle.get("gate") or {}).get("findings", [])
    blockers = [f for f in findings if f.get("level") == "blocker"]
    warnings = [f for f in findings if f.get("level") == "warning"]
    checks = bundle.get("checks") or {}
    failed_checks = [r["command"] for r in checks.get("results", []) if not r.get("passed")]

    must_unmet = [r for r in matrix if r["must"] and r["verdict"] == "Not met"]
    soft = [r for r in matrix if r["verdict"] in ("Partially met", "Not verifiable")
            or (r["verdict"] == "Not met" and not r["must"])]

    reasons: list[str] = []
    reasons += [f"Must requirement not met: {r['id']} — {r['criterion']}" for r in must_unmet]
    reasons += [f"Code-review blocker: {f.get('path')}:{f.get('line')} {f.get('title')}" for f in blockers]
    reasons += [f"Check failed: {command}" for command in failed_checks]
    if reasons:
        verdict = REQUEST_CHANGES
    elif warnings or soft or bundle.get("drift"):
        verdict = FOLLOW_UPS
        reasons += [f"{len(warnings)} code-review warning(s)"] if warnings else []
        reasons += [f"{r['id']}: {r['verdict']}" for r in soft]
        reasons += ["design drift recorded"] if bundle.get("drift") else []
    else:
        verdict = APPROVE
    counts = {name: sum(1 for r in matrix if r["verdict"] == name) for name in VERDICTS}
    return {"verdict": verdict, "reasons": reasons, "counts": counts,
            "blockers": len(blockers), "warnings": len(warnings)}


# ---------------------------------------------------------------- render

def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def _bullets(items: Sequence[Any] | None, empty: str = "None.") -> list[str]:
    return [f"- {item}" for item in items] if items else [empty]


def render(bundle: Mapping[str, Any], date: str) -> str:
    result = decide(bundle)
    lines = [
        f"# Review: {bundle.get('title', 'change')}",
        f"| Verdict | {result['verdict']} | Base..Head | {bundle.get('base', '?')}..{bundle.get('head', '?')} "
        f"| Date | {date} | Requirements | {', '.join(bundle.get('requirements_sources', [])) or '—'} |",
        "|---|---|---|---|---|---|---|---|",
        "",
        "## 1. Summary",
        bundle.get("summary", "").strip() or "_No summary provided._",
        "",
        "**Decided by:**",
        *_bullets(result["reasons"], "All in-scope requirements met; no blockers or warnings."),
        "",
        "## 2. Verification matrix",
        " · ".join(f"{name}: {count}" for name, count in result["counts"].items()),
        "",
        "| ID | Acceptance criterion | Evidence | Verdict | Notes |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {_cell(r['id'])}{' (Must)' if r.get('must') else ''} | {_cell(r['criterion'])} | "
        f"{_cell(r.get('evidence'))} | {_cell(r['verdict'])} | {_cell(r.get('notes'))} |"
        for r in bundle.get("matrix", [])
    ]
    lines += ["", "## 3. Code findings"]
    findings = (bundle.get("gate") or {}).get("findings", [])
    order = {"blocker": 0, "warning": 1, "info": 2}
    for f in sorted(findings, key=lambda item: order.get(item.get("level"), 3)):
        lines += [
            f"- **{f.get('level', '?')}** `{f.get('path')}:{f.get('line')}` — {f.get('title')}",
            f"  - Failure: {f.get('impact')} Evidence: {f.get('evidence')}",
            f"  - Fix: {f.get('remediation')}",
        ]
    if not findings:
        lines.append("None.")
    lines += ["", "## 4. Test quality", *_bullets(bundle.get("test_quality"))]
    lines += ["", "## 5. Scope creep & design drift", *_bullets(bundle.get("drift"))]
    lines += ["", "## 6. Not verified", *_bullets(bundle.get("not_verified"))]
    lines += ["", "## 7. Commands run"]
    commands = [f"`{r['command']}` → exit {r['exit_code']} ({'pass' if r['passed'] else 'FAIL'})"
                for r in (bundle.get("checks") or {}).get("results", [])]
    commands += [f"`{c.get('command')}` → {c.get('result')}" for c in bundle.get("commands", [])]
    lines += _bullets(commands)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- cli

def _load_json(path: str) -> Any:
    try:
        return json.loads(sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON from {path}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic helpers for the review skill.")
    sub = parser.add_subparsers(dest="command", required=True)

    scope = sub.add_parser("scope", help="write the change diff; list files, claimed FRs, stubs, untraced code")
    scope.add_argument("target", nargs="?", help="range (a..b), branch/commit, or omit for the working tree")
    scope.add_argument("--base", help="base for a branch/commit target (default: origin's default branch)")
    scope.add_argument("--diff", help="use this diff instead of running git (e.g. a fetched PR diff)")
    scope.add_argument("--out", default="change.diff", help="where to write the diff")
    scope.add_argument("--log", default=impl.LOG_PATH)

    matrix = sub.add_parser("matrix", help="verification-matrix skeleton, one row per acceptance criterion")
    matrix.add_argument("--prd", default=impl.PRD_PATH)
    matrix.add_argument("--log", default=impl.LOG_PATH)
    matrix.add_argument("--scope", help="scope JSON, to pre-fail done FRs that still contain stubs")
    matrix.add_argument("--ids", help="comma-separated IDs (default: FRs in the log, else all)")

    verdict = sub.add_parser("verdict", help="apply the verdict rules to a filled review bundle")
    verdict.add_argument("bundle")

    rend = sub.add_parser("render", help="write REVIEW.md from a filled review bundle")
    rend.add_argument("bundle")
    rend.add_argument("--out", default=REVIEW_PATH)
    rend.add_argument("--date", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "scope":
            if args.diff:
                base, head = args.base or "?", "provided diff"
                diff_text = sys.stdin.read() if args.diff == "-" else Path(args.diff).read_text(encoding="utf-8")
            else:
                base, head, diff_text = resolve_diff(args.target, args.base)
            Path(args.out).write_text(diff_text, encoding="utf-8")
            payload = build_scope(diff_text, base, head, Path(args.log))
            payload["diff_path"] = args.out
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        elif args.command == "matrix":
            reqs = impl.parse_requirements(impl._read(Path(args.prd)))
            if not reqs:
                raise ValueError(f"no FR/NFR table rows found in {args.prd}")
            stubs = _load_json(args.scope).get("stubs", []) if args.scope else []
            ids = {item.strip() for item in args.ids.split(",")} if args.ids else None
            print(json.dumps(build_matrix(reqs, impl.read_log(Path(args.log)), stubs, ids), indent=2, ensure_ascii=False))
        elif args.command == "verdict":
            print(json.dumps(decide(_load_json(args.bundle)), indent=2, ensure_ascii=False))
        elif args.command == "render":
            bundle = _load_json(args.bundle)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render(bundle, args.date), encoding="utf-8")
            print(json.dumps({"written": str(out), **decide(bundle)}, indent=2, ensure_ascii=False))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
