from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "review.py"

PRD = """\
| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-1 | Convert totals to cents | Must | 12.34 becomes 1234; invalid input is rejected |
| FR-2 | Cancel pending orders | Should | Pending orders can be cancelled |
| FR-3 | Export CSV | Could | |
"""
LOG = """\
# Implementation Log

| FR | Approach | Tests (file::name) | Code | Status | Notes / assumptions |
|---|---|---|---|---|---|
| FR-1 | tdd | tests/test_money.py::test_cents | app/money.py | done | |
| FR-2 | ddd | tests/test_orders.py::test_cancel | app/orders.py | partial | |
"""
DIFF = """\
diff --git a/app/money.py b/app/money.py
--- a/app/money.py
+++ b/app/money.py
@@ -1 +1,2 @@
 x = 1
+raise NotImplementedError
diff --git a/app/extra.py b/app/extra.py
--- /dev/null
+++ b/app/extra.py
@@ -0,0 +1 @@
+def bonus(): return 1
diff --git a/docs/blueprint/PRD.md b/docs/blueprint/PRD.md
--- a/docs/blueprint/PRD.md
+++ b/docs/blueprint/PRD.md
@@ -1 +1,2 @@
+TODO
"""


def load_module():
    spec = importlib.util.spec_from_file_location("review", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def filled(matrix, verdict="Met"):
    return [dict(row, verdict=row["verdict"] or verdict) for row in matrix]


class ScopeAndMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "log.md"
        self.log.write_text(LOG)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_scope_lists_claims_stubs_and_untraced_code(self) -> None:
        scope = self.review.build_scope(DIFF, "main", "feature", self.log)

        self.assertEqual(scope["files"], ["app/money.py", "app/extra.py", "docs/blueprint/PRD.md"])
        self.assertEqual([c["id"] for c in scope["claimed"]], ["FR-1", "FR-2"])
        self.assertEqual([(s["path"], s["kind"]) for s in scope["stubs"]], [("app/money.py", "not-implemented")])
        self.assertEqual(scope["untraced"], ["app/extra.py"])

    def test_matrix_defaults_to_logged_frs_and_prefails_stubbed_done_rows(self) -> None:
        reqs = self.review.impl.parse_requirements(PRD)
        stubs = self.review.build_scope(DIFF, "main", "feature", self.log)["stubs"]

        result = self.review.build_matrix(reqs, self.review.impl.read_log(self.log), stubs, None)
        rows = result["matrix"]

        self.assertEqual([r["id"] for r in rows], ["FR-1", "FR-1", "FR-2"])
        self.assertEqual({r["verdict"] for r in rows if r["id"] == "FR-1"}, {"Not met"})
        self.assertIsNone(rows[2]["verdict"])
        self.assertEqual(rows[0]["evidence"], "tests/test_money.py::test_cents")
        self.assertEqual(result["out_of_scope"], ["FR-3"])

    def test_requirement_without_criteria_gets_one_row(self) -> None:
        reqs = self.review.impl.parse_requirements(PRD)
        rows = self.review.build_matrix(reqs, [], [], {"FR-3"})["matrix"]
        self.assertEqual([(r["criterion"], r["notes"]) for r in rows],
                         [("Export CSV", "no acceptance criteria in the PRD")])


class VerdictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load_module()
        reqs = self.review.impl.parse_requirements(PRD)
        self.matrix = self.review.build_matrix(reqs, [], [], {"FR-1", "FR-2"})["matrix"]

    def test_all_met_approves(self) -> None:
        result = self.review.decide({"matrix": filled(self.matrix)})
        self.assertEqual(result["verdict"], "Approve")
        self.assertEqual(result["counts"]["Met"], 3)

    def test_must_not_met_requests_changes(self) -> None:
        matrix = filled(self.matrix)
        matrix[0]["verdict"] = "Not met"
        self.assertEqual(self.review.decide({"matrix": matrix})["verdict"], "Request changes")

    def test_should_not_met_is_a_follow_up(self) -> None:
        matrix = filled(self.matrix)
        matrix[2]["verdict"] = "Not met"
        self.assertEqual(self.review.decide({"matrix": matrix})["verdict"], "Approve with follow-ups")

    def test_blocker_or_failed_check_requests_changes(self) -> None:
        gate = {"findings": [{"level": "blocker", "path": "a.py", "line": 1, "title": "t"}]}
        checks = {"results": [{"command": "pytest", "passed": False, "exit_code": 1}]}
        self.assertEqual(self.review.decide({"matrix": filled(self.matrix), "gate": gate})["verdict"],
                         "Request changes")
        self.assertEqual(self.review.decide({"matrix": filled(self.matrix), "checks": checks})["verdict"],
                         "Request changes")

    def test_warning_or_drift_is_a_follow_up(self) -> None:
        gate = {"findings": [{"level": "warning"}]}
        self.assertEqual(self.review.decide({"matrix": filled(self.matrix), "gate": gate})["verdict"],
                         "Approve with follow-ups")
        self.assertEqual(self.review.decide({"matrix": filled(self.matrix), "drift": ["x"]})["verdict"],
                         "Approve with follow-ups")

    def test_unfilled_rows_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.review.decide({"matrix": self.matrix})


class RenderTests(unittest.TestCase):
    def test_render_cli_writes_report_with_verdict(self) -> None:
        review = load_module()
        matrix = filled(review.build_matrix(review.impl.parse_requirements(PRD), [], [], {"FR-1"})["matrix"])
        bundle = {
            "title": "Totals", "base": "main", "head": "feat", "requirements_sources": ["PRD.md"],
            "summary": "Adds cents conversion.", "matrix": matrix,
            "gate": {"findings": [{"level": "info", "path": "a.py", "line": 2, "title": "Note",
                                   "impact": "i", "evidence": "e", "remediation": "r"}]},
            "checks": {"results": [{"command": "pytest -q", "exit_code": 0, "passed": True}]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            bundle_path = Path(tmp) / "bundle.json"
            bundle_path.write_text(json.dumps(bundle))
            out = Path(tmp) / "REVIEW.md"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "render", str(bundle_path), "--out", str(out),
                 "--date", "2026-10-01"],
                capture_output=True, text=True, check=False,
            )
            report = out.read_text()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "Approve")
        self.assertIn("| Verdict | Approve |", report)
        self.assertIn("| FR-1 (Must) | 12.34 becomes 1234 |", report)
        self.assertIn("`pytest -q` → exit 0 (pass)", report)
        self.assertIn("**info** `a.py:2` — Note", report)


if __name__ == "__main__":
    unittest.main()
