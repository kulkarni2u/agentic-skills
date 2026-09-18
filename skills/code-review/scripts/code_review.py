#!/usr/bin/env python3
"""Provider-neutral Jev-style diff slicing and decision policy gating."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


HUNK_HEADER = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?P<context>.*)$"
)
DIFF_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")

LANGUAGES = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "typescript",
}


@dataclass(frozen=True)
class DiffHunk:
    path: str
    language: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    changed_lines: tuple[int, ...]
    context: str
    content: str


@dataclass(frozen=True)
class Policy:
    # A low first-stage threshold favors recall while still dropping weak signals.
    triage_probability: float = 0.25
    triage_confidence: float = 0.50
    classification_confidence: float = 0.60
    blocker_severity: float = 7.0
    blocker_confidence: float = 0.80
    warning_severity: float = 4.0
    warning_confidence: float = 0.65


def infer_language(path: str) -> str:
    return LANGUAGES.get(Path(path).suffix.lower(), "unknown")


def parse_unified_diff(diff_text: str) -> list[DiffHunk]:
    """Split a git unified diff into language-neutral review hunks."""
    lines = diff_text.splitlines()
    hunks: list[DiffHunk] = []
    current_path: str | None = None
    index = 0

    while index < len(lines):
        line = lines[index]
        file_match = DIFF_HEADER.match(line)
        if file_match:
            current_path = file_match.group(2)
            index += 1
            continue

        hunk_match = HUNK_HEADER.match(line)
        if current_path is None or hunk_match is None:
            index += 1
            continue

        old_start = int(hunk_match.group(1))
        old_count = int(hunk_match.group(2) or "1")
        new_start = int(hunk_match.group(3))
        new_count = int(hunk_match.group(4) or "1")
        context = hunk_match.group("context").strip()
        index += 1

        content: list[str] = []
        changed_lines: list[int] = []
        new_line = new_start
        while index < len(lines):
            hunk_line = lines[index]
            if hunk_line.startswith("diff --git ") or HUNK_HEADER.match(hunk_line):
                break
            content.append(hunk_line)
            if hunk_line.startswith("+") and not hunk_line.startswith("+++"):
                changed_lines.append(new_line)
                new_line += 1
            elif hunk_line.startswith("-") and not hunk_line.startswith("---"):
                pass
            elif not hunk_line.startswith("\\ No newline at end of file"):
                new_line += 1
            index += 1

        hunks.append(
            DiffHunk(
                path=current_path,
                language=infer_language(current_path),
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                changed_lines=tuple(changed_lines),
                context=context,
                content="\n".join(content),
            )
        )

    return hunks


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return number


def _validated_primitives(decision: Mapping[str, Any]) -> dict[str, Any]:
    path = _text(decision.get("path"), "path")
    line = decision.get("line")
    if isinstance(line, bool) or not isinstance(line, int) or line < 1:
        raise ValueError("line must be a positive integer")

    condition = _mapping(decision.get("condition"), "condition")
    classification = _mapping(decision.get("classification"), "classification")
    severity = _mapping(decision.get("severity"), "severity")

    return {
        "path": path,
        "line": line,
        "condition_probability": _number(
            condition.get("probability"), "condition.probability", 0.0, 1.0
        ),
        "condition_confidence": _number(
            condition.get("confidence"), "condition.confidence", 0.0, 1.0
        ),
        "category": _text(classification.get("category"), "classification.category"),
        "issue_type": _text(
            classification.get("issue_type"), "classification.issue_type"
        ),
        "classification_confidence": _number(
            classification.get("confidence"),
            "classification.confidence",
            0.0,
            1.0,
        ),
        "severity_value": _number(severity.get("value"), "severity.value", 0.0, 10.0),
        "severity_confidence": _number(
            severity.get("confidence"), "severity.confidence", 0.0, 1.0
        ),
    }


def _suppressed(decision: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "path": decision.get("path"),
        "line": decision.get("line"),
        "reason": reason,
    }


def gate_decisions(
    decisions: Iterable[Mapping[str, Any]], policy: Policy | None = None
) -> dict[str, Any]:
    """Validate provider decisions and apply deterministic publication policy."""
    active_policy = policy or Policy()
    findings: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []

    for decision in decisions:
        if not isinstance(decision, Mapping):
            raise ValueError("each decision must be an object")
        values = _validated_primitives(decision)

        if values["condition_probability"] < active_policy.triage_probability:
            suppressed.append(_suppressed(decision, "below-triage-threshold"))
            continue
        if values["condition_confidence"] < active_policy.triage_confidence:
            suppressed.append(_suppressed(decision, "low-triage-confidence"))
            continue
        if values["classification_confidence"] < active_policy.classification_confidence:
            suppressed.append(_suppressed(decision, "low-classification-confidence"))
            continue

        title = _text(decision.get("title"), "title")
        evidence = _text(decision.get("evidence"), "evidence")
        impact = _text(decision.get("impact"), "impact")
        remediation = _text(decision.get("remediation"), "remediation")

        blocker_confidences = (
            values["condition_confidence"],
            values["classification_confidence"],
            values["severity_confidence"],
        )
        if (
            values["severity_value"] >= active_policy.blocker_severity
            and min(blocker_confidences) >= active_policy.blocker_confidence
        ):
            level = "blocker"
        elif (
            values["severity_value"] >= active_policy.warning_severity
            and values["severity_confidence"] >= active_policy.warning_confidence
        ):
            level = "warning"
        else:
            level = "info"

        findings.append(
            {
                "path": values["path"],
                "line": values["line"],
                "level": level,
                "category": values["category"],
                "issue_type": values["issue_type"],
                "title": title,
                "evidence": evidence,
                "impact": impact,
                "remediation": remediation,
                "condition": dict(_mapping(decision["condition"], "condition")),
                "classification": dict(
                    _mapping(decision["classification"], "classification")
                ),
                "severity": dict(_mapping(decision["severity"], "severity")),
            }
        )

    if any(finding["level"] == "blocker" for finding in findings):
        verdict = "block"
    elif findings:
        verdict = "warn"
    else:
        verdict = "pass"

    return {"verdict": verdict, "findings": findings, "suppressed": suppressed}


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def _load_decisions(path: str) -> Sequence[Mapping[str, Any]]:
    try:
        payload = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    if isinstance(payload, Mapping):
        payload = payload.get("decisions")
    if not isinstance(payload, list):
        raise ValueError("input must be a JSON list or an object with a decisions list")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Slice diffs and gate Jev-style review decisions without provider lock-in."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    slice_parser = subparsers.add_parser("slice", help="emit JSON review hunks")
    slice_parser.add_argument("diff", help="unified diff path, or - for stdin")

    gate_parser = subparsers.add_parser("gate", help="validate and gate decision JSON")
    gate_parser.add_argument("decisions", help="decision JSON path, or - for stdin")
    gate_parser.add_argument(
        "--fail-on",
        choices=("never", "warning", "blocker"),
        default="never",
        help="set a non-zero exit status only at the selected level (default: never)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "slice":
            payload = {"hunks": [asdict(hunk) for hunk in parse_unified_diff(_read_text(args.diff))]}
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        report = gate_decisions(_load_decisions(args.decisions))
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.fail_on == "blocker" and report["verdict"] == "block":
            return 1
        if args.fail_on == "warning" and report["verdict"] in {"warn", "block"}:
            return 1
        return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
