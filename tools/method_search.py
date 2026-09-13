"""Control constrained Method Realization, candidate search, and evidence-driven refinement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from common import (
    DEFAULT_ROOT,
    ProtocolError,
    atomic_yaml_write,
    load_state,
    load_yaml,
    resolve_project_path,
    save_state,
    validate_document,
)


PHASE_TRANSITIONS = {
    "NOT_STARTED": {"EXPLORE"},
    "EXPLORE": {"SCREEN"},
    "SCREEN": {"CHEAP_EVALUATE"},
    "CHEAP_EVALUATE": {"SELECT"},
    "SELECT": {"FULL_EVALUATE"},
    "FULL_EVALUATE": {"REFINE", "CONVERGED"},
    "REFINE": {"CONVERGED"},
    "CONVERGED": set(),
}

HARD_SCREEN_CHECKS = {
    "research_spine_compatible",
    "contribution_aligned",
    "validation_feasible",
    "fair_comparison_feasible",
    "within_budget",
    "scale_gain_not_primary",
}


class MethodBudgetRequired(ProtocolError):
    """Raised after state records a method-search budget extension recommendation."""


def _artifact_ref(identifier: str, path: Path, root: Path, status: str) -> dict[str, Any]:
    return {"id": identifier, "path": path.relative_to(root).as_posix(), "status": status}


def _find_ref(entries: list[dict[str, Any]], identifier: str) -> dict[str, Any] | None:
    return next((entry for entry in entries if entry["id"] == identifier), None)


def _memory_has_outcome(root: Path, candidate_id: str, result_path: str) -> bool:
    state = load_state(root)
    memory_path = resolve_project_path(root, state.get("memory_path", "evidence/experiment_memory.jsonl"))
    if not memory_path.exists():
        return False
    for line in memory_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") == "candidate_outcome_recorded" and event.get("candidate_id") == candidate_id and event.get("result_path") == result_path:
            return True
    return False


def _load_indexed_artifact(root: Path, entries: list[dict[str, Any]], identifier: str) -> tuple[Path, dict[str, Any]]:
    entry = _find_ref(entries, identifier)
    if not entry:
        raise ProtocolError(f"Unknown indexed artifact: {identifier}")
    path = resolve_project_path(root, entry["path"])
    return path, load_yaml(path)


def _request_extension(
    root: Path,
    state: dict[str, Any],
    expected_revision: int,
    *,
    resource: str,
    needed: int,
    limit: int,
    reason: str,
) -> None:
    budget = state["method_search"]["budget"]
    budget["extension_status"] = "recommended"
    budget["extension_recommendation"] = {
        "resource": resource,
        "current_limit": limit,
        "requested_additional": needed,
        "reason": reason,
        "impact_if_rejected": "The current Method Search action remains blocked; evidence uncertainty is preserved.",
    }
    state["status"] = "BUDGET_EXTENSION_REQUIRED"
    state["next_action"] = {
        "type": "user_budget_decision",
        "resource": resource,
        "reason": reason,
    }
    saved = save_state(
        root,
        state,
        expected_revision=expected_revision,
        event_type="method_search_budget_extension_recommended",
        event=budget["extension_recommendation"],
    )
    raise MethodBudgetRequired(
        f"Method Search budget exhausted for {resource}; recommendation saved at revision {saved['revision']}"
    )


def _ensure_method_capacity(
    root: Path,
    state: dict[str, Any],
    expected_revision: int,
    *,
    used_key: str,
    limit_key: str,
    amount: int,
    reason: str,
) -> None:
    budget = state["method_search"]["budget"]
    used = int(budget["used"].get(used_key, 0))
    limit = int(budget["limits"].get(limit_key, 0))
    if used + amount > limit:
        _request_extension(
            root,
            state,
            expected_revision,
            resource=limit_key,
            needed=used + amount - limit,
            limit=limit,
            reason=reason,
        )


def register_functional_requirement(root: Path, path_text: str, expected_revision: int) -> dict[str, Any]:
    path = resolve_project_path(root, path_text)
    document = load_yaml(path)
    validate_document(document, root / "schemas" / "functional_requirement.schema.json")
    body = document["functional_requirement"]
    state = load_state(root)
    contribution_ids = {item.get("id") for item in state["research_spine"]["contributions"] if isinstance(item, dict)}
    if body["contribution_id"] not in contribution_ids:
        raise ProtocolError(f"Functional Requirement references unknown Contribution: {body['contribution_id']}")
    known_questions = {item.get("id") for item in state["evidence_questions"] if isinstance(item, dict)}
    missing_questions = [item for item in body["evidence_question_ids"] if item not in known_questions]
    if missing_questions:
        raise ProtocolError(f"Unknown Evidence Questions: {missing_questions}")
    if _find_ref(state["functional_requirements"], body["requirement_id"]):
        raise ProtocolError(f"Duplicate Functional Requirement: {body['requirement_id']}")
    state["functional_requirements"].append(_artifact_ref(body["requirement_id"], path, root, body["status"]))
    return save_state(root, state, expected_revision=expected_revision, event_type="functional_requirement_registered", event={"id": body["requirement_id"], "contribution_id": body["contribution_id"], "path": path_text})


def register_design_envelope(root: Path, path_text: str, expected_revision: int) -> dict[str, Any]:
    path = resolve_project_path(root, path_text)
    document = load_yaml(path)
    validate_document(document, root / "schemas" / "design_envelope.schema.json")
    body = document["design_envelope"]
    state = load_state(root)
    for requirement_id in body["functional_requirement_ids"]:
        if not _find_ref(state["functional_requirements"], requirement_id):
            raise ProtocolError(f"Design Envelope references unknown Functional Requirement: {requirement_id}")
    if _find_ref(state["design_envelopes"], body["envelope_id"]):
        raise ProtocolError(f"Duplicate Design Envelope: {body['envelope_id']}")
    state["design_envelopes"].append(_artifact_ref(body["envelope_id"], path, root, body["status"]))
    return save_state(root, state, expected_revision=expected_revision, event_type="design_envelope_registered", event={"id": body["envelope_id"], "contribution_id": body["contribution_id"], "path": path_text})


def start_search(root: Path, contribution_id: str, envelope_id: str, expected_revision: int) -> dict[str, Any]:
    state = load_state(root)
    search = state["method_search"]
    if search["phase"] != "NOT_STARTED":
        raise ProtocolError(f"Method Search already started at phase {search['phase']}")
    envelope_ref = _find_ref(state["design_envelopes"], envelope_id)
    if not envelope_ref:
        raise ProtocolError(f"Unknown Design Envelope: {envelope_id}")
    _, envelope = _load_indexed_artifact(root, state["design_envelopes"], envelope_id)
    if envelope["design_envelope"]["contribution_id"] != contribution_id:
        raise ProtocolError("Contribution and Design Envelope disagree")
    search["phase"] = "EXPLORE"
    search["contribution_id"] = contribution_id
    search["active_envelope_id"] = envelope_id
    state["next_action"] = {"type": "generate_candidates", "phase": "EXPLORE", "contribution_id": contribution_id, "design_envelope_id": envelope_id}
    return save_state(root, state, expected_revision=expected_revision, event_type="method_search_started", event={"contribution_id": contribution_id, "design_envelope_id": envelope_id})


def add_candidate(root: Path, path_text: str, expected_revision: int) -> dict[str, Any]:
    path = resolve_project_path(root, path_text)
    document = load_yaml(path)
    validate_document(document, root / "schemas" / "candidate_mechanism.schema.json")
    body = document["candidate"]
    state = load_state(root)
    search = state["method_search"]
    if search["phase"] != "EXPLORE":
        raise ProtocolError(f"New candidates are allowed only in EXPLORE, not {search['phase']}")
    if body["design_envelope_id"] != search["active_envelope_id"] or body["contribution_id"] != search["contribution_id"]:
        raise ProtocolError("Candidate is outside the active Contribution or Design Envelope")
    if _find_ref(state["candidate_registry"], body["candidate_id"]):
        raise ProtocolError(f"Duplicate Candidate: {body['candidate_id']}")
    if len(search["active_candidate_ids"]) >= 5:
        raise ProtocolError("Active EXPLORE search cannot exceed 5 Candidates")
    _, envelope_doc = _load_indexed_artifact(root, state["design_envelopes"], body["design_envelope_id"])
    allowed = set(envelope_doc["design_envelope"]["allowed_design_dimensions"])
    outside = sorted(set(body["design_dimensions"]) - allowed)
    if outside:
        raise ProtocolError(f"Candidate uses dimensions outside the Design Envelope: {outside}")
    _ensure_method_capacity(root, state, expected_revision, used_key="initial_candidates", limit_key="max_initial_candidates", amount=1, reason=f"Add Candidate {body['candidate_id']} to active search")
    state["candidate_registry"].append({**_artifact_ref(body["candidate_id"], path, root, body["status"]), "contribution_id": body["contribution_id"], "design_envelope_id": body["design_envelope_id"]})
    search["active_candidate_ids"].append(body["candidate_id"])
    search["budget"]["used"]["initial_candidates"] += 1
    return save_state(root, state, expected_revision=expected_revision, event_type="candidate_added", event={"candidate_id": body["candidate_id"], "design_envelope_id": body["design_envelope_id"], "path": path_text})


def record_screening(root: Path, path_text: str, expected_revision: int) -> dict[str, Any]:
    path = resolve_project_path(root, path_text)
    document = load_yaml(path)
    validate_document(document, root / "schemas" / "candidate_screening.schema.json")
    body = document["screening"]
    state = load_state(root)
    if state["method_search"]["phase"] != "SCREEN":
        raise ProtocolError("Conceptual Screening records require SCREEN phase")
    candidate_ref = _find_ref(state["candidate_registry"], body["candidate_id"])
    if not candidate_ref or body["candidate_id"] not in state["method_search"]["active_candidate_ids"]:
        raise ProtocolError(f"Screening references an inactive Candidate: {body['candidate_id']}")
    checks = body["hard_checks"]
    if set(checks) != HARD_SCREEN_CHECKS:
        raise ProtocolError(f"Hard checks must be exactly: {sorted(HARD_SCREEN_CHECKS)}")
    if any(value is not True for value in checks.values()) and body["decision"] != "REJECT":
        raise ProtocolError("A failed hard check requires REJECT; scores cannot override it")
    if body["decision"] == "PASS" and not body["recommended_for_cheap_evaluation"]:
        raise ProtocolError("PASS must explicitly recommend Cheap Evaluation")
    for dimension, score in body["scores"].items():
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 5:
            raise ProtocolError(f"Screening score {dimension} must be numeric in [0, 5]")
    passed = [entry for entry in state["candidate_registry"] if entry["status"] == "screened_in"]
    max_cheap = state["method_search"]["budget"]["limits"]["max_cheap_candidates"]
    if body["decision"] == "PASS" and len(passed) >= max_cheap:
        raise ProtocolError(f"Conceptual Screening cannot pass more than {max_cheap} Candidates")
    candidate_ref["status"] = "screened_in" if body["decision"] == "PASS" else "screened_out" if body["decision"] == "REJECT" else "proposed"
    if body["decision"] == "REJECT" and body["candidate_id"] not in state["method_search"]["rejected_candidate_ids"]:
        state["method_search"]["rejected_candidate_ids"].append(body["candidate_id"])
    return save_state(root, state, expected_revision=expected_revision, event_type="candidate_screened", event={"candidate_id": body["candidate_id"], "decision": body["decision"], "screening_path": path_text})


def advance_phase(root: Path, target: str, expected_revision: int, reason: str) -> dict[str, Any]:
    state = load_state(root)
    search = state["method_search"]
    source = search["phase"]
    if target not in PHASE_TRANSITIONS.get(source, set()):
        raise ProtocolError(f"Illegal Method Search transition: {source} -> {target}")
    if source == "SELECT":
        raise ProtocolError("SELECT -> FULL_EVALUATE requires a schema-valid Candidate Decision")
    active_refs = [entry for entry in state["candidate_registry"] if entry["id"] in search["active_candidate_ids"]]
    if source == "EXPLORE":
        count = len(active_refs)
        if count < 2:
            raise ProtocolError("EXPLORE requires at least 2 Candidates before SCREEN")
    elif source == "SCREEN":
        passed = [entry for entry in active_refs if entry["status"] == "screened_in"]
        if not passed:
            raise ProtocolError("At least one Candidate must pass Conceptual Screening")
        if len(passed) > search["budget"]["limits"]["max_cheap_candidates"]:
            raise ProtocolError("Too many Candidates passed into Cheap Evaluation")
        search["active_candidate_ids"] = [entry["id"] for entry in passed]
        search["cheap_protocol_signature"] = None
    elif source == "CHEAP_EVALUATE":
        evaluated = [entry for entry in active_refs if entry["status"] == "cheap_evaluated"]
        if not evaluated:
            raise ProtocolError("At least one audited Cheap Evaluation is required before SELECT")
    elif source == "FULL_EVALUATE" and target == "REFINE":
        if not search["last_diagnosis_id"]:
            raise ProtocolError("FULL_EVALUATE -> REFINE requires a recorded Diagnosis")
    elif source == "FULL_EVALUATE" and target == "CONVERGED":
        if not search["selected_candidate_ids"] or not set(search["selected_candidate_ids"]).issubset(set(search["full_evaluated_candidate_ids"])):
            raise ProtocolError("FULL_EVALUATE -> CONVERGED requires audited Full Evaluation of the selected Candidate")
    elif source == "REFINE" and target == "CONVERGED":
        iteration_id = (state["current_method"] or {}).get("source_iteration_id")
        validations = [entry for entry in state["experiment_registry"] if entry.get("design_iteration_id") == iteration_id and entry["experiment_mode"] == "refinement_validation" and entry["status"] == "audited"]
        if not iteration_id or not validations:
            raise ProtocolError("REFINE -> CONVERGED requires an audited refinement-validation experiment for the current Method")
    search["phase"] = target
    if target == "CONVERGED" and state["current_method"]:
        state["current_method"]["status"] = "converged"
    state["next_action"] = {"type": "method_search_phase", "phase": target, "reason": reason}
    return save_state(root, state, expected_revision=expected_revision, event_type="method_search_phase", event={"from": source, "to": target, "reason": reason})


def apply_candidate_decision(root: Path, path_text: str, expected_revision: int) -> dict[str, Any]:
    path = resolve_project_path(root, path_text)
    document = load_yaml(path)
    validate_document(document, root / "schemas" / "candidate_decision.schema.json")
    body = document["candidate_decision"]
    state = load_state(root)
    search = state["method_search"]
    if search["phase"] != "SELECT":
        raise ProtocolError("Candidate Decision requires SELECT phase")
    if len(body["selected"]) != 1 or len(body["reserve"]) > 1:
        raise ProtocolError("SELECT chooses exactly one primary route and at most one reserve")
    evaluated = {entry["id"] for entry in state["candidate_registry"] if entry["status"] == "cheap_evaluated"}
    if not set(body["selected"] + body["reserve"]).issubset(evaluated):
        raise ProtocolError("Selected and reserve Candidates must have audited Cheap Evaluation")
    for candidate_id in body["selected"]:
        _find_ref(state["candidate_registry"], candidate_id)["status"] = "selected"  # type: ignore[index]
    for candidate_id in body["reserve"]:
        _find_ref(state["candidate_registry"], candidate_id)["status"] = "reserve"  # type: ignore[index]
    rejected_ids = [entry["candidate_id"] if isinstance(entry, dict) else entry for entry in body["rejected"]]
    for candidate_id in rejected_ids:
        candidate_ref = _find_ref(state["candidate_registry"], candidate_id)
        if candidate_ref:
            candidate_ref["status"] = "rejected"
        if candidate_id not in search["rejected_candidate_ids"]:
            search["rejected_candidate_ids"].append(candidate_id)
    search["selected_candidate_ids"] = body["selected"]
    search["reserve_candidate_ids"] = body["reserve"]
    search["candidate_decision_path"] = path.relative_to(root).as_posix()
    selected_ref = _find_ref(state["candidate_registry"], body["selected"][0])
    method_id = "M1"
    state["current_method"] = {"id": method_id, "source_candidate_id": body["selected"][0], "artifact_path": selected_ref["path"], "status": "selected_for_full_evaluation"}  # type: ignore[index]
    _append_lineage_node(root, method_id, "candidate_selection", body["selected"][0], path.relative_to(root).as_posix())
    search["phase"] = "FULL_EVALUATE"
    state["next_action"] = {"type": "create_full_experiment", "candidate_id": body["selected"][0], "decision_path": path.relative_to(root).as_posix()}
    return save_state(root, state, expected_revision=expected_revision, event_type="candidate_decision_applied", event={"decision_id": body["decision_id"], "selected": body["selected"], "reserve": body["reserve"], "rejected": body["rejected"], "rationale": body["rationale"], "path": path_text})


def _append_lineage_node(root: Path, method_id: str, source_type: str, source_id: str, source_path: str, parent_method_id: str | None = None) -> None:
    state = load_state(root)
    lineage_path = resolve_project_path(root, state["method_search"]["method_lineage_path"])
    lineage = load_yaml(lineage_path)
    validate_document(lineage, root / "schemas" / "method_lineage.schema.json")
    body = lineage["lineage"]
    if any(node.get("method_id") == method_id for node in body["nodes"]):
        raise ProtocolError(f"Duplicate Method lineage node: {method_id}")
    body["nodes"].append({"method_id": method_id, "source_type": source_type, "source_id": source_id, "source_path": source_path})
    if body["root_method_id"] is None:
        body["root_method_id"] = method_id
    if parent_method_id:
        body["edges"].append({"from": parent_method_id, "to": method_id, "relation": "targeted_refinement", "source_id": source_id})
    body["current_method_id"] = method_id
    atomic_yaml_write(lineage_path, lineage)


def record_candidate_outcome(root: Path, candidate_id: str, result_path_text: str, expected_revision: int) -> dict[str, Any]:
    result_path = resolve_project_path(root, result_path_text)
    result = load_yaml(result_path)
    validate_document(result, root / "schemas" / "result_record.schema.json")
    state = load_state(root)
    candidate_ref = _find_ref(state["candidate_registry"], candidate_id)
    if not candidate_ref:
        raise ProtocolError(f"Unknown Candidate: {candidate_id}")
    result_body = result["result"]
    experiment = next((entry for entry in state["experiment_registry"] if entry["id"] == result_body["experiment_id"]), None)
    if not experiment or experiment.get("candidate_id") != candidate_id:
        raise ProtocolError("Result experiment is not linked to the Candidate")
    if experiment["status"] != "audited":
        raise ProtocolError("Candidate outcome requires an audited Experiment")
    if _memory_has_outcome(root, candidate_id, result_path_text):
        raise ProtocolError("Candidate outcome has already been recorded")
    diagnosis = result_body["audit"]["diagnosis"]
    search = state["method_search"]
    if experiment["experiment_mode"] == "cheap_evaluation":
        if result_body["evidence_classification"] != "PRELIMINARY_NON_PAPER":
            raise ProtocolError("Cheap Evaluation must remain PRELIMINARY_NON_PAPER")
        if candidate_ref["status"] != "screened_in":
            raise ProtocolError("Only screened-in Candidates can record Cheap Evaluation")
        first_cheap_evaluation = candidate_ref["status"] != "cheap_evaluated"
        if first_cheap_evaluation:
            _ensure_method_capacity(root, state, expected_revision, used_key="cheap_candidates", limit_key="max_cheap_candidates", amount=1, reason=f"Record Cheap Evaluation for {candidate_id}")
            search["budget"]["used"]["cheap_candidates"] += 1
        candidate_ref["status"] = "cheap_evaluated"
    elif experiment["experiment_mode"] == "full_evaluation":
        first_full_evaluation = candidate_id not in search["full_evaluated_candidate_ids"]
        if first_full_evaluation:
            _ensure_method_capacity(root, state, expected_revision, used_key="full_candidates", limit_key="max_full_candidates", amount=1, reason=f"Record Full Evaluation for {candidate_id}")
            search["budget"]["used"]["full_candidates"] += 1
        candidate_ref["status"] = "full_evaluated"
        if first_full_evaluation:
            search["full_evaluated_candidate_ids"].append(candidate_id)
        if first_full_evaluation and diagnosis["experiment_validity"] == "valid" and diagnosis["baseline_fairness"] in {"fair", "not_applicable"}:
            search["reasonable_candidates_tested"] += 1
            if diagnosis["result_type"] in {"FALSIFYING", "NULL"}:
                search["consistent_negative_results"] += 1
    else:
        raise ProtocolError("Candidate outcomes must come from cheap or full evaluation")
    if diagnosis["failure_level"] == "F2_METHOD" and not candidate_ref.get("failure_recorded"):
        _ensure_method_capacity(root, state, expected_revision, used_key="candidate_failures", limit_key="max_candidate_failures", amount=1, reason=f"Record Method Realization failure for {candidate_id}")
        search["candidate_failures"] += 1
        search["budget"]["used"]["candidate_failures"] += 1
        candidate_ref["failure_recorded"] = True
    candidate_ref["latest_outcome_path"] = result_path_text
    candidate_ref["outcome_count"] = int(candidate_ref.get("outcome_count", 0)) + 1
    search["last_diagnosis_id"] = diagnosis["diagnosis_id"]
    return save_state(root, state, expected_revision=expected_revision, event_type="candidate_outcome_recorded", event={"candidate_id": candidate_id, "experiment_id": result_body["experiment_id"], "result_type": diagnosis["result_type"], "failure_level": diagnosis["failure_level"], "result_path": result_path_text})


def register_design_iteration(root: Path, path_text: str, expected_revision: int) -> dict[str, Any]:
    path = resolve_project_path(root, path_text)
    document = load_yaml(path)
    validate_document(document, root / "schemas" / "design_iteration.schema.json")
    body = document["design_iteration"]
    state = load_state(root)
    search = state["method_search"]
    if search["phase"] != "REFINE":
        raise ProtocolError(f"Design Iteration requires REFINE phase, not {search['phase']}")
    if not body["diagnosis"].strip() or not body["diagnosis_id"].strip():
        raise ProtocolError("NO DIAGNOSIS -> NO METHOD CHANGE")
    if body["parent_method_id"] != (state["current_method"] or {}).get("id"):
        raise ProtocolError("Design Iteration parent does not match current Method")
    _, envelope_doc = _load_indexed_artifact(root, state["design_envelopes"], body["design_envelope_id"])
    allowed_dimensions = set(envelope_doc["design_envelope"]["allowed_design_dimensions"])
    affected_dimensions = set(body["affected_design_dimensions"])
    if not affected_dimensions.issubset(allowed_dimensions):
        raise ProtocolError(f"Refinement changes dimensions outside the Design Envelope: {sorted(affected_dimensions - allowed_dimensions)}")
    evidence_docs = [load_yaml(resolve_project_path(root, evidence_path)) for evidence_path in body["evidence"]]
    diagnoses = [item["result"]["audit"]["diagnosis"] for item in evidence_docs if "result" in item]
    linked = next((item for item in diagnoses if item["diagnosis_id"] == body["diagnosis_id"]), None)
    if not linked:
        raise ProtocolError("Design Iteration must link its Diagnosis to an audited Result Record")
    if linked["recommended_action"] != "REFINE_METHOD" or linked["failure_level"] != "F2_METHOD":
        raise ProtocolError("Targeted Refinement requires an F2 diagnosis recommending REFINE_METHOD")
    diagnosed_dimensions: set[str] = set()
    for cause in linked["suspected_causes"]:
        if isinstance(cause, dict):
            diagnosed_dimensions.update(cause.get("design_dimensions", []))
    if not affected_dimensions.issubset(diagnosed_dimensions):
        raise ProtocolError("Targeted change includes dimensions not implicated by the Diagnosis")
    approved_dimensions = set(body["approved_scope"]["allowed_dimensions"])
    if not affected_dimensions.issubset(approved_dimensions):
        raise ProtocolError("Targeted change exceeds its approved scope")
    _ensure_method_capacity(root, state, expected_revision, used_key="design_iterations", limit_key="max_design_iterations", amount=1, reason=f"Register Design Iteration {body['iteration_id']}")
    if _find_ref(state["design_iterations"], body["iteration_id"]):
        raise ProtocolError(f"Duplicate Design Iteration: {body['iteration_id']}")
    state["design_iterations"].append(_artifact_ref(body["iteration_id"], path, root, body["status"]))
    search["budget"]["used"]["design_iterations"] += 1
    return save_state(root, state, expected_revision=expected_revision, event_type="design_iteration_registered", event={"iteration_id": body["iteration_id"], "parent_method_id": body["parent_method_id"], "diagnosis_id": body["diagnosis_id"], "affected_design_dimensions": body["affected_design_dimensions"], "path": path_text})


def apply_design_iteration(root: Path, iteration_id: str, expected_revision: int) -> dict[str, Any]:
    state = load_state(root)
    path, document = _load_indexed_artifact(root, state["design_iterations"], iteration_id)
    body = document["design_iteration"]
    if body["status"] != "approved" or not body["approved_scope"].get("approved_by") or not body["approved_scope"].get("approved_at"):
        raise ProtocolError("Design Iteration must be approved before changing the Method")
    parent_id = (state["current_method"] or {}).get("id")
    if body["parent_method_id"] != parent_id:
        raise ProtocolError("Design Iteration parent is stale")
    next_number = len(state["design_iterations"]) + 1
    method_id = f"M{next_number}"
    state["current_method"] = {"id": method_id, "parent_method_id": parent_id, "source_iteration_id": iteration_id, "artifact_path": path.relative_to(root).as_posix(), "status": "refinement_pending_validation"}
    _append_lineage_node(root, method_id, "design_iteration", iteration_id, path.relative_to(root).as_posix(), parent_method_id=parent_id)
    return save_state(root, state, expected_revision=expected_revision, event_type="design_iteration_applied", event={"iteration_id": iteration_id, "from_method": parent_id, "to_method": method_id})


def reopen_search(root: Path, reason: str, evidence_paths: list[str], expected_revision: int) -> dict[str, Any]:
    if not reason.strip() or not evidence_paths:
        raise ProtocolError("Reopening EXPLORE requires a specific reason and evidence")
    state = load_state(root)
    search = state["method_search"]
    if search["phase"] not in {"FULL_EVALUATE", "REFINE", "CONVERGED"}:
        raise ProtocolError(f"Cannot reopen search from {search['phase']}")
    _ensure_method_capacity(root, state, expected_revision, used_key="reopen_search", limit_key="max_reopen_search", amount=1, reason=reason)
    for path_text in evidence_paths:
        if not resolve_project_path(root, path_text).exists():
            raise ProtocolError(f"Missing reopening evidence: {path_text}")
    search["phase"] = "EXPLORE"
    search["reopen_count"] += 1
    search["reopen_reason"] = reason
    search["budget"]["used"]["reopen_search"] += 1
    search["active_candidate_ids"] = []
    search["selected_candidate_ids"] = []
    search["reserve_candidate_ids"] = []
    search["cheap_protocol_signature"] = None
    state["next_action"] = {"type": "reopened_candidate_generation", "reason": reason, "evidence": evidence_paths}
    return save_state(root, state, expected_revision=expected_revision, event_type="method_search_reopened", event={"reason": reason, "evidence": evidence_paths})


def assess_hypothesis_risk(root: Path, assessment: dict[str, Any], expected_revision: int) -> dict[str, Any]:
    required_true = ["implementation_validated", "baseline_validated", "evaluation_valid", "results_consistently_negative", "major_confounds_resolved"]
    missing = [key for key in required_true if assessment.get(key) is not True]
    threshold = max(2, int(assessment.get("reasonable_candidate_threshold", 2)))
    state = load_state(root)
    search = state["method_search"]
    if missing or search["reasonable_candidates_tested"] < threshold or search["consistent_negative_results"] < threshold:
        raise ProtocolError(
            "Hypothesis risk gate not met: "
            f"false_conditions={missing}, reasonable_candidates={search['reasonable_candidates_tested']}/{threshold}, "
            f"negative_results={search['consistent_negative_results']}/{threshold}"
        )
    state["status"] = "HYPOTHESIS_AT_RISK"
    state["next_action"] = {"type": "human_hypothesis_review", "assessment": assessment, "method_search_phase": search["phase"]}
    return save_state(root, state, expected_revision=expected_revision, event_type="hypothesis_at_risk", event={"assessment": assessment, "reasonable_candidates_tested": search["reasonable_candidates_tested"], "consistent_negative_results": search["consistent_negative_results"]})


def build_gate2_summary(root: Path, output_path_text: str) -> Path:
    state = load_state(root)
    output_path = resolve_project_path(root, output_path_text)
    search = state["method_search"]
    decision = None
    if search.get("candidate_decision_path"):
        decision = load_yaml(resolve_project_path(root, search["candidate_decision_path"]))["candidate_decision"]
    summary = {
        "schema_version": "1.1",
        "gate_2_summary": {
            "current_method": state["current_method"] or {},
            "method_evolution_summary": f"{len(state['design_iterations'])} Design Iterations; lineage at {search['method_lineage_path']}",
            "primary_claim_evidence": state["claim_status"],
            "candidate_search_summary": {
                "phase": search["phase"],
                "active": search["active_candidate_ids"],
                "selected": search["selected_candidate_ids"],
                "reserve": search["reserve_candidate_ids"],
                "rejected": search["rejected_candidate_ids"],
                "reasonable_candidates_tested": search["reasonable_candidates_tested"],
                "decision_path": search.get("candidate_decision_path"),
            },
            "selection_rationale": decision["rationale"] if decision else "Candidate selection has not been finalized.",
            "remaining_uncertainty": state["unresolved_risks"],
            "current_budget": {"experiment": state["budget"], "method_search": search["budget"]},
            "potential_refinement_roi": "Requires Orchestrator assessment from current Diagnosis and remaining Claim uncertainty.",
            "allowed_decisions": ["CONTINUE_REFINEMENT", "ACCEPT_CURRENT_METHOD", "ENTER_SUPPORTING_EXPERIMENTS", "HYPOTHESIS_AT_RISK"],
        },
    }
    validate_document(summary, root / "schemas" / "gate2_summary.schema.json")
    atomic_yaml_write(output_path, summary)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("register-requirement", "register-envelope", "add-candidate", "screen", "decide", "iteration"):
        sub = subparsers.add_parser(name)
        sub.add_argument("path")
        sub.add_argument("--expected-revision", type=int, required=True)
    start = subparsers.add_parser("start")
    start.add_argument("contribution_id")
    start.add_argument("envelope_id")
    start.add_argument("--expected-revision", type=int, required=True)
    phase = subparsers.add_parser("phase")
    phase.add_argument("target")
    phase.add_argument("--reason", required=True)
    phase.add_argument("--expected-revision", type=int, required=True)
    gate2 = subparsers.add_parser("gate2-summary")
    gate2.add_argument("output_path")
    outcome = subparsers.add_parser("outcome")
    outcome.add_argument("candidate_id")
    outcome.add_argument("result_path")
    outcome.add_argument("--expected-revision", type=int, required=True)
    apply_iteration = subparsers.add_parser("apply-iteration")
    apply_iteration.add_argument("iteration_id")
    apply_iteration.add_argument("--expected-revision", type=int, required=True)
    reopen = subparsers.add_parser("reopen")
    reopen.add_argument("--reason", required=True)
    reopen.add_argument("--evidence", action="append", required=True)
    reopen.add_argument("--expected-revision", type=int, required=True)
    risk = subparsers.add_parser("assess-risk")
    risk.add_argument("assessment", help="YAML/JSON mapping of hypothesis-risk preconditions")
    risk.add_argument("--expected-revision", type=int, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "register-requirement":
            result = register_functional_requirement(root, args.path, args.expected_revision)
        elif args.command == "register-envelope":
            result = register_design_envelope(root, args.path, args.expected_revision)
        elif args.command == "add-candidate":
            result = add_candidate(root, args.path, args.expected_revision)
        elif args.command == "screen":
            result = record_screening(root, args.path, args.expected_revision)
        elif args.command == "decide":
            result = apply_candidate_decision(root, args.path, args.expected_revision)
        elif args.command == "iteration":
            result = register_design_iteration(root, args.path, args.expected_revision)
        elif args.command == "start":
            result = start_search(root, args.contribution_id, args.envelope_id, args.expected_revision)
        elif args.command == "phase":
            result = advance_phase(root, args.target, args.expected_revision, args.reason)
        elif args.command == "gate2-summary":
            print(build_gate2_summary(root, args.output_path))
            return 0
        elif args.command == "outcome":
            result = record_candidate_outcome(root, args.candidate_id, args.result_path, args.expected_revision)
        elif args.command == "apply-iteration":
            result = apply_design_iteration(root, args.iteration_id, args.expected_revision)
        elif args.command == "reopen":
            result = reopen_search(root, args.reason, args.evidence, args.expected_revision)
        elif args.command == "assess-risk":
            assessment = yaml.safe_load(args.assessment)
            if not isinstance(assessment, dict):
                raise ProtocolError("Assessment must be a mapping")
            result = assess_hypothesis_risk(root, assessment, args.expected_revision)
        print(result["revision"])
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
