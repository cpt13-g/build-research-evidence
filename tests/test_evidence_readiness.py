from __future__ import annotations

import hashlib
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
from evidence_builder import build_claim_evidence, build_completion_queue, finalize_venue_gap  # noqa: E402
from experiment_registry import activate  # noqa: E402
from readiness import assess_readiness, freeze_evidence  # noqa: E402
from report_builder import build_experiment_report, build_figure_table_plan  # noqa: E402


class EvidenceReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        state = load_state(self.root)
        state.update({"status": "ACTIVE", "current_stage": "S9_VENUE_EVIDENCE_AUDIT"})
        state["method_search"]["phase"] = "CONVERGED"
        state["current_method"] = {"id": "M2", "status": "converged", "artifact_path": "research/method/methods/M2.yaml"}
        state["venue"] = {"target": "ToyVenue", "status": "confirmed"}
        state["claims"] = [
            {"id": "C1", "statement": "The method improves the primary task.", "importance": "primary", "required_evidence": [{"evidence_type": "main_result", "description": "Controlled main result.", "experiment_ids": ["E1001"], "required": True, "reviewer_risk": "HIGH", "expected_information_gain": "HIGH", "estimated_cost": "LOW"}]},
            {"id": "C2", "statement": "The constraint is causally useful.", "importance": "secondary", "required_evidence": [{"evidence_type": "ablation", "description": "Constraint ablation is missing.", "experiment_ids": ["E1002"], "required": True, "reviewer_risk": "HIGH", "expected_information_gain": "HIGH", "estimated_cost": "LOW"}]},
        ]
        state["research_spine"].update({"research_question": "Toy question", "core_hypothesis": "Toy hypothesis", "primary_claims": [{"id": "C1"}], "secondary_claims": [{"id": "C2"}]})
        state["human_gates"] = {"gate_1": "approved", "gate_2": "approved", "gate_3": "not_ready"}
        atomic_yaml_write(self.root / "research" / "research_state.yaml", state)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _template(self, name: str) -> dict:
        return yaml.safe_load((self.root / "templates" / name).read_text(encoding="utf-8"))

    def _add_result(self, experiment_id: str, claim_id: str, result_type: str, *, formal: bool = True, valid: str = "valid", fair: str = "fair", confounds: list[str] | None = None) -> None:
        card = self._template("experiment_card.yaml")
        body = card["experiment"]
        body.update({
            "experiment_id": experiment_id, "claim_id": claim_id, "evidence_question_id": f"EQ-{claim_id}",
            "status": "approved", "priority": "P0" if formal else "P0_BLOCKER", "experiment_role": "CORE_P0" if formal else "P0_SUPPORT",
            "experiment_mode": "full_evaluation" if formal else "cheap_evaluation", "paper_evidence_eligible": formal,
            "evidence_label": "FORMAL_CLAIM_EVIDENCE" if formal else "PRELIMINARY_NON_PAPER", "candidate_id": None if formal else "MC-C1-01",
            "cheap_protocol": None if formal else {"dataset_fraction": 0.1, "epochs": 1, "seeds": [1], "shared_across_candidates": True, "proxy_risk": "proxy"},
            "seed_protocol": {"seeds": [1, 2, 3]}, "datasets": ["toy"], "metrics": ["score"], "estimated_budget": {"gpu_hours": 1},
        })
        card_path = self.root / "experiments" / experiment_id / "experiment_card.yaml"
        atomic_yaml_write(card_path, card)
        state = load_state(self.root)
        state["experiment_registry"].append({
            "id": experiment_id, "kind": "scientific", "priority": body["priority"], "experiment_role": body["experiment_role"],
            "experiment_mode": body["experiment_mode"], "paper_evidence_eligible": formal, "candidate_id": body["candidate_id"],
            "design_iteration_id": None, "status": "audited", "card_path": card_path.relative_to(self.root).as_posix(),
        })
        atomic_yaml_write(self.root / "research" / "research_state.yaml", state)
        result_doc = self._template("result_record.yaml")
        result = result_doc["result"]
        result.update({"record_id": f"R-{experiment_id}-001", "experiment_id": experiment_id, "run_id": f"run-{experiment_id}", "evidence_classification": "FORMAL_CLAIM_EVIDENCE" if formal else "PRELIMINARY_NON_PAPER"})
        run_dir = self.root / "experiments" / experiment_id / "runs" / f"run-{experiment_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_dir / "run.log"
        log_path.write_text("synthetic test run\n", encoding="utf-8")
        environment_path = run_dir / "environment.json"
        environment_path.write_text("{}\n", encoding="utf-8")
        metrics_path = run_dir / "raw_metrics.json"
        metrics_path.write_text('{"score": 1.0}\n', encoding="utf-8")
        manifest_path = run_dir / "run_manifest.json"
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0", "run_id": f"run-{experiment_id}", "experiment_id": experiment_id,
            "card_path": card_path.relative_to(self.root).as_posix(), "card_sha256": digest(card_path),
            "command": ["synthetic-test"], "started_at": "2026-09-02T00:00:00Z", "ended_at": "2026-09-02T00:00:01Z",
            "exit_code": 0, "timed_out": False, "log_path": log_path.relative_to(self.root).as_posix(),
            "environment_path": environment_path.relative_to(self.root).as_posix(), "environment_sha256": digest(environment_path),
            "code_identity": {"commit": None, "tracked_source_dirty": None, "src_tree_sha256": None, "configs_tree_sha256": None, "command_sha256": "0" * 64},
            "configuration_identity": {"card_revision": 1, "method_variant": {}, "config_tree_sha256": None},
            "data_identity": {"datasets": ["toy"], "seed_protocol": {"seeds": [1, 2, 3]}},
            "artifacts": [
                {"kind": "log", "path": log_path.relative_to(self.root).as_posix(), "sha256": digest(log_path), "size_bytes": log_path.stat().st_size},
                {"kind": "metrics", "path": metrics_path.relative_to(self.root).as_posix(), "sha256": digest(metrics_path), "size_bytes": metrics_path.stat().st_size},
            ],
            "manifest_completeness": "COMPLETE", "missing_declarations": [], "run_manifest_path": manifest_path.relative_to(self.root).as_posix(),
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result["execution"].update({"run_manifest_path": manifest["run_manifest_path"], "environment_path": manifest["environment_path"], "log_path": manifest["log_path"], "command": manifest["command"]})
        audit = result["audit"]
        audit.update({"result_type": result_type, "validity": valid, "claim_impact": {claim_id: result_type.lower()}, "confidence": "high", "audited_at": "2026-09-02T00:00:00Z"})
        audit["diagnosis"].update({
            "diagnosis_id": f"DG-{experiment_id}", "result_type": result_type, "experiment_validity": valid, "convergence_status": "converged",
            "baseline_fairness": fair, "claim_impact": audit["claim_impact"], "confidence": "high", "unresolved_confounders": confounds or [],
            "recommended_action": "ACCEPT" if result_type == "SUPPORTING" else "KEEP_AS_BOUNDARY_EVIDENCE" if result_type in {"BOUNDARY", "NULL"} else "STOP",
        })
        result_path = self.root / "experiments" / experiment_id / "results" / f"R-{experiment_id}-001.yaml"
        atomic_yaml_write(result_path, result_doc)

    def _venue(self, gaps: list[dict] | None = None, name: str = "venue_input.yaml") -> str:
        doc = self._template("venue_gap.yaml")
        doc.update({"venue": "ToyVenue", "search_date": "2026-09-02", "search_stopped": True, "stop_reason": "Five papers established stable expectations.", "gaps": gaps or []})
        path = self.root / "evidence" / name
        atomic_yaml_write(path, doc)
        return path.relative_to(self.root).as_posix()

    def test_01_cheap_evaluation_is_excluded_from_formal_claim_evidence(self) -> None:
        self._add_result("E1001", "C1", "SUPPORTING")
        self._add_result("E1999", "C1", "SUPPORTING", formal=False)
        matrix = build_claim_evidence(self.root)
        self.assertIn("E1999", matrix["excluded_preliminary_experiments"])
        formal_ids = {item["experiment_id"] for item in matrix["claims"][0]["supporting_experiments"]}
        self.assertEqual(formal_ids, {"E1001"})

    def test_02_converged_method_does_not_imply_sufficient_evidence(self) -> None:
        matrix = build_claim_evidence(self.root)
        self.assertEqual(matrix["method_status"], "CONVERGED")
        self.assertEqual(matrix["evidence_status"], "INCOMPLETE")
        self.assertNotEqual(matrix["claim_status"], "SUPPORTED")

    def test_03_missing_primary_evidence_is_not_ready(self) -> None:
        build_claim_evidence(self.root)
        finalize_venue_gap(self.root, self._venue())
        build_completion_queue(self.root)
        readiness = assess_readiness(self.root)
        self.assertEqual(readiness["readiness"], "NOT_READY")
        self.assertFalse(readiness["hard_gates"]["primary_claim_has_evidence"])

    def test_04_venue_common_but_claim_irrelevant_is_skip_or_p3(self) -> None:
        gap = {"evidence_type": "extra_dataset", "claim_ids": [], "current_status": "MISSING", "venue_commonality": "HIGH", "claim_relevance": "LOW", "reviewer_risk": "MEDIUM", "expected_information_gain": "LOW", "estimated_cost": "HIGH", "recommendation": "P1", "reason": "Common but unrelated to the Claims."}
        venue = finalize_venue_gap(self.root, self._venue([gap]))
        self.assertIn(venue["gaps"][0]["recommendation"], {"P3", "SKIP"})

    def test_05_only_p1_enters_default_completion_recommendations(self) -> None:
        build_claim_evidence(self.root)
        low_gap = {"evidence_type": "extra_dataset", "claim_ids": [], "current_status": "MISSING", "venue_commonality": "HIGH", "claim_relevance": "LOW", "reviewer_risk": "HIGH", "expected_information_gain": "LOW", "estimated_cost": "LOW", "recommendation": "P3", "reason": "Low Claim relevance."}
        finalize_venue_gap(self.root, self._venue([low_gap]))
        queue = build_completion_queue(self.root)
        priorities = {item["recommendation_id"]: item["priority"] for item in queue["items"]}
        self.assertTrue(queue["active_recommendations"])
        self.assertTrue(all(priorities[item] == "P1" for item in queue["active_recommendations"]))
        self.assertTrue(all(not item["recommended_for_execution"] for item in queue["items"] if item["priority"] == "P3"))

    def test_06_negative_and_boundary_results_are_preserved(self) -> None:
        self._add_result("E1001", "C1", "SUPPORTING")
        self._add_result("E1002", "C2", "BOUNDARY")
        matrix = build_claim_evidence(self.root)
        c2 = next(claim for claim in matrix["claims"] if claim["claim_id"] == "C2")
        self.assertEqual(c2["boundary_experiments"][0]["experiment_id"], "E1002")

    def test_07_freeze_blocks_ordinary_experiment_activation(self) -> None:
        self._add_result("E1001", "C1", "SUPPORTING")
        self._add_result("E1002", "C2", "SUPPORTING")
        build_claim_evidence(self.root)
        finalize_venue_gap(self.root, self._venue())
        build_completion_queue(self.root)
        build_figure_table_plan(self.root)
        assess_readiness(self.root)
        state = load_state(self.root)
        state["human_gates"]["gate_3"] = "approved"
        atomic_yaml_write(self.root / "research" / "research_state.yaml", state)
        frozen = freeze_evidence(self.root, state["revision"], "test-user", "Evidence is complete.")
        self.assertEqual(frozen["status"], "EVIDENCE_FROZEN")
        with self.assertRaises(ProtocolError):
            activate(self.root, "E1001", frozen["revision"])

    def test_08_toy_e2e_completion_freeze_report_and_recovery(self) -> None:
        self._add_result("E1001", "C1", "SUPPORTING")
        self._add_result("E1003", "C2", "BOUNDARY")
        first = build_claim_evidence(self.root)
        self.assertEqual(next(c for c in first["claims"] if c["claim_id"] == "C1")["status"], "SUPPORTED")
        self.assertEqual(next(c for c in first["claims"] if c["claim_id"] == "C2")["status"], "PARTIAL")
        ablation_gap = {"evidence_type": "ablation", "claim_ids": ["C2"], "current_status": "MISSING", "venue_commonality": "HIGH", "claim_relevance": "HIGH", "reviewer_risk": "HIGH", "expected_information_gain": "HIGH", "estimated_cost": "LOW", "recommendation": "P2", "reason": "Directly tests the C2 mechanism."}
        finalize_venue_gap(self.root, self._venue([ablation_gap]))
        first_queue = build_completion_queue(self.root)
        self.assertTrue(any(item["priority"] == "P1" and "C2" in item["claim_ids"] for item in first_queue["items"]))

        self._add_result("E1002", "C2", "SUPPORTING")
        state = load_state(self.root)
        completed = build_claim_evidence(self.root, state["revision"])
        self.assertEqual(next(c for c in completed["claims"] if c["claim_id"] == "C2")["status"], "SUPPORTED")
        ablation_gap["current_status"] = "COMPLETE"
        state = load_state(self.root)
        finalize_venue_gap(self.root, self._venue([ablation_gap], "venue_complete.yaml"), state["revision"])
        state = load_state(self.root)
        final_queue = build_completion_queue(self.root, state["revision"])
        self.assertFalse(final_queue["active_recommendations"])
        plan_path = build_figure_table_plan(self.root)
        state = load_state(self.root)
        readiness = assess_readiness(self.root, state["revision"])
        self.assertIn(readiness["readiness"], {"A", "B"})
        state = load_state(self.root)
        state["human_gates"]["gate_3"] = "approved"
        atomic_yaml_write(self.root / "research" / "research_state.yaml", state)
        freeze_evidence(self.root, state["revision"], "test-user", "Primary and required supporting evidence are complete.")
        report_path = build_experiment_report(self.root)

        recovered = load_state(self.root)
        recovered_matrix = yaml.safe_load((self.root / recovered["evidence"]["claim_evidence_path"]).read_text(encoding="utf-8"))
        recovered_readiness = yaml.safe_load((self.root / recovered["evidence"]["readiness_path"]).read_text(encoding="utf-8"))
        self.assertEqual(recovered["status"], "EVIDENCE_FROZEN")
        self.assertEqual(recovered["evidence"]["claim_status"], "SUPPORTED")
        self.assertIn(recovered["evidence"]["submission_readiness"], {"A", "B"})
        self.assertEqual(recovered_matrix["evidence_status"], "SUFFICIENT")
        self.assertIn(recovered_readiness["readiness"], {"A", "B"})
        self.assertTrue(plan_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Negative / Boundary Findings", report_text)
        self.assertIn("E1003", report_text)


if __name__ == "__main__":
    unittest.main()
