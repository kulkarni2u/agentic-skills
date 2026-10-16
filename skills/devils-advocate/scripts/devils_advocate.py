#!/usr/bin/env python3
"""Deterministic helpers for the devils-advocate skill: lenses, ledger skeleton, exit gate, report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence


LENSES_PATH = Path(__file__).resolve().parents[1] / "references" / "lenses.md"
KINDS = ("design", "decision", "plan", "requirements", "code", "other")
DECISION_TYPES = ("decision", "assumption", "constraint", "goal")
SEVERITIES = ("critical", "high", "medium", "low")
STATUSES = ("open", "refuted", "mitigated", "accepted")
COVERAGE_STATUSES = ("pending", "clear", "n/a")
BLOCKING_SEVERITIES = ("critical", "high")
LENS_HEADING = re.compile(r"^###\s+`([a-z0-9-]+)`\s+[—-]+\s+(.+?)\s*$")
VERDICTS = ("Hardened", "Hardened with residual risks", "Not hardened")


def load_lenses(path: Path = LENSES_PATH) -> list[dict[str, Any]]:
    lenses: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = LENS_HEADING.match(line)
        if heading:
            current = {"id": heading.group(1), "name": heading.group(2), "applies_to": [], "questions": []}
            lenses.append(current)
        elif current is None:
            continue
        elif line.startswith("Applies to:"):
            current["applies_to"] = [k.strip() for k in line.split(":", 1)[1].split(",") if k.strip()]
        elif line.startswith("- "):
            current["questions"].append(line[2:].strip())
    return lenses


def lenses_for(kind: str, lenses: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    lenses = load_lenses() if lenses is None else lenses
    if kind == "other":
        return lenses
    return [lens for lens in lenses if kind in lens["applies_to"]]


def init_ledger(subject: str, kind: str, source: str = "") -> dict[str, Any]:
    return {
        "subject": subject,
        "kind": kind,
        "source": source,
        "steelman": "",
        "decisions": [],
        "coverage": {lens["id"]: {"status": "pending", "note": ""} for lens in lenses_for(kind)},
        "challenges": [],
        "changes": [],
        "tripwires": [],
        "convergence_waived_by": "",
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def gate(ledger: dict[str, Any], lenses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Apply the exit rules. Blockers mean the proposal is not hardened yet."""
    all_lenses = {lens["id"] for lens in (load_lenses() if lenses is None else lenses)}
    blockers: list[str] = []
    warnings: list[str] = []

    kind = ledger.get("kind", "")
    if kind not in KINDS:
        blockers.append(f"kind {kind!r} is not one of {', '.join(KINDS)}")
    if not _text(ledger.get("steelman")):
        blockers.append("steelman is empty: state the strongest case for the proposal before attacking it")

    decisions = ledger.get("decisions") or []
    decision_ids = {d.get("id") for d in decisions}
    if not decisions:
        blockers.append("no decisions or assumptions extracted from the proposal")
    for d in decisions:
        if d.get("type") not in DECISION_TYPES:
            blockers.append(f"{d.get('id')}: type must be one of {', '.join(DECISION_TYPES)}")

    change_ids = {c.get("id") for c in ledger.get("changes") or []}
    challenges = ledger.get("challenges") or []
    challenged_lenses: set[str] = set()
    counts = {s: 0 for s in STATUSES}
    open_by_severity = {s: 0 for s in SEVERITIES}
    accepted: list[str] = []

    for c in challenges:
        cid = c.get("id", "?")
        lens, severity, status = c.get("lens"), c.get("severity"), c.get("status")
        if lens not in all_lenses:
            blockers.append(f"{cid}: unknown lens {lens!r}")
        else:
            challenged_lenses.add(lens)
        if c.get("target") not in decision_ids:
            blockers.append(f"{cid}: target {c.get('target')!r} is not an extracted decision; challenges must be relative")
        if not _text(c.get("question")) or not _text(c.get("scenario")):
            blockers.append(f"{cid}: needs both a question and a concrete failure scenario")
        if severity not in SEVERITIES:
            blockers.append(f"{cid}: severity must be one of {', '.join(SEVERITIES)}")
            continue
        if status not in STATUSES:
            blockers.append(f"{cid}: status must be one of {', '.join(STATUSES)}")
            continue
        counts[status] += 1
        blocking = severity in BLOCKING_SEVERITIES
        if status == "open":
            open_by_severity[severity] += 1
            (blockers if blocking else warnings).append(f"{cid} ({severity}) is still open")
        elif status == "refuted" and not _text(c.get("evidence")):
            blockers.append(f"{cid}: refuted without evidence")
        elif status == "mitigated":
            if not _text(c.get("resolution")):
                blockers.append(f"{cid}: mitigated without a resolution")
            if c.get("change") not in change_ids:
                blockers.append(f"{cid}: mitigated but change {c.get('change')!r} is not in changes")
        elif status == "accepted":
            accepted.append(cid)
            if blocking and not _text(c.get("signoff")):
                blockers.append(f"{cid} ({severity}): accepted risk needs a named sign-off")
            if not _text(c.get("resolution")):
                warnings.append(f"{cid}: accepted without a stated rationale or tripwire")

    coverage = ledger.get("coverage") or {}
    for lens_id, entry in coverage.items():
        status = (entry or {}).get("status", "pending")
        note = _text((entry or {}).get("note"))
        if lens_id not in all_lenses:
            blockers.append(f"coverage: unknown lens {lens_id!r}")
        elif lens_id in challenged_lenses:
            continue
        elif status == "pending":
            blockers.append(f"lens {lens_id} not examined")
        elif status not in COVERAGE_STATUSES:
            blockers.append(f"lens {lens_id}: status must be one of {', '.join(COVERAGE_STATUSES)}")
        elif not note:
            blockers.append(f"lens {lens_id} marked {status} without a reason")

    rounds = [c.get("round") for c in challenges if isinstance(c.get("round"), int)]
    last_round = max(rounds, default=0)
    late_blocking = [
        c.get("id", "?") for c in challenges
        if c.get("round") == last_round and c.get("severity") in BLOCKING_SEVERITIES
    ]
    if last_round and late_blocking and not _text(ledger.get("convergence_waived_by")):
        blockers.append(
            f"not converged: round {last_round} raised {', '.join(late_blocking)}; "
            "attack the revised proposal again until a round raises no critical/high challenge"
        )

    if (accepted or counts["mitigated"]) and not ledger.get("tripwires"):
        warnings.append("no tripwires: name the signals that would show a mitigation or accepted risk failing")

    verdict = VERDICTS[2] if blockers else VERDICTS[1] if (warnings or accepted) else VERDICTS[0]
    return {
        "verdict": verdict,
        "passed": not blockers,
        "rounds": last_round,
        "challenges": len(challenges),
        "status_counts": counts,
        "open_by_severity": open_by_severity,
        "accepted": accepted,
        "blockers": blockers,
        "warnings": warnings,
    }


