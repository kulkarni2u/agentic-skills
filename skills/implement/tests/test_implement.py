from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "implement.py"

PRD = """\
# PRD: Orders

## 5. Functional requirements
| ID | Requirement | Priority (MoSCoW) | Acceptance criteria |
|---|---|---|---|
| FR-1 | Parse and convert order totals to cents | Must | 12.34 becomes 1234; invalid input is rejected |
| FR-2 | A user can cancel a pending order unless it shipped | Should | Given a pending order when cancelled then status is cancelled<br>Shipped orders cannot be cancelled |
| FR-3 | Export orders as CSV | Could | |

## 6. Non-functional requirements
| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Performance | p95 latency under 200 ms |
"""


def load_module():
    spec = importlib.util.spec_from_file_location("implement", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RequirementTests(unittest.TestCase):
    def test_parses_fr_and_nfr_tables_with_split_criteria(self) -> None:
        impl = load_module()
        reqs = {r["id"]: r for r in impl.parse_requirements(PRD)}

        self.assertEqual(set(reqs), {"FR-1", "FR-2", "FR-3", "NFR-1"})
        self.assertEqual(reqs["FR-1"]["acceptance"], ["12.34 becomes 1234", "invalid input is rejected"])
        self.assertEqual(len(reqs["FR-2"]["acceptance"]), 2)
        self.assertEqual(reqs["FR-3"]["acceptance"], [])
        self.assertTrue(reqs["FR-1"]["must"])
        self.assertFalse(reqs["FR-2"]["must"])
        self.assertTrue(reqs["NFR-1"]["must"])
        self.assertEqual(reqs["NFR-1"]["category"], "Performance")

    def test_selects_by_id_and_must(self) -> None:
        impl = load_module()
        reqs = impl.parse_requirements(PRD)

        self.assertEqual([r["id"] for r in impl.select_requirements(reqs, "FR-2,FR-3", False)], ["FR-2", "FR-3"])
        self.assertEqual([r["id"] for r in impl.select_requirements(reqs, None, True)], ["FR-1", "NFR-1"])


class ApproachTests(unittest.TestCase):
    def test_pure_logic_scores_tdd(self) -> None:
        result = load_module().score_approach("Parse ISO-8601 durations and convert them to seconds")
        self.assertEqual(result["primary"], "tdd")
        self.assertFalse(result["split"])

    def test_rules_and_lifecycle_beat_workflow(self) -> None:
        result = load_module().score_approach(
            "As a user I can cancel a pending order unless it has shipped"
        )
        self.assertEqual(result["primary"], "ddd")
        self.assertIn("lifecycle", result["signals"]["ddd"])

    def test_api_endpoint_scores_bdd(self) -> None:
        result = load_module().score_approach("POST /orders endpoint returns 201 with the created order")
        self.assertEqual(result["primary"], "bdd")

    def test_tie_is_flagged_as_split_and_broken_toward_ddd(self) -> None:
        result = load_module().score_approach("Users see a quota page")
        self.assertEqual(result["scores"]["bdd"], result["scores"]["ddd"])
        self.assertTrue(result["split"])
        self.assertEqual(result["primary"], "ddd")

    def test_no_signal_defaults_to_tdd(self) -> None:
        self.assertEqual(load_module().score_approach("Do the thing")["primary"], "tdd")


class DetectTests(unittest.TestCase):
    def test_makefile_beats_package_scripts_and_rules_are_listed(self) -> None:
        impl = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Makefile").write_text("test:\n\tjest\nlint:\n\teslint .\n")
            (root / "package.json").write_text(json.dumps({
                "scripts": {"test": "jest", "typecheck": "tsc --noEmit"},
                "devDependencies": {"@cucumber/cucumber": "^10"},
            }))
            (root / "pnpm-lock.yaml").write_text("")
            (root / "CLAUDE.md").write_text("rules")

            found = impl.detect(root)

        self.assertEqual(found["commands"], {"test": "make test", "lint": "make lint", "typecheck": "pnpm run typecheck"})
        self.assertEqual(found["bdd_tools"], ["cucumber-js"])
        self.assertIn("CLAUDE.md", found["rules"])

    def test_cargo_defaults(self) -> None:
        impl = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Cargo.toml").write_text("[package]\nname='x'\n")
            self.assertEqual(impl.detect(Path(tmp))["commands"]["test"], "cargo test")


class StubTests(unittest.TestCase):
    def test_diff_scan_reports_only_added_code_lines(self) -> None:
        impl = load_module()
        diff = """\
diff --git a/app/orders.py b/app/orders.py
--- a/app/orders.py
+++ b/app/orders.py
@@ -1,2 +1,5 @@
 import os
-# TODO old
+def cancel(order):
+    pass
+    raise NotImplementedError
+# 501 until FR-4
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1,2 @@
+- [ ] TODO FR-1
"""
        hits = impl.scan_stubs([], diff)
        kinds = {(h["line"], h["kind"]) for h in hits}

        self.assertEqual(kinds, {(3, "empty-body"), (4, "not-implemented"), (5, "http-501")})
        self.assertTrue(all(h["path"] == "app/orders.py" for h in hits))

    def test_file_scan_finds_skipped_tests(self) -> None:
        impl = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            test_file = Path(tmp) / "test_x.py"
            test_file.write_text("import pytest\n\n@pytest.mark.skip\ndef test_a():\n    assert True\n")
            hits = impl.scan_stubs([tmp], None)
        self.assertEqual([(h["line"], h["kind"]) for h in hits], [(3, "skipped-test")])


class LogTests(unittest.TestCase):
    def test_upsert_creates_updates_and_ticks_checklist(self) -> None:
        impl = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "docs" / "IMPLEMENTATION-LOG.md"
            readme = Path(tmp) / "README.md"
            readme.write_text("- [ ] FR-1 totals\n- [ ] FR-10 other\n")

            impl.upsert_log(log, "FR-1", {"approach": "tdd", "status": "partial", "tests": None,
                                          "code": "app/money.py", "notes": None}, readme)
            result = impl.upsert_log(log, "FR-1", {"approach": None, "status": "done",
                                                   "tests": "tests/test_money.py::test_cents | x",
                                                   "code": None, "notes": None}, readme)
            rows = impl.read_log(log)
            checklist = readme.read_text()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "app/money.py")
        self.assertEqual(rows[0]["tests"], "tests/test_money.py::test_cents | x")
        self.assertEqual(result["ticked"], 1)
        self.assertIn("- [x] FR-1 totals", checklist)
        self.assertIn("- [ ] FR-10 other", checklist)

    def test_rejects_unknown_status_and_approach(self) -> None:
        impl = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "log.md"
            with self.assertRaises(ValueError):
                impl.upsert_log(log, "FR-1", {"status": "finished"}, None)
            with self.assertRaises(ValueError):
                impl.upsert_log(log, "FR-1", {"approach": "waterfall"}, None)
            impl.upsert_log(log, "FR-1", {"approach": "ddd+bdd"}, None)


class ReindexTests(unittest.TestCase):
    def test_skips_repos_without_python(self) -> None:
        impl = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "main.go").write_text("package main\n")
            code, payload = impl.reindex(Path(tmp))
        self.assertEqual((code, payload["status"]), (0, "skipped"))


class CliTests(unittest.TestCase):
    def test_requirements_cli_emits_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "PRD.md"
            prd.write_text(PRD)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "requirements", "--prd", str(prd), "--must"],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([r["id"] for r in json.loads(proc.stdout)["requirements"]], ["FR-1", "NFR-1"])

    def test_missing_prd_is_a_usage_error(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "requirements", "--prd", "/nonexistent/PRD.md"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no FR/NFR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
