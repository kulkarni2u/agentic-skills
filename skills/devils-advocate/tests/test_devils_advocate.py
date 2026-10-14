from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "devils_advocate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("devils_advocate", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


da = load_module()


def hardened_ledger() -> dict:
    ledger = da.init_ledger("Session storage", "decision", "docs/adr/007.md")
    for lens_id in ledger["coverage"]:
        ledger["coverage"][lens_id] = {"status": "clear", "note": "examined, nothing material"}
    ledger["steelman"] = "Redis is already run by the team and meets the latency target."
    ledger["decisions"] = [{"id": "D1", "type": "decision", "statement": "Store sessions in one Redis node"}]
    ledger["challenges"] = [
        {
            "id": "C1", "round": 1, "lens": "failure", "target": "D1", "severity": "high",
            "question": "When the single node restarts mid-checkout, which carts are lost?",
            "scenario": "Node restarts during deploy; every active cart disappears.",
            "status": "mitigated", "resolution": "Enable AOF persistence and a replica.", "change": "CH1",
        },
        {
            "id": "C2", "round": 2, "lens": "cost", "target": "D1", "severity": "low",
            "question": "Does the replica double the hosting bill?",
            "scenario": "Replica adds $40/month.",
            "status": "refuted", "evidence": "Pricing page: replica is $12/month on the current plan.",
        },
    ]
    ledger["changes"] = [{"id": "CH1", "description": "Add AOF + one replica", "affects": ["D1"]}]
    ledger["tripwires"] = [{"signal": "Replica lag > 5s", "action": "Page on-call"}]
    return ledger


class LensTests(unittest.TestCase):
    def test_parses_every_lens_with_questions_and_kinds(self) -> None:
        lenses = da.load_lenses()
        self.assertGreaterEqual(len(lenses), 15)
        ids = [lens["id"] for lens in lenses]
        self.assertEqual(len(ids), len(set(ids)))
        for lens in lenses:
            self.assertTrue(lens["questions"], lens["id"])
            self.assertTrue(set(lens["applies_to"]) <= set(da.KINDS), lens["id"])

    def test_kind_filters_lenses_and_other_gets_all(self) -> None:
        code = {lens["id"] for lens in da.lenses_for("code")}
        self.assertIn("edge-cases", code)
        self.assertNotIn("cost", code)
        self.assertEqual(len(da.lenses_for("other")), len(da.load_lenses()))


class GateTests(unittest.TestCase):
    def test_hardened_ledger_passes(self) -> None:
        result = da.gate(hardened_ledger())
        self.assertTrue(result["passed"], result["blockers"])
        self.assertEqual(result["verdict"], "Hardened")

    def test_fresh_ledger_blocks_on_every_pending_lens(self) -> None:
        result = da.gate(da.init_ledger("x", "plan"))
        self.assertEqual(result["verdict"], "Not hardened")
        self.assertTrue(any("steelman" in b for b in result["blockers"]))
        self.assertTrue(any("lens delivery not examined" in b for b in result["blockers"]))

    def test_open_high_blocks_but_open_medium_only_warns(self) -> None:
        ledger = hardened_ledger()
        ledger["challenges"][1].update(severity="medium", status="open")
        result = da.gate(ledger)
        self.assertTrue(result["passed"])
        self.assertEqual(result["verdict"], "Hardened with residual risks")
        ledger["challenges"][0]["status"] = "open"
        self.assertIn("C1 (high) is still open", da.gate(ledger)["blockers"])

    def test_accepted_high_risk_needs_signoff(self) -> None:
        ledger = hardened_ledger()
        ledger["challenges"][0].update(status="accepted", resolution="Carts are cheap to rebuild")
        self.assertTrue(any("sign-off" in b for b in da.gate(ledger)["blockers"]))
        ledger["challenges"][0]["signoff"] = "product owner (user)"
        result = da.gate(ledger)
        self.assertTrue(result["passed"], result["blockers"])
        self.assertEqual(result["verdict"], "Hardened with residual risks")

    def test_resolutions_need_evidence_and_real_changes(self) -> None:
        ledger = hardened_ledger()
        ledger["challenges"][1]["evidence"] = ""
        ledger["challenges"][0]["change"] = "CH9"
        blockers = da.gate(ledger)["blockers"]
        self.assertIn("C2: refuted without evidence", blockers)
        self.assertTrue(any("CH9" in b for b in blockers))

    def test_challenges_must_target_an_extracted_decision(self) -> None:
        ledger = hardened_ledger()
        ledger["challenges"][1]["target"] = "the database"
        self.assertTrue(any("must be relative" in b for b in da.gate(ledger)["blockers"]))

    def test_not_converged_when_last_round_raised_blocking_challenge(self) -> None:
        ledger = hardened_ledger()
        ledger["challenges"][0]["round"] = 2
        self.assertTrue(any("not converged" in b for b in da.gate(ledger)["blockers"]))
        ledger["convergence_waived_by"] = "user, round cap reached"
        self.assertTrue(da.gate(ledger)["passed"])

    def test_lens_marked_na_needs_reason(self) -> None:
        ledger = hardened_ledger()
        ledger["coverage"]["compliance"] = {"status": "n/a", "note": ""}
        self.assertIn("lens compliance marked n/a without a reason", da.gate(ledger)["blockers"])


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT_PATH), *args], capture_output=True, text=True)

    def test_gate_exit_code_and_render_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "ledger.json"
            good.write_text(json.dumps(hardened_ledger()))
            self.assertEqual(self.run_cli("gate", str(good)).returncode, 0)

            bad_ledger = copy.deepcopy(hardened_ledger())
            bad_ledger["challenges"][0]["status"] = "open"
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps(bad_ledger))
            self.assertEqual(self.run_cli("gate", str(bad)).returncode, 1)

            out = Path(tmp) / "docs" / "DA.md"
            proc = self.run_cli("render", str(good), "--date", "2026-10-14", "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = out.read_text()
            self.assertIn("**Verdict: Hardened**", report)
            self.assertIn("| C1 | 1 | failure | D1 | high |", report)
            self.assertIn("Replica lag > 5s", report)

    def test_init_lists_applicable_lenses(self) -> None:
        proc = self.run_cli("init", "--subject", "Rollout", "--kind", "plan")
        ledger = json.loads(proc.stdout)
        self.assertIn("delivery", ledger["coverage"])
        self.assertNotIn("edge-cases", ledger["coverage"])


if __name__ == "__main__":
    unittest.main()