def _cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip() or "—"


def render(ledger: dict[str, Any], date: str) -> str:
    result = gate(ledger)
    lens_names = {lens["id"]: lens["name"] for lens in load_lenses()}
    lines = [
        f"# Devil's advocate review: {ledger.get('subject', '')}",
        "",
        f"| Kind | {ledger.get('kind', '')} | Source | {ledger.get('source') or '—'} | Date | {date} |",
        "|---|---|---|---|---|---|",
        "",
        f"**Verdict: {result['verdict']}** — {result['challenges']} challenges over "
        f"{result['rounds']} round(s); " + ", ".join(f"{n} {s}" for s, n in result["status_counts"].items()) + ".",
        "",
    ]
    if result["blockers"]:
        lines += ["## Blockers", ""] + [f"- {b}" for b in result["blockers"]] + [""]
    lines += ["## Strongest case for the proposal", "", _text(ledger.get("steelman")) or "—", ""]
    lines += ["## Decisions and assumptions examined", "", "| ID | Type | Statement |", "|---|---|---|"]
    lines += [f"| {_cell(d.get('id'))} | {_cell(d.get('type'))} | {_cell(d.get('statement'))} |"
              for d in ledger.get("decisions") or []]
    lines += ["", "## Challenges", "",
              "| ID | Rd | Lens | Target | Severity | Question | Failure scenario | Status | Resolution / evidence |",
              "|---|---|---|---|---|---|---|---|---|"]
    order = {s: i for i, s in enumerate(SEVERITIES)}
    for c in sorted(ledger.get("challenges") or [], key=lambda c: (order.get(c.get("severity"), 9), str(c.get("id")))):
        outcome = c.get("evidence") if c.get("status") == "refuted" else c.get("resolution")
        if c.get("change"):
            outcome = f"{outcome or ''} ({c['change']})"
        if c.get("signoff"):
            outcome = f"{outcome or ''} — signed off by {c['signoff']}"
        lines.append(
            f"| {_cell(c.get('id'))} | {_cell(c.get('round'))} | {_cell(c.get('lens'))} | {_cell(c.get('target'))} "
            f"| {_cell(c.get('severity'))} | {_cell(c.get('question'))} | {_cell(c.get('scenario'))} "
            f"| {_cell(c.get('status'))} | {_cell(outcome)} |"
        )
    lines += ["", "## Changes to the proposal", ""]
    changes = ledger.get("changes") or []
    lines += [f"- **{_cell(ch.get('id'))}** ({', '.join(ch.get('affects') or []) or '—'}): {_cell(ch.get('description'))}"
              for ch in changes] or ["- None."]
    lines += ["", "## Residual risks", ""]
    residual = [c for c in ledger.get("challenges") or [] if c.get("status") in ("accepted", "open")]
    lines += [f"- **{c.get('id')}** ({c.get('severity')}, {c.get('status')}): {_cell(c.get('question'))}"
              for c in residual] or ["- None identified."]
    lines += ["", "## Tripwires", "", "| Signal | Action |", "|---|---|"]
    lines += [f"| {_cell(t.get('signal'))} | {_cell(t.get('action'))} |" for t in ledger.get("tripwires") or []]
    lines += ["", "## Lens coverage", "", "| Lens | Result |", "|---|---|"]
    challenged = {c.get("lens") for c in ledger.get("challenges") or []}
    for lens_id, entry in (ledger.get("coverage") or {}).items():
        n = sum(1 for c in ledger.get("challenges") or [] if c.get("lens") == lens_id)
        result_text = f"{n} challenge(s)" if lens_id in challenged else f"{entry.get('status')}: {entry.get('note') or '—'}"
        lines.append(f"| {_cell(lens_names.get(lens_id, lens_id))} | {_cell(result_text)} |")
    if result["warnings"]:
        lines += ["", "## Warnings", ""] + [f"- {w}" for w in result["warnings"]]
    return "\n".join(lines) + "\n"


