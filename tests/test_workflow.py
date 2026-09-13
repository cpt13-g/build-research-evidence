from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from common import ProtocolError, atomic_yaml_write, load_state  # noqa: E402
from experiment_registry import activate, approve, register, set_status  # noqa: E402
from result_recorder import record  # noqa: E402
from runner import run  # noqa: E402
from state_manager import update_gate  # noqa: E402
from validate_project import validate_project  # noqa: E402


class WorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in ("schemas", "templates", "tools", "research", "evidence", "experiments", ".agents", "docs"):
            source = ROOT / directory
            if source.exists():
                shutil.copytree(source, self.root / directory)

        state = yaml.safe_load((self.root / "templates" / "research_state.yaml").read_text(encoding="utf-8"))
        state["project"].update({"id": "toy-text-classification", "title": "Hierarchical pooling for long-text classification", "created_at": "2026-09-02T00:00:00Z", "updated_at": "2026-09-02T00:00:00Z"})
        state["status"] = "ACTIVE"
        state["current_stage"] = "S6_P0_MAIN_EXPERIMENTS"
        state["research_spine"].update({
            "research_question": "Does hierarchy-aware pooling improve long-text classification?",
            "problem_context": "Flat pooling may dilute section-level signals.",
            "core_hypothesis": "Preserving section hierarchy improves classification under a fair encoder budget.",
            "contributions": [{"id": "C1", "text": "Hierarchy-aware pooling"}],
            "primary_claims": ["C1"],
            "evaluation_goals": ["macro-F1"],
            "task_boundary": ["supervised long-text classification"],
            "exclusions": ["changing the task or label space"],
        })
        state["venue"] = {"target": "Example Venue", "status": "confirmed"}
        state["claims"] = [{"id": "C1", "text": "Hierarchy-aware pooling improves macro-F1"}]
        state["evidence_questions"] = [{"id": "P0-EQ1", "claim_id": "C1"}]
        state["experiment_contract"] = {"path": "research/experiment_contract.yaml", "version": 1, "status": "approved"}
        state["budget"]["limits"].update({"gpu_hours": 3, "wall_time_hours": 3, "max_full_runs": 3})
        state["human_gates"]["gate_1"] = "approved"
        atomic_yaml_write(self.root / "research" / "research_state.yaml", state)

        contract = yaml.safe_load((self.root / "templates" / "experiment_contract.yaml").read_text(encoding="utf-8"))
        contract["contract"]["status"] = "approved"
        contract["contract"]["claims"] = state["claims"]
        contract["contract"]["evidence_questions"] = state["evidence_questions"]
        contract["contract"]["datasets"] = ["toy-long-text"]
        contract["contract"]["data_splits"] = ["fixed-split-v1"]
        contract["contract"]["baselines"] = ["flat-pooling"]
        contract["contract"]["primary_metrics"] = ["macro-F1"]
        contract["contract"]["fairness_rules"] = ["same encoder and training budget"]
        contract["contract"]["stop_conditions"] = ["three full runs"]
        contract["contract"]["approval"] = {"gate": "gate_1", "status": "approved", "approved_by": "test-user", "approved_at": "2026-09-02T00:00:00Z"}
        atomic_yaml_write(self.root / "research" / "experiment_contract.yaml", contract)

        self._make_card("E0001", "P0")
        self._make_card("E0002", "P1")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _make_card(self, item_id: str, priority: str) -> None:
        card = yaml.safe_load((self.root / "templates" / "experiment_card.yaml").read_text(encoding="utf-8"))
        experiment = card["experiment"]
        experiment.update({
            "experiment_id": item_id,
            "priority": priority,
            "experiment_role": {"P0": "CORE_P0", "P1": "P1_SUPPORT", "P2": "P2_COMPLETENESS", "P3": "P3_OPTIONAL"}[priority],
            "purpose": "Test hierarchy-aware pooling under fixed controls.",
            "hypothesis": "Hierarchy-aware pooling improves macro-F1.",
            "datasets": ["toy-long-text"],
            "metrics": ["macro-F1"],
            "seed_protocol": {"seeds": [1, 2, 3]},
            "expected_supporting_result": "Positive multi-seed macro-F1 difference.",
            "falsifying_result": "No difference or a stable negative difference.",
            "estimated_budget": {"gpu_hours": 1},
            "expected_information_gain": "Resolves the primary performance uncertainty.",
            "stop_condition": "Stop after the approved run budget.",
        })
        path = self.root / "experiments" / item_id / "experiment_card.yaml"
        atomic_yaml_write(path, card)

    def test_project_protocols_validate(self) -> None:
        messages = validate_project(self.root)
        self.assertTrue(any("research/research_state.yaml" in message for message in messages))

    def test_p0_gate_run_result_and_resume(self) -> None:
        state = register(self.root, "experiments/E0001/experiment_card.yaml", 0)
        state = approve(self.root, "E0001", "orchestrator", state["revision"])
        state = register(self.root, "experiments/E0002/experiment_card.yaml", state["revision"])
        state = approve(self.root, "E0002", "orchestrator", state["revision"])

        with self.assertRaises(ProtocolError):
            activate(self.root, "E0002", state["revision"])

        state = activate(self.root, "E0001", state["revision"])
        self.assertEqual(state["budget"]["reserved"]["gpu_hours"], 1.0)
        metric_path = self.root / "experiments" / "E0001" / "raw_metrics.json"
        metric_path.write_text('{"macro_f1": 0.81}\n', encoding="utf-8")
        raw_path = run(self.root, "E0001", [sys.executable, "-c", "print('macro_f1=0.81')"], 10, [metric_path])
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["exit_code"], 0)
        self.assertEqual(raw["manifest_completeness"], "COMPLETE")
        self.assertIn("macro_f1=0.81", (raw_path.parent / "run.log").read_text(encoding="utf-8"))

        state = set_status(self.root, "E0001", "completed", state["revision"], "run completed")
        self.assertEqual(state["budget"]["reserved"]["gpu_hours"], 0.0)
        self.assertEqual(state["budget"]["used"]["gpu_hours"], 1.0)
        result_doc = yaml.safe_load((self.root / "templates" / "result_record.yaml").read_text(encoding="utf-8"))
        result_doc["result"].update({"experiment_id": "E0001", "run_id": raw["run_id"]})
        result_doc["result"]["execution"].update({"started_at": raw["started_at"], "ended_at": raw["ended_at"], "command": raw["command"], "run_manifest_path": raw["run_manifest_path"], "environment_path": raw["environment_path"], "log_path": raw["log_path"]})
        result_doc["result"]["metrics"] = {"macro_f1": 0.81}
        result_doc["result"]["audit"].update({"result_type": "SUPPORTING", "validity": "valid", "performance_value": "Positive primary metric.", "scientific_value": "Direct P0 evidence.", "claim_impact": {"C1": "supports"}, "confidence": "medium", "recommended_next_action": "Complete remaining seeds.", "audited_at": "2026-09-02T00:00:00Z"})
        result_doc["result"]["audit"]["diagnosis"].update({"diagnosis_id": "DG-E0001", "result_type": "SUPPORTING", "experiment_validity": "valid", "convergence_status": "converged", "baseline_fairness": "fair", "primary_observation": "Macro-F1 improved under fixed controls.", "claim_impact": {"C1": "supports"}, "performance_value": "Positive primary metric.", "scientific_value": "Direct P0 evidence.", "confidence": "medium", "failure_level": "NONE", "recommended_action": "ACCEPT"})
        incoming = self.root / "experiments" / "E0001" / "incoming_result.yaml"
        atomic_yaml_write(incoming, result_doc)
        result_doc["result"]["audit"]["independence"]["planner_interpretation_seen_before_verdict"] = True
        atomic_yaml_write(incoming, result_doc)
        with self.assertRaises(ProtocolError):
            record(self.root, incoming.relative_to(self.root).as_posix())
        result_doc["result"]["audit"]["independence"]["planner_interpretation_seen_before_verdict"] = False
        raw["manifest_completeness"] = "PARTIAL"
        raw["missing_declarations"] = ["seed_protocol"]
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        atomic_yaml_write(incoming, result_doc)
        with self.assertRaises(ProtocolError):
            record(self.root, incoming.relative_to(self.root).as_posix())
        raw["manifest_completeness"] = "COMPLETE"
        raw["missing_declarations"] = []
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        metric_path.write_text('{"macro_f1": 0.99}\n', encoding="utf-8")
        with self.assertRaises(ProtocolError):
            record(self.root, incoming.relative_to(self.root).as_posix())
        metric_path.write_text('{"macro_f1": 0.81}\n', encoding="utf-8")
        persisted = record(self.root, incoming.relative_to(self.root).as_posix())
        self.assertTrue(persisted.exists())
        state = set_status(self.root, "E0001", "audited", state["revision"], "auditor record persisted")
        state = update_gate(self.root, "gate_2", "approved", state["revision"], "test-user")
        state = activate(self.root, "E0002", state["revision"])
        self.assertIn("E0002", state["active_queue"])
        self.assertEqual(state["budget"]["reserved"]["gpu_hours"], 1.0)

        recovered = load_state(self.root)
        self.assertEqual(recovered["revision"], state["revision"])
        memory_lines = (self.root / "evidence" / "experiment_memory.jsonl").read_text(encoding="utf-8").splitlines()
        event_types = {json.loads(line)["event_type"] for line in memory_lines if line.strip()}
        self.assertIn("result_audited", event_types)
        self.assertIn("experiment_activated", event_types)


if __name__ == "__main__":
    unittest.main()
