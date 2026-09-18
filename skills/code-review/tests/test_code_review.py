from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "code_review.py"


def load_module():
    spec = importlib.util.spec_from_file_location("code_review", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DiffSlicingTests(unittest.TestCase):
    def test_slices_changed_hunks_without_assuming_a_language(self) -> None:
        reviewer = load_module()
        diff = """\
diff --git a/src/auth.ts b/src/auth.ts
index 1111111..2222222 100644
--- a/src/auth.ts
+++ b/src/auth.ts
@@ -9,2 +9,3 @@ export function update() {
 keep();
-oldCall();
+newCall();
+audit();
 }
diff --git a/service/worker.py b/service/worker.py
index 3333333..4444444 100644
--- a/service/worker.py
+++ b/service/worker.py
@@ -20 +20 @@ def run():
-    return old()
+    return new()
"""

        hunks = reviewer.parse_unified_diff(diff)

        self.assertEqual([hunk.path for hunk in hunks], ["src/auth.ts", "service/worker.py"])
        self.assertEqual(hunks[0].language, "typescript")
        self.assertEqual(hunks[0].changed_lines, (10, 11))
        self.assertEqual(hunks[1].language, "python")
        self.assertEqual(hunks[1].changed_lines, (20,))

    def test_handles_single_line_hunk_headers(self) -> None:
        reviewer = load_module()
        diff = """\
diff --git a/main.go b/main.go
--- a/main.go
+++ b/main.go
@@ -3 +3 @@
-return oldValue
+return newValue
"""

        hunks = reviewer.parse_unified_diff(diff)

        self.assertEqual(hunks[0].new_start, 3)
        self.assertEqual(hunks[0].new_count, 1)
        self.assertEqual(hunks[0].changed_lines, (3,))


class PolicyGateTests(unittest.TestCase):
    @staticmethod
    def decision(**overrides):
        value = {
            "path": "src/auth.ts",
            "line": 12,
            "condition": {"probability": 0.94, "confidence": 0.91},
            "classification": {
                "category": "security",
                "issue_type": "authorization-bypass",
                "confidence": 0.93,
            },
            "severity": {"value": 9.0, "confidence": 0.90},
            "title": "User-controlled flag bypasses authorization",
            "evidence": "The query flag selects an arbitrary account ID.",
            "impact": "An authenticated user can change another account.",
            "remediation": "Authorize cross-account updates using trusted server-side roles.",
        }
        value.update(overrides)
        return value

    def test_promotes_high_confidence_high_severity_decision_to_blocker(self) -> None:
        reviewer = load_module()

        report = reviewer.gate_decisions([self.decision()])

        self.assertEqual(report["verdict"], "block")
        self.assertEqual(report["findings"][0]["level"], "blocker")
        self.assertEqual(report["suppressed"], [])

    def test_suppresses_weak_triage_signal_before_classification(self) -> None:
        reviewer = load_module()
        decision = self.decision(condition={"probability": 0.20, "confidence": 0.95})

        report = reviewer.gate_decisions([decision])

        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["suppressed"][0]["reason"], "below-triage-threshold")

    def test_suppresses_uncertain_classification(self) -> None:
        reviewer = load_module()
        decision = self.decision(
            classification={
                "category": "security",
                "issue_type": "authorization-bypass",
                "confidence": 0.55,
            }
        )

        report = reviewer.gate_decisions([decision])

        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(report["suppressed"][0]["reason"], "low-classification-confidence")

    def test_rejects_actionable_decision_without_evidence(self) -> None:
        reviewer = load_module()
        decision = self.decision(evidence="")

        with self.assertRaisesRegex(ValueError, "evidence"):
            reviewer.gate_decisions([decision])


class CliTests(unittest.TestCase):
    def test_gate_outputs_json_and_only_fails_when_requested(self) -> None:
        decision = PolicyGateTests.decision()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"decisions": [decision]}, handle)
            decisions_path = Path(handle.name)
        self.addCleanup(decisions_path.unlink, missing_ok=True)

        normal = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "gate", str(decisions_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        blocking = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "gate",
                str(decisions_path),
                "--fail-on",
                "blocker",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(normal.returncode, 0, normal.stderr)
        self.assertEqual(json.loads(normal.stdout)["verdict"], "block")
        self.assertEqual(blocking.returncode, 1)


if __name__ == "__main__":
    unittest.main()
