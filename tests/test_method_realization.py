from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from common import ProtocolError, atomic_yaml_write, load_state, save_state  # noqa: E402
from experiment_registry import activate, approve, register, set_status  # noqa: E402
from method_search import (  # noqa: E402
    MethodBudgetRequired,
    add_candidate,
    advance_phase,
    apply_candidate_decision,
    apply_design_iteration,
    assess_hypothesis_risk,
    build_gate2_summary,
    record_candidate_outcome,
    record_screening,
    register_design_envelope,
    register_design_iteration,
    register_functional_requirement,
    start_search,
)
from result_recorder import record  # noqa: E402
from runner import run  # noqa: E402


class MethodRealizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in ("schemas", "templates", "tools", "research", "evidence", "experiments", ".agents", "docs"):
            source = ROOT / directory
            if source.exists():
                shutil.copytree(source, self.root / directory)
        state = self._template("research_state.yaml")
        state["project"].update({"id": "toy-multisource-sequence", "title": "Hierarchical multi-source sequence classification", "created_at": "2026-09-02T00:00:00Z", "updated_at": "2026-09-02T00:00:00Z"})
        state["status"] = "ACTIVE"
        state["current_stage"] = "S3_METHOD_REALIZATION"
        state["research_spine"].update({
            "research_question": "Can hierarchical source representations improve multi-source sequence classification?",
            "problem_context": "Flat concatenation can erase source identity and cross-level interactions.",
            "core_hypothesis": "A hierarchy-aware fusion mechanism preserves source-specific signals and improves classification.",
            "contributions": [{"id": "C1", "text": "Hierarchy-aware multi-source fusion"}],
            "primary_claims": ["C1"],
            "evaluation_goals": ["accuracy", "macro-F1"],
            "task_boundary": ["multi-source sequence classification"],
            "exclusions": ["changing labels", "changing task", "hiding failure with a new metric"],
        })
        state["venue"] = {"target": "Toy AI Venue", "status": "confirmed"}
        state["claims"] = [{"id": "C1", "text": "Hierarchy-aware fusion improves fair multi-source classification"}]
        state["evidence_questions"] = [{"id": "P0-EQ1", "claim_id": "C1", "text": "Does hierarchy-aware fusion improve Accuracy/F1?"}]
        state["budget"]["limits"].update({"gpu_hours": 20, "wall_time_hours": 20, "max_full_runs": 10})
        state["method_search"]["budget"]["limits"].update({"max_initial_candidates": 5, "max_cheap_candidates": 3, "max_full_candidates": 2, "max_design_iterations": 3, "max_reopen_search": 1, "max_candidate_failures": 3})
        atomic_yaml_write(self.root / "research" / "research_state.yaml", state)
        atomic_yaml_write(self.root / "research" / "experiment_contract.yaml", self._template("experiment_contract.yaml"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _template(self, name: str) -> dict:
        return yaml.safe_load((self.root / "templates" / name).read_text(encoding="utf-8"))

    def _write(self, relative: str, document: dict) -> str:
        path = self.root / relative
        atomic_yaml_write(path, document)
        return path.relative_to(self.root).as_posix()

    def _prepare_search(self, candidate_count: int = 3) -> dict:
        requirement = self._template("functional_requirement.yaml")
        requirement["functional_requirement"].update({
            "research_problem": "Flat fusion loses source identity and level-specific interactions.",
            "observed_or_expected_failure": "Short dominant sources overwhelm weak but complementary sources.",
            "hypothesized_cause": "One-shot concatenation lacks source-preserving hierarchy and gated interaction.",
            "required_capability": ["preserve source identity", "interact across source and hierarchy levels"],
            "validation_target": ["macro-F1", "source-gate selectivity"],
            "status": "active",
        })
        requirement_path = self._write("research/method/functional_requirements/FR-C1.yaml", requirement)
        state = register_functional_requirement(self.root, requirement_path, 0)

        envelope = self._template("design_envelope.yaml")
        envelope["design_envelope"].update({
            "scientific_goal": "Realize hierarchy-aware multi-source fusion.",
            "problem_to_solve": "Source identity loss and late cross-level interaction.",
            "required_capabilities": requirement["functional_requirement"]["required_capability"],
            "allowed_design_dimensions": ["representation", "fusion", "interaction", "routing"],
            "status": "active",
        })
        envelope_path = self._write("research/method/design_envelopes/DE-C1.yaml", envelope)
        state = register_design_envelope(self.root, envelope_path, state["revision"])
        state = start_search(self.root, "C1", "DE-C1", state["revision"])

        mechanisms = [
            ("MC-C1-01", "Hierarchical gated fusion", "Source-level encoders feed level-wise gates before aggregation.", ["representation", "fusion", "routing"], "high", "direct"),
            ("MC-C1-02", "Cross-level source attention", "Source tokens attend within level before a controlled cross-level attention pass.", ["representation", "interaction", "fusion"], "medium", "direct"),
            ("MC-C1-03", "Wide flat attention", "A larger flat attention layer concatenates all sources.", ["interaction"], "high", "weak"),
            ("MC-C1-04", "Source adapters", "Source-specific adapters preserve identity before compact fusion.", ["representation", "fusion"], "medium", "direct"),
            ("MC-C1-05", "Dynamic source routing", "Input-conditioned routing selects source pathways at each hierarchy level.", ["routing", "interaction"], "high", "direct"),
            ("MC-C1-06", "Extra candidate", "A sixth mechanism should be rejected by the hard exploration cap.", ["fusion"], "low", "direct"),
        ]
        for candidate_id, name, algorithm, dimensions, complexity, alignment in mechanisms[:candidate_count]:
            candidate = self._template("candidate_mechanism.yaml")
            candidate["candidate"].update({
                "candidate_id": candidate_id,
                "mechanism_name": name,
                "mechanism_summary": algorithm,
                "problem_addressed": "Source identity loss and insufficient cross-level interaction.",
                "scientific_rationale": "The mechanism instantiates the required source-preserving hierarchical capability.",
                "architecture_or_algorithm": algorithm,
                "expected_effect": "Improve macro-F1 and source-sensitive intermediate behavior.",
                "differentiator_from_baseline": "Changes interaction structure under a controlled encoder and training budget.",
                "validation_hook": "Measure gate/attention selectivity by source and hierarchy level.",
                "ablation_hook": "Remove hierarchical interaction while retaining parameter budget.",
                "failure_interpretation": "Failure rejects this realization, not the Research Idea by itself.",
                "implementation_complexity": complexity,
                "claim_alignment": {"C1": alignment},
                "design_dimensions": dimensions,
                "estimated_cost": {"gpu_hours": 1},
            })
            candidate_path = self._write(f"research/method/candidates/{candidate_id}.yaml", candidate)
            state = add_candidate(self.root, candidate_path, state["revision"])
        return state

    def _screen_to_cheap(self, state: dict, passed: tuple[str, ...] = ("MC-C1-01", "MC-C1-02")) -> dict:
        state = advance_phase(self.root, "SCREEN", state["revision"], "Three mechanisms are ready for conceptual screening.")
        for candidate_id in list(state["method_search"]["active_candidate_ids"]):
            screening = self._template("candidate_screening.yaml")
            screening["screening"].update({"screening_id": f"CS-{candidate_id[3:]}", "candidate_id": candidate_id})
            if candidate_id in passed:
                screening["screening"].update({"decision": "PASS", "recommended_for_cheap_evaluation": True, "rationale": "Direct Claim alignment, feasible validation, fair comparison, and acceptable cost."})
                screening["screening"]["scores"].update({"claim_alignment": 5, "scientific_rationale": 5, "expected_evidence_strength": 4, "interpretability": 4, "ablation_feasibility": 4, "implementation_feasibility": 4, "compute_cost": 3, "complexity": 3, "risk": 3})
            else:
                screening["screening"].update({"decision": "REJECT", "recommended_for_cheap_evaluation": False, "rationale": "The expected gain is dominated by scale and weakly tied to C1."})
                screening["screening"]["hard_checks"]["scale_gain_not_primary"] = False
            path = self._write(f"research/method/screenings/{screening['screening']['screening_id']}.yaml", screening)
            state = record_screening(self.root, path, state["revision"])
        return advance_phase(self.root, "CHEAP_EVALUATE", state["revision"], "Conceptual screening retained bounded candidates.")

    def _make_card(self, item_id: str, candidate_id: str | None, *, mode: str, role: str, priority: str, iteration_id: str | None = None) -> str:
        card = self._template("experiment_card.yaml")
        body = card["experiment"]
        body.update({
            "experiment_id": item_id,
            "candidate_id": candidate_id,
            "design_iteration_id": iteration_id,
            "experiment_mode": mode,
            "experiment_role": role,
            "priority": priority,
            "paper_evidence_eligible": mode != "cheap_evaluation",
            "evidence_label": "PRELIMINARY_NON_PAPER" if mode == "cheap_evaluation" else "FORMAL_CLAIM_EVIDENCE",
            "cheap_protocol": {"dataset_fraction": 0.2, "epochs": 2, "seeds": [7], "shared_across_candidates": True, "proxy_risk": "Short training may alter final ranking."} if mode == "cheap_evaluation" else None,
            "purpose": f"Evaluate {candidate_id or iteration_id} under {mode}.",
            "hypothesis": "The mechanism improves macro-F1 and expected intermediate behavior.",
            "datasets": ["toy-multisource"],
            "baselines": ["flat-concatenation"],
            "metrics": ["accuracy", "macro-F1"],
            "seed_protocol": {"seeds": [7]},
            "estimated_budget": {"gpu_hours": 1},
            "expected_supporting_result": "Positive controlled metric and mechanism-specific behavior.",
            "falsifying_result": "Stable null/negative controlled result without confounds.",
            "expected_information_gain": "Determines whether this mechanism merits deeper evaluation.",
            "stop_condition": "Stop after the declared protocol.",
        })
        return self._write(f"experiments/{item_id}/experiment_card.yaml", card)

    def _execute_and_audit(self, state: dict, item_id: str, card_path: str, *, metric: float, result_type: str, failure_level: str = "NONE", action: str = "FULL_EVALUATION", scientific_value: str = "Discriminates candidate viability.", suspected_dimensions: list[str] | None = None) -> tuple[dict, str]:
        if state["human_gates"]["gate_1"] != "approved":
            state = self._approve_contract(state)
        state = register(self.root, card_path, state["revision"])
        state = approve(self.root, item_id, "orchestrator", state["revision"])
        state = activate(self.root, item_id, state["revision"])
        metric_path = self.root / "experiments" / item_id / "raw_metrics.json"
        metric_path.write_text(json.dumps({"macro_f1": metric}), encoding="utf-8")
        raw_path = run(self.root, item_id, [sys.executable, "-c", f"print('macro_f1={metric}')"], 10, [metric_path])
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        state = set_status(self.root, item_id, "completed", state["revision"], "run completed")
        result_doc = self._template("result_record.yaml")
        result = result_doc["result"]
        result.update({"record_id": f"R-{item_id}-001", "experiment_id": item_id, "run_id": raw["run_id"], "metrics": {"macro_f1": metric}})
        experiment_ref = next(entry for entry in state["experiment_registry"] if entry["id"] == item_id)
        result["evidence_classification"] = "PRELIMINARY_NON_PAPER" if experiment_ref["experiment_mode"] == "cheap_evaluation" else "FORMAL_CLAIM_EVIDENCE"
        result["execution"].update({"started_at": raw["started_at"], "ended_at": raw["ended_at"], "command": raw["command"], "run_manifest_path": raw["run_manifest_path"], "environment_path": raw["environment_path"], "log_path": raw["log_path"]})
        audit = result["audit"]
        audit.update({"result_type": result_type, "validity": "valid", "performance_value": f"macro-F1={metric}", "scientific_value": scientific_value, "claim_impact": {"C1": "supports" if result_type == "SUPPORTING" else "unresolved"}, "confidence": "medium", "recommended_next_action": action, "audited_at": "2026-09-02T00:00:00Z"})
        causes = [] if not suspected_dimensions else [{"cause": "Interaction stage mismatch", "design_dimensions": suspected_dimensions}]
        audit["diagnosis"].update({"diagnosis_id": f"DG-{item_id}", "result_type": result_type, "experiment_validity": "valid", "convergence_status": "converged", "baseline_fairness": "fair", "primary_observation": f"Controlled macro-F1 was {metric}.", "claim_impact": audit["claim_impact"], "performance_value": audit["performance_value"], "scientific_value": scientific_value, "confidence": "medium", "suspected_causes": causes, "failure_level": failure_level, "recommended_action": action})
        incoming = self._write(f"experiments/{item_id}/incoming_result.yaml", result_doc)
        persisted = record(self.root, incoming)
        state = set_status(self.root, item_id, "audited", state["revision"], "structured audit persisted")
        return state, persisted.relative_to(self.root).as_posix()

    def _approve_contract(self, state: dict) -> dict:
        contract = self._template("experiment_contract.yaml")
        contract["contract"].update({"status": "approved", "claims": state["claims"], "evidence_questions": state["evidence_questions"], "datasets": ["toy-multisource"], "data_splits": ["fixed-v1"], "baselines": ["flat-concatenation"], "primary_metrics": ["accuracy", "macro-F1"], "fairness_rules": ["same data, encoder capacity, optimization and cheap protocol"], "stop_conditions": ["declared card stop condition"]})
        contract["contract"]["approval"] = {"gate": "gate_1", "status": "approved", "approved_by": "test-user", "approved_at": "2026-09-02T00:00:00Z"}
        atomic_yaml_write(self.root / "research" / "experiment_contract.yaml", contract)
        state["experiment_contract"] = {"path": "research/experiment_contract.yaml", "version": 1, "status": "approved"}
        state["human_gates"]["gate_1"] = "approved"
        return save_state(self.root, state, expected_revision=state["revision"], event_type="test_gate_1", event={"actor": "test-user"})

    def test_01_single_candidate_failure_does_not_trigger_hypothesis_risk(self) -> None:
        state = load_state(self.root)
        state["method_search"]["reasonable_candidates_tested"] = 1
        state["method_search"]["consistent_negative_results"] = 1
        state = save_state(self.root, state, expected_revision=0, event_type="test_single_failure", event={})
        with self.assertRaises(ProtocolError):
            assess_hypothesis_risk(self.root, {"implementation_validated": True, "baseline_validated": True, "evaluation_valid": True, "results_consistently_negative": True, "major_confounds_resolved": True}, state["revision"])
        self.assertEqual(load_state(self.root)["status"], "ACTIVE")

    def test_02_method_change_without_diagnosis_is_rejected(self) -> None:
        state = self._prepare_search(2)
        state["method_search"]["phase"] = "REFINE"
        state["current_method"] = {"id": "M1", "status": "full_evaluated"}
        state = save_state(self.root, state, expected_revision=state["revision"], event_type="test_refine_setup", event={})
        iteration = self._template("design_iteration.yaml")
        iteration["design_iteration"]["diagnosis"] = ""
        path = self._write("research/method/design_iterations/D0001.yaml", iteration)
        with self.assertRaises(ProtocolError):
            register_design_iteration(self.root, path, state["revision"])

    def test_03_p2_remains_blocked_before_p0_completion(self) -> None:
        state = load_state(self.root)
        state = self._approve_contract(state)
        core = self._make_card("E0001", None, mode="full_evaluation", role="CORE_P0", priority="P0")
        p2 = self._make_card("E0002", None, mode="diagnostic", role="P2_COMPLETENESS", priority="P2")
        state = register(self.root, core, state["revision"])
        state = approve(self.root, "E0001", "orchestrator", state["revision"])
        state = register(self.root, p2, state["revision"])
        state = approve(self.root, "E0002", "orchestrator", state["revision"])
        with self.assertRaises(ProtocolError):
            activate(self.root, "E0002", state["revision"])

    def test_04_cheap_evaluation_is_blocked_before_gate1(self) -> None:
        state = self._screen_to_cheap(self._prepare_search(2), passed=("MC-C1-01", "MC-C1-02"))
        card = self._make_card("E0101", "MC-C1-01", mode="cheap_evaluation", role="P0_SUPPORT", priority="P0_BLOCKER")
        state = register(self.root, card, state["revision"])
        state = approve(self.root, "E0101", "orchestrator", state["revision"])
        with self.assertRaises(ProtocolError):
            activate(self.root, "E0101", state["revision"])
        state = self._approve_contract(state)
        state = activate(self.root, "E0101", state["revision"])
        self.assertIn("E0101", state["active_queue"])
        self.assertEqual(state["human_gates"]["gate_1"], "approved")
        unfair_card_path = self._make_card("E0102", "MC-C1-02", mode="cheap_evaluation", role="P0_SUPPORT", priority="P0_BLOCKER")
        unfair_card = yaml.safe_load((self.root / unfair_card_path).read_text(encoding="utf-8"))
        unfair_card["experiment"]["cheap_protocol"]["epochs"] = 4
        atomic_yaml_write(self.root / unfair_card_path, unfair_card)
        state = register(self.root, unfair_card_path, state["revision"])
        state = approve(self.root, "E0102", "orchestrator", state["revision"])
        with self.assertRaises(ProtocolError):
            activate(self.root, "E0102", state["revision"])

    def test_05_active_explore_has_hard_five_candidate_cap(self) -> None:
        state = self._prepare_search(5)
        state["method_search"]["budget"]["limits"]["max_initial_candidates"] = 6
        state = save_state(self.root, state, expected_revision=state["revision"], event_type="test_raise_budget", event={})
        candidate = self._template("candidate_mechanism.yaml")
        candidate["candidate"].update({"candidate_id": "MC-C1-06", "mechanism_name": "Sixth", "mechanism_summary": "Sixth bounded mechanism.", "problem_addressed": "Same problem.", "scientific_rationale": "Same capability.", "architecture_or_algorithm": "Controlled fusion.", "expected_effect": "Expected behavior.", "differentiator_from_baseline": "Fusion only.", "validation_hook": "Intermediate measure.", "ablation_hook": "Remove fusion.", "failure_interpretation": "Candidate-specific.", "design_dimensions": ["fusion"]})
        path = self._write("research/method/candidates/MC-C1-06.yaml", candidate)
        with self.assertRaises(ProtocolError):
            add_candidate(self.root, path, state["revision"])

    def test_06_refine_cannot_generate_new_candidates_without_reopen(self) -> None:
        state = self._prepare_search(2)
        state["method_search"]["phase"] = "REFINE"
        state = save_state(self.root, state, expected_revision=state["revision"], event_type="test_refine", event={})
        candidate = self._template("candidate_mechanism.yaml")
        candidate["candidate"]["candidate_id"] = "MC-C1-99"
        path = self._write("research/method/candidates/MC-C1-99.yaml", candidate)
        with self.assertRaises(ProtocolError):
            add_candidate(self.root, path, state["revision"])

    def test_07_null_result_is_saved_with_scientific_value(self) -> None:
        state = self._screen_to_cheap(self._prepare_search(2), passed=("MC-C1-01",))
        card = self._make_card("E0101", "MC-C1-01", mode="cheap_evaluation", role="P0_SUPPORT", priority="P0_BLOCKER")
        state, result_path = self._execute_and_audit(state, "E0101", card, metric=0.50, result_type="NULL", scientific_value="The candidate does not separate from the baseline under the shared proxy.", action="REJECT_CANDIDATE", failure_level="F2_METHOD")
        result = yaml.safe_load((self.root / result_path).read_text(encoding="utf-8"))
        self.assertEqual(result["result"]["audit"]["result_type"], "NULL")
        self.assertTrue(result["result"]["audit"]["scientific_value"])

    def test_08_cheap_result_cannot_be_formal_evidence(self) -> None:
        state = self._screen_to_cheap(self._prepare_search(2), passed=("MC-C1-01",))
        state = self._approve_contract(state)
        card_path = self._make_card("E0101", "MC-C1-01", mode="cheap_evaluation", role="P0_SUPPORT", priority="P0_BLOCKER")
        state = register(self.root, card_path, state["revision"])
        state = approve(self.root, "E0101", "orchestrator", state["revision"])
        state = activate(self.root, "E0101", state["revision"])
        state = set_status(self.root, "E0101", "completed", state["revision"], "synthetic run completed")
        result = self._template("result_record.yaml")
        result["result"].update({"experiment_id": "E0101", "record_id": "R-E0101-FORMAL", "evidence_classification": "FORMAL_CLAIM_EVIDENCE"})
        path = self._write("experiments/E0101/invalid_formal_result.yaml", result)
        with self.assertRaises(ProtocolError):
            record(self.root, path)

    def test_09_method_search_budget_exhaustion_requests_user_decision(self) -> None:
        state = load_state(self.root)
        state["method_search"]["budget"]["limits"]["max_initial_candidates"] = 2
        atomic_yaml_write(self.root / "research" / "research_state.yaml", state)
        state = self._prepare_search(2)
        candidate = self._template("candidate_mechanism.yaml")
        candidate["candidate"]["candidate_id"] = "MC-C1-03"
        path = self._write("research/method/candidates/MC-C1-03.yaml", candidate)
        with self.assertRaises(MethodBudgetRequired):
            add_candidate(self.root, path, state["revision"])
        recovered = load_state(self.root)
        self.assertEqual(recovered["status"], "BUDGET_EXTENSION_REQUIRED")
        self.assertEqual(recovered["method_search"]["budget"]["extension_status"], "recommended")

    def test_10_end_to_end_method_realization_refinement_and_recovery(self) -> None:
        state = self._screen_to_cheap(self._prepare_search(3))
        cheap_results: dict[str, str] = {}
        for item_id, candidate_id, metric in (("E0101", "MC-C1-01", 0.79), ("E0102", "MC-C1-02", 0.77)):
            card = self._make_card(item_id, candidate_id, mode="cheap_evaluation", role="P0_SUPPORT", priority="P0_BLOCKER")
            state, result_path = self._execute_and_audit(state, item_id, card, metric=metric, result_type="SUPPORTING", action="FULL_EVALUATION")
            state = record_candidate_outcome(self.root, candidate_id, result_path, state["revision"])
            cheap_results[candidate_id] = result_path
        state = advance_phase(self.root, "SELECT", state["revision"], "Two Candidates completed the same Cheap Protocol.")

        decision = self._template("candidate_decision.yaml")
        decision["candidate_decision"].update({
            "selected": ["MC-C1-02"],
            "reserve": ["MC-C1-01"],
            "rejected": [{"candidate_id": "MC-C1-03", "reason": "Scale-dominated and weak Claim alignment."}],
            "rationale": "MC-C1-02 is slightly lower on proxy F1 but has clearer C1 alignment, a direct attention validation hook, lower complexity, and stronger fair ablation.",
            "metric_tradeoff": "Selects 0.77 rather than the proxy-best 0.79.",
            "scientific_tradeoff": "Accepts a small proxy loss for stronger interpretability and evidence strength.",
        })
        decision_path = self._write("research/method/decisions/CD-C1-01.yaml", decision)
        state = apply_candidate_decision(self.root, decision_path, state["revision"])
        self.assertEqual(state["current_method"]["source_candidate_id"], "MC-C1-02")
        state = self._approve_contract(state)

        full_card = self._make_card("E0201", "MC-C1-02", mode="full_evaluation", role="CORE_P0", priority="P0")
        state, full_result_path = self._execute_and_audit(state, "E0201", full_card, metric=0.74, result_type="NULL", failure_level="F2_METHOD", action="REFINE_METHOD", scientific_value="Full evaluation reveals a stable boundary: cross-level interaction occurs too late.", suspected_dimensions=["fusion"])
        state = record_candidate_outcome(self.root, "MC-C1-02", full_result_path, state["revision"])
        with self.assertRaises(ProtocolError):
            assess_hypothesis_risk(self.root, {"implementation_validated": True, "baseline_validated": True, "evaluation_valid": True, "results_consistently_negative": True, "major_confounds_resolved": True}, state["revision"])
        state = advance_phase(self.root, "REFINE", state["revision"], "Valid F2 diagnosis identifies late fusion as the specific cause.")

        invalid_iteration = self._template("design_iteration.yaml")
        invalid_iteration["design_iteration"].update({"diagnosis": "", "parent_method_id": "M1", "evidence": [full_result_path]})
        invalid_path = self._write("research/method/design_iterations/D9999.yaml", invalid_iteration)
        with self.assertRaises(ProtocolError):
            register_design_iteration(self.root, invalid_path, state["revision"])

        iteration = self._template("design_iteration.yaml")
        iteration["design_iteration"].update({
            "iteration_id": "D0001",
            "parent_method_id": "M1",
            "trigger_experiment": "E0201",
            "diagnosis_id": "DG-E0201",
            "diagnosis": "Cross-level interaction occurs after source evidence has already been compressed.",
            "evidence": [full_result_path],
            "proposed_change": "Move controlled cross-source fusion before final level aggregation.",
            "affected_design_dimensions": ["fusion"],
            "scientific_reason": "Earlier fusion preserves the required complementary source signal.",
            "expected_effect": "Recover source-sensitive attention and improve macro-F1.",
            "status": "approved",
        })
        iteration["design_iteration"]["approved_scope"] = {"allowed_dimensions": ["fusion"], "approved_by": "orchestrator", "approved_at": "2026-09-02T00:00:00Z"}
        iteration_path = self._write("research/method/design_iterations/D0001.yaml", iteration)
        state = register_design_iteration(self.root, iteration_path, state["revision"])
        state = apply_design_iteration(self.root, "D0001", state["revision"])
        self.assertEqual(state["current_method"]["id"], "M2")

        refine_card = self._make_card("E0301", "MC-C1-02", mode="refinement_validation", role="P0_SUPPORT", priority="P0_BLOCKER", iteration_id="D0001")
        state, _ = self._execute_and_audit(state, "E0301", refine_card, metric=0.82, result_type="SUPPORTING", action="ACCEPT", scientific_value="The targeted fusion-stage change restores the expected behavior and improves the primary metric.")
        state = advance_phase(self.root, "CONVERGED", state["revision"], "Targeted refinement passed its rejection condition and P0 validation.")

        recovered = load_state(self.root)
        self.assertEqual(recovered["method_search"]["phase"], "CONVERGED")
        self.assertEqual(recovered["current_method"]["id"], "M2")
        self.assertEqual(recovered["current_method"]["status"], "converged")
        lineage = yaml.safe_load((self.root / recovered["method_search"]["method_lineage_path"]).read_text(encoding="utf-8"))
        self.assertEqual(lineage["lineage"]["current_method_id"], "M2")
        self.assertEqual(len(lineage["lineage"]["edges"]), 1)
        summary_path = build_gate2_summary(self.root, "reports/GATE2_SUMMARY.yaml")
        summary = yaml.safe_load(summary_path.read_text(encoding="utf-8"))
        self.assertIn("slightly lower on proxy F1", summary["gate_2_summary"]["selection_rationale"])
        memory = [json.loads(line) for line in (self.root / "evidence" / "experiment_memory.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertIn("design_iteration_applied", {entry["event_type"] for entry in memory})


if __name__ == "__main__":
    unittest.main()