def _read_json(path: str) -> dict[str, Any]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic helpers for the devils-advocate skill.")
    sub = parser.add_subparsers(dest="command", required=True)
    lenses = sub.add_parser("lenses", help="lenses and question templates for a proposal kind")
    lenses.add_argument("--kind", choices=KINDS, default="other")
    init = sub.add_parser("init", help="empty ledger with every applicable lens pending")
    init.add_argument("--subject", required=True)
    init.add_argument("--kind", choices=KINDS, required=True)
    init.add_argument("--source", default="")
    gate_cmd = sub.add_parser("gate", help="apply the exit rules to a filled ledger")
    gate_cmd.add_argument("ledger")
    rend = sub.add_parser("render", help="write the markdown report from a filled ledger")
    rend.add_argument("ledger")
    rend.add_argument("--date", default=dt.date.today().isoformat())
    rend.add_argument("--out")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "lenses":
        print(json.dumps(lenses_for(args.kind), indent=2))
    elif args.command == "init":
        print(json.dumps(init_ledger(args.subject, args.kind, args.source), indent=2))
    elif args.command == "gate":
        result = gate(_read_json(args.ledger))
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    elif args.command == "render":
        ledger = _read_json(args.ledger)
        report = render(ledger, args.date)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(report, encoding="utf-8")
            print(json.dumps({"written": args.out, "verdict": gate(ledger)["verdict"]}))
        else:
            sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
