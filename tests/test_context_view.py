from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from common import ProtocolError, atomic_yaml_write, load_state  # noqa: E402
from context_view import build_view, check_fresh, excerpt, history_view  # noqa: E402
from experiment_registry import activate, approve, register  # noqa: E402
from runner import run  # noqa: E402


class ContextViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in ("schemas", "templates", "research", "evidence", "tools", ".agents"):
            shutil.copytree(ROOT / directory, self.root / directory)
        (self.root / "docs").mkdir()
        for path in (ROOT / "docs").glob("*.md"):
            shutil.copy2(path, self.root / "docs" / path.name)
        for filename in ("AGENTS.md", "Research Spine.md"):
            shutil.copy2(ROOT / filename, self.root / filename)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _prepare_run(self) -> str:
        state = load_state(self.root)
        state["status"] = "ACTIVE"
        state["human_gates"]["gate_1"] = "approved"
        state["experiment_contract"]["status"] = "approved"
        # These planner judgments must never appear in the blind-first packet.
        state["claim_status"] = {"C1": "PLANNER_PREFERRED_VERDICT"}
        state["next_action"] = {"reason": "PLANNER_PREFERRED_VERDICT"}
        atomic_yaml_write(self.root / "research/research_state.yaml", state)
        contract = yaml.safe_load((self.root / "research/experiment_contract.yaml").read_text(encoding="utf-8"))
        contract["contract"]["status"] = "approved"
        atomic_yaml_write(self.root / "research/experiment_contract.yaml", contract)
        card = yaml.safe_load((self.root / "templates/experiment_card.yaml").read_text(encoding="utf-8"))
        card["experiment"]["datasets"] = ["toy"]
        card["experiment"]["seed_protocol"] = {"seeds": [1, 2, 3]}
        path = "experiments/E0001/experiment_card.yaml"
        atomic_yaml_write(self.root / path, card)
        state = register(self.root, path, state["revision"])
        state = approve(self.root, "E0001", "test-orchestrator", state["revision"])
        activate(self.root, "E0001", state["revision"])
        metric = self.root / "experiments/E0001/metrics.json"
        metric.write_text('{"seed_scores":[0.8,0.7,0.9]}', encoding="utf-8")
        manifest = run(self.root, "E0001", [sys.executable, "-c", "print('all three seeds recorded')"],
            30, [metric])
        return manifest.relative_to(self.root).as_posix()

    def test_projection_is_read_only_and_detects_same_revision_changes(self) -> None:
        state_path = self.root / "research/research_state.yaml"
        before = state_path.read_bytes()
        view = build_view(self.root)
        self.assertEqual(before, state_path.read_bytes())
        self.assertEqual([], check_fresh(self.root, view))
        state = load_state(self.root)
        state["unresolved_risks"].append({"id": "R2", "description": "must expand evidence"})
        atomic_yaml_write(state_path, state)
        self.assertIn("research/research_state.yaml", check_fresh(self.root, view))

    def test_policy_change_invalidates_reusable_context(self) -> None:
        view = build_view(self.root)
        path = self.root / "docs/PROTOCOLS.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nUpdated rule", encoding="utf-8")
        self.assertIn("docs/PROTOCOLS.md", check_fresh(self.root, view))

    def test_large_history_is_bounded_but_active_work_and_risks_are_complete(self) -> None:
        state = load_state(self.root)
        for number in range(300):
            item_id = f"E{number+1000}"
            state["experiment_registry"].append({
                "id": item_id, "kind": "scientific", "priority": "P0",
                "experiment_role": "CORE_P0", "experiment_mode": "full_evaluation",
                "paper_evidence_eligible": True, "candidate_id": None, "design_iteration_id": None,
                "status": "audited", "card_path": f"experiments/{item_id}/experiment_card.yaml"})
            state["completed_experiments"].append(item_id)
            state["backlog"].append(item_id)
        state["active_queue"] = ["E1299"]
        state["unresolved_risks"] = [{"id": "NEGATIVE", "description": "primary counter-evidence"}]
        atomic_yaml_write(self.root / "research/research_state.yaml", state)
        view = build_view(self.root, limit=4)
        self.assertEqual(296, view["backlog"]["omitted"])
        self.assertEqual("E1299", view["active_items"][0]["id"])
        self.assertEqual(state["unresolved_risks"], view["unresolved_risks"])
        self.assertEqual(state["claims"], view["claims"])
        self.assertLess(len(json.dumps(view)), len(json.dumps(state)) * 0.3)

    def test_runner_card_complete_but_view_does_not_authorize(self) -> None:
        state = load_state(self.root)
        card = yaml.safe_load((self.root / "templates/experiment_card.yaml").read_text(encoding="utf-8"))
        path = "experiments/E0001/experiment_card.yaml"
        atomic_yaml_write(self.root / path, card)
        register(self.root, path, state["revision"])
        view = build_view(self.root, "runner", experiment_id="E0001")
        self.assertEqual(card, view["card"])
        self.assertFalse(view["execution_state"]["in_active_queue"])
        with self.assertRaises(ProtocolError):
            run(self.root, "E0001", [sys.executable, "-c", "print('should not run')"], 10)

    def test_auditor_packet_excludes_planner_and_preserves_raw_evidence(self) -> None:
        manifest_path = self._prepare_run()
        view = build_view(self.root, "auditor", experiment_id="E0001", manifest_path=manifest_path)
        self.assertNotIn("PLANNER_PREFERRED_VERDICT", json.dumps(view))
        self.assertNotIn("claim_status", view)
        self.assertEqual([1, 2, 3], view["card"]["experiment"]["seed_protocol"]["seeds"])
        self.assertTrue(view["evidence_review_required"])
        self.assertIn("manifest_integrity", view["deterministic_checks"])
        self.assertEqual([], check_fresh(self.root, view))
        metrics = self.root / "experiments/E0001/metrics.json"
        metrics.write_text('{"seed_scores":[0.99]}', encoding="utf-8")
        self.assertIn("experiments/E0001/metrics.json", check_fresh(self.root, view))
        with self.assertRaisesRegex(ProtocolError, "integrity mismatch"):
            build_view(self.root, "auditor", experiment_id="E0001", manifest_path=manifest_path)

    def test_auditor_requires_specific_manifest(self) -> None:
        with self.assertRaises(ProtocolError):
            build_view(self.root, "auditor")

    def test_runner_receives_complete_refinement_and_envelope(self) -> None:
        state = load_state(self.root)
        iteration = yaml.safe_load((self.root / "templates/design_iteration.yaml").read_text(encoding="utf-8"))
        envelope = yaml.safe_load((self.root / "templates/design_envelope.yaml").read_text(encoding="utf-8"))
        iteration_path = "research/method/D0001.yaml"
        envelope_path = "research/method/envelope.yaml"
        envelope_id = iteration["design_iteration"]["design_envelope_id"]
        atomic_yaml_write(self.root / iteration_path, iteration)
        atomic_yaml_write(self.root / envelope_path, envelope)
        state["design_iterations"] = [{"id": "D0001", "path": iteration_path, "status": "approved"}]
        state["design_envelopes"] = [{"id": envelope_id, "path": envelope_path, "status": "active"}]
        atomic_yaml_write(self.root / "research/research_state.yaml", state)
        card = yaml.safe_load((self.root / "templates/experiment_card.yaml").read_text(encoding="utf-8"))
        card["experiment"]["design_iteration_id"] = "D0001"
        card["experiment"]["experiment_mode"] = "refinement_validation"
        path = "experiments/E0001/experiment_card.yaml"
        atomic_yaml_write(self.root / path, card)
        register(self.root, path, state["revision"])
        view = build_view(self.root, "runner", experiment_id="E0001")
        self.assertEqual([iteration, envelope], [x["document"] for x in view["method_artifacts"]])

    def test_venue_view_tracks_complete_evidence_sources(self) -> None:
        view = build_view(self.root, "venue")
        self.assertIn("evidence/claim_evidence.yaml", [x["path"] for x in view["sources"]])
        self.assertEqual([], check_fresh(self.root, view))

    def test_history_pagination_retains_negative_and_null_results(self) -> None:
        path = self.root / "evidence/experiment_memory.jsonl"
        events = [{"experiment_id": "E0001", "event_type": "result_audited", "result_type": value}
                  for value in ("FALSIFYING", "NULL", "BOUNDARY", "SUPPORTING")]
        path.write_text("\n".join(json.dumps(x) for x in events) + "\n", encoding="utf-8")
        recent = history_view(self.root, experiment_id="E0001", limit=2)
        older = history_view(self.root, experiment_id="E0001", limit=2, before_line=recent["next_before_line"])
        self.assertEqual(["FALSIFYING", "NULL"], [x["event"]["result_type"] for x in older["items"]])
        self.assertEqual(2, recent["omitted"])

    def test_excerpt_marks_truncation_and_can_expand(self) -> None:
        path = self.root / "evidence/test.log"
        path.write_text("a"*100 + " FATAL\nnegative result\n", encoding="utf-8")
        short = excerpt(self.root, "evidence/test.log", max_chars=10)
        self.assertEqual(1, short["partial_line"])
        expanded = excerpt(self.root, "evidence/test.log", max_chars=1000)
        self.assertIn("FATAL", expanded["items"][0]["text"])
        self.assertIn("negative", expanded["items"][1]["text"])
        self.assertIsNone(expanded["next_start_line"])
        with self.assertRaises(ProtocolError):
            excerpt(self.root, "../escape.log")

    def test_cli_compatibility_full_state_and_exact_field(self) -> None:
        def command(*args: str) -> str:
            result = subprocess.run([sys.executable, str(self.root / "tools/state_manager.py"),
                "--root", str(self.root), "show", *args], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(0, result.returncode, result.stderr)
            return result.stdout
        self.assertEqual("orchestrator", json.loads(command())["role"])
        self.assertEqual(load_state(self.root), yaml.safe_load(command("--full")))
        self.assertEqual(load_state(self.root)["claims"], yaml.safe_load(command("--field", "claims")))

    def test_context_cli_checks_saved_view_freshness(self) -> None:
        command = [sys.executable, str(self.root / "tools/context_view.py"), "--root", str(self.root)]
        shown = subprocess.run([*command, "show"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, shown.returncode, shown.stderr)
        packet = json.loads(shown.stdout)
        (self.root / "view.json").write_text(json.dumps(packet), encoding="utf-8")
        fresh = subprocess.run([*command, "verify", "view.json"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, fresh.returncode, fresh.stderr)
        state = load_state(self.root)
        state["revision"] += 1
        atomic_yaml_write(self.root / "research/research_state.yaml", state)
        stale = subprocess.run([*command, "verify", "view.json"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(1, stale.returncode)
        self.assertFalse(json.loads(stale.stdout)["fresh"])

    def test_registry_cli_keeps_full_output_option(self) -> None:
        command = [sys.executable, str(self.root / "tools/experiment_registry.py"), "--root", str(self.root), "list"]
        compact = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, compact.returncode, compact.stderr)
        self.assertEqual({"items": [], "total": 0, "omitted": 0}, json.loads(compact.stdout))
        full = subprocess.run([*command, "--all"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, full.returncode, full.stderr)
        self.assertEqual([], yaml.safe_load(full.stdout))


if __name__ == "__main__":
    unittest.main()
