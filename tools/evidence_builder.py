"""Build compact Claim-Evidence, Venue Gap, and Evidence Completion artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from common import (
    DEFAULT_ROOT,
    ProtocolError,
    atomic_yaml_write,
    load_state,
    load_run_manifest,
    load_yaml,
    now_iso,
    resolve_project_path,
    save_state,
    validate_document,
)


FORMAL_RESULT_TYPES = {"SUPPORTING", "FALSIFYING", "BOUNDARY", "NULL", "CONFOUNDING", "INCONCLUSIVE"}


def _id(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("id") or value.get("claim_id")
    return None


def _claim_inputs(state: dict[str, Any]) -> list[dict[str, Any]]:
    primary_ids = {_id(item) for item in state["research_spine"].get("primary_claims", [])}
    claims: list[dict[str, Any]] = []
    for item in state.get("claims", []):
        if isinstance(item, str):
            claims.append({"claim_id": item, "statement": item, "importance": "primary" if item in primary_ids else "secondary", "required_evidence": []})
            continue
        if not isinstance(item, dict):
            continue
        claim_id = _id(item)
        if not claim_id:
            continue
        claims.append({
            "claim_id": claim_id,
            "statement": item.get("statement") or item.get("claim") or item.get("description") or "",
            "importance": item.get("importance") or ("primary" if claim_id in primary_ids else "secondary"),
            "required_evidence": item.get("required_evidence", []),
        })
    return claims


def _method_status(state: dict[str, Any]) -> str:
    if state.get("status") == "HYPOTHESIS_AT_RISK":
        return "AT_RISK"
    phase = state.get("method_search", {}).get("phase", "NOT_STARTED")
    if phase == "CONVERGED":
        return "CONVERGED"
    return "NOT_STARTED" if phase == "NOT_STARTED" else "ACTIVE"


def _formal_results(root: Path, state: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[str], list[dict[str, str]]]:
    registry = {item["id"]: item for item in state["experiment_registry"]}
    by_claim: dict[str, list[dict[str, Any]]] = {}
    excluded: set[str] = set()
    invalid: list[dict[str, str]] = []
    for path in sorted((root / "experiments").glob("E*/results/*.yaml")):
        document = load_yaml(path)
        validate_document(document, root / "schemas" / "result_record.schema.json")
        result = document["result"]
        experiment_id = result["experiment_id"]
        item = registry.get(experiment_id)
        if not item:
            continue
        if not item.get("paper_evidence_eligible") or item.get("experiment_mode") == "cheap_evaluation" or result["evidence_classification"] != "FORMAL_CLAIM_EVIDENCE":
            excluded.add(experiment_id)
            continue
        independence = result["audit"]["independence"]
        if independence["first_pass_mode"] != "BLIND_FIRST_PASS" or independence["planner_interpretation_seen_before_verdict"]:
            invalid.append({"experiment_id": experiment_id, "reason": "Formal evidence lacks an isolated blind-first audit."})
            continue
        try:
            load_run_manifest(
                root,
                result["execution"]["run_manifest_path"],
                expected_run_id=result["run_id"],
                expected_experiment_id=experiment_id,
                require_complete=True,
            )
        except ProtocolError as error:
            invalid.append({"experiment_id": experiment_id, "reason": str(error)})
            continue
        card = load_yaml(resolve_project_path(root, item["card_path"]))["experiment"]
        audit = result["audit"]
        diagnosis = audit["diagnosis"]
        result_type = audit["result_type"]
        if result_type not in FORMAL_RESULT_TYPES:
            continue
        seed_protocol = card.get("seed_protocol") or {}
        seeds = seed_protocol.get("seeds", []) if isinstance(seed_protocol, dict) else []
        entry = {
            "experiment_id": experiment_id,
            "card_path": item["card_path"],
            "result_path": path.relative_to(root).as_posix(),
            "result_type": result_type,
            "validity": diagnosis["experiment_validity"],
            "baseline_fairness": diagnosis["baseline_fairness"],
            "unresolved_confounders": diagnosis["unresolved_confounders"],
            "seed_count": len(seeds),
        }
        by_claim.setdefault(card["claim_id"], []).append(entry)
    return by_claim, sorted(excluded), invalid


def _public_ref(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: entry[key] for key in ("experiment_id", "card_path", "result_path", "result_type")}


def _assess_claim(claim: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    supporting = [item for item in results if item["result_type"] == "SUPPORTING"]
    contradicting = [item for item in results if item["result_type"] == "FALSIFYING"]
    boundary = [item for item in results if item["result_type"] in {"BOUNDARY", "NULL"}]
    relevant = supporting + contradicting + boundary + [item for item in results if item["result_type"] in {"CONFOUNDING", "INCONCLUSIVE"}]
    confounds = sorted({str(value) for item in relevant for value in item["unresolved_confounders"]})
    gaps: list[dict[str, Any]] = []
    support_ids = {item["experiment_id"] for item in supporting}
    for requirement in claim["required_evidence"]:
        if not isinstance(requirement, dict) or requirement.get("required", True) is False:
            continue
        expected_ids = set(requirement.get("experiment_ids", []))
        satisfied = bool(support_ids & expected_ids) if expected_ids else bool(supporting)
        if not satisfied:
            gaps.append({
                "evidence_type": requirement.get("evidence_type") or requirement.get("type") or "direct_evidence",
                "reason": requirement.get("description") or "Required evidence is missing.",
                "claim_relevance": "HIGH" if claim["importance"] == "primary" else "MEDIUM",
                "reviewer_risk": requirement.get("reviewer_risk", "HIGH" if claim["importance"] == "primary" else "MEDIUM"),
                "expected_information_gain": requirement.get("expected_information_gain", "HIGH"),
                "estimated_cost": requirement.get("estimated_cost", "MEDIUM"),
            })

    hard_failures: list[str] = []
    if claim["importance"] == "primary" and not supporting:
        hard_failures.append("PRIMARY_EVIDENCE_MISSING")
    if any(item["validity"] == "invalid" for item in relevant):
        hard_failures.append("EVALUATION_INVALID")
    if any(item["baseline_fairness"] == "unfair" for item in relevant):
        hard_failures.append("BASELINE_UNFAIR")
    if gaps:
        hard_failures.append("REQUIRED_EVIDENCE_MISSING")

    directness = "DIRECT" if relevant else "MISSING"
    if any(item["validity"] == "invalid" for item in relevant):
        validity = "INVALID"
    elif relevant and all(item["validity"] == "valid" for item in relevant):
        validity = "VALID"
    else:
        validity = "MIXED"
    if not supporting:
        consistency = "NONE"
    elif contradicting:
        consistency = "MIXED"
    elif len(supporting) >= 2 or any(item["seed_count"] >= 2 for item in supporting):
        consistency = "CONSISTENT"
    else:
        consistency = "SINGLE"
    if confounds or any(item["result_type"] == "CONFOUNDING" for item in relevant):
        confound_control = "UNCONTROLLED"
    elif any(item["baseline_fairness"] == "uncertain" for item in relevant):
        confound_control = "PARTIAL"
    else:
        confound_control = "CONTROLLED" if relevant else "UNCONTROLLED"

    if hard_failures:
        strength = "INSUFFICIENT"
    elif directness == "DIRECT" and validity == "VALID" and consistency == "CONSISTENT" and confound_control == "CONTROLLED" and not contradicting:
        strength = "STRONG"
    elif supporting and validity == "VALID" and confound_control in {"CONTROLLED", "PARTIAL"} and not contradicting:
        strength = "MODERATE"
    elif supporting or boundary or contradicting:
        strength = "WEAK"
    else:
        strength = "INSUFFICIENT"

    if contradicting and not supporting:
        status = "UNSUPPORTED"
    elif strength in {"STRONG", "MODERATE"}:
        status = "SUPPORTED"
    elif supporting or boundary:
        status = "PARTIAL"
    else:
        status = "INCONCLUSIVE"
    next_action = None
    if gaps:
        next_action = {"type": "COMPLETE_EVIDENCE", "evidence_type": gaps[0]["evidence_type"], "reason": gaps[0]["reason"]}
    elif status == "UNSUPPORTED" and claim["importance"] == "primary":
        next_action = {"type": "PRIMARY_CLAIM_RISK_REVIEW", "reason": "Formal evidence contradicts the primary claim."}

    return {
        **claim,
        "supporting_experiments": [_public_ref(item) for item in supporting],
        "contradicting_experiments": [_public_ref(item) for item in contradicting],
        "boundary_experiments": [_public_ref(item) for item in boundary],
        "unresolved_confounds": confounds,
        "assessment": {"directness": directness, "validity": validity, "consistency": consistency, "confound_control": confound_control, "hard_failures": hard_failures},
        "evidence_strength": strength,
        "status": status,
        "remaining_gap": gaps,
        "next_action": next_action,
    }


def build_claim_evidence(root: Path, expected_revision: int | None = None) -> dict[str, Any]:
    state = load_state(root)
    by_claim, excluded, invalid = _formal_results(root, state)
    claims = [_assess_claim(claim, by_claim.get(claim["claim_id"], [])) for claim in _claim_inputs(state)]
    statuses = [claim["status"] for claim in claims]
    primary = [claim for claim in claims if claim["importance"] == "primary"]
    if not claims:
        claim_status, evidence_status = "NOT_ASSESSED", "NOT_ASSESSED"
    elif any(claim["status"] == "UNSUPPORTED" for claim in primary):
        claim_status, evidence_status = "UNSUPPORTED", "AT_RISK"
    elif all(claim["status"] == "SUPPORTED" for claim in claims):
        claim_status, evidence_status = "SUPPORTED", "SUFFICIENT"
    elif any(status in {"SUPPORTED", "PARTIAL"} for status in statuses):
        claim_status, evidence_status = "PARTIAL", "INCOMPLETE"
    else:
        claim_status, evidence_status = "INCONCLUSIVE", "INCOMPLETE"
    document = {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "method_status": _method_status(state),
        "claim_status": claim_status,
        "evidence_status": evidence_status,
        "excluded_preliminary_experiments": excluded,
        "excluded_invalid_evidence": invalid,
        "claims": claims,
    }
    validate_document(document, root / "schemas" / "claim_evidence.schema.json")
    path = resolve_project_path(root, state["evidence"]["claim_evidence_path"])
    atomic_yaml_write(path, document)
    if expected_revision is not None:
        state["evidence"].update({"method_status": document["method_status"], "claim_status": claim_status, "evidence_status": evidence_status})
        state["claim_status"] = {claim["claim_id"]: claim["status"] for claim in claims}
        state["evidence"]["next_evidence_action"] = next((claim["next_action"] for claim in claims if claim["next_action"]), None)
        save_state(root, state, expected_revision=expected_revision, event_type="claim_evidence_built", event={"claim_status": claim_status, "evidence_status": evidence_status, "path": path.relative_to(root).as_posix()})
    return document


def recommend_priority(gap: dict[str, Any]) -> str:
    relevance = gap["claim_relevance"]
    risk = gap["reviewer_risk"]
    gain = gap["expected_information_gain"]
    cost = gap["estimated_cost"]
    if relevance == "LOW":
        return "P3" if risk == "HIGH" and cost == "LOW" else "SKIP"
    if relevance == "HIGH" and (risk == "HIGH" or gain == "HIGH") and cost != "HIGH":
        return "P1"
    if relevance == "HIGH" or (relevance == "MEDIUM" and risk == "HIGH" and cost != "HIGH"):
        return "P2"
    return "P3"


def finalize_venue_gap(root: Path, source_path_text: str, expected_revision: int | None = None) -> dict[str, Any]:
    state = load_state(root)
    document = load_yaml(resolve_project_path(root, source_path_text))
    papers = document.get("reviewed_papers", [])
    target_papers = document.get("target_papers")
    included_relevant = [paper for paper in papers if paper.get("included") is True and paper.get("relevance") in {"HIGH", "MEDIUM"}]
    if not isinstance(target_papers, int) or not 5 <= target_papers <= 10:
        raise ProtocolError("Venue audit target_papers must be between 5 and 10")
    if not 5 <= len(papers) <= 10 or len(included_relevant) < 5:
        raise ProtocolError("Venue audit must stop after 5-10 highly relevant papers")
    if document.get("search_stopped") is not True or not str(document.get("stop_reason", "")).strip():
        raise ProtocolError("Venue audit requires an explicit stop decision and reason")
    for gap in document.get("gaps", []):
        gap["recommendation"] = recommend_priority(gap)
    validate_document(document, root / "schemas" / "venue_gap.schema.json")
    destination = resolve_project_path(root, state["evidence"]["venue_gap_path"])
    atomic_yaml_write(destination, document)
    if expected_revision is not None:
        save_state(root, state, expected_revision=expected_revision, event_type="venue_evidence_audited", event={"venue": document["venue"], "papers": len(papers), "path": destination.relative_to(root).as_posix()})
    return document


def build_completion_queue(root: Path, expected_revision: int | None = None) -> dict[str, Any]:
    state = load_state(root)
    matrix = load_yaml(resolve_project_path(root, state["evidence"]["claim_evidence_path"]))
    venue = load_yaml(resolve_project_path(root, state["evidence"]["venue_gap_path"]))
    items: list[dict[str, Any]] = []
    counter = 1
    for claim in matrix["claims"]:
        for gap in claim["remaining_gap"]:
            priority = recommend_priority(gap)
            items.append({"recommendation_id": f"REC-{counter:03d}", "source": "CLAIM_GAP", "evidence_type": gap["evidence_type"], "claim_ids": [claim["claim_id"]], "claim_relevance": gap["claim_relevance"], "reviewer_risk": gap["reviewer_risk"], "expected_information_gain": gap["expected_information_gain"], "estimated_cost": gap["estimated_cost"], "priority": priority, "recommended_for_execution": priority == "P1", "reason": gap["reason"]})
            counter += 1
    for gap in venue.get("gaps", []):
        if gap["current_status"] == "COMPLETE":
            continue
        priority = recommend_priority(gap)
        items.append({"recommendation_id": f"REC-{counter:03d}", "source": "VENUE_GAP", "evidence_type": gap["evidence_type"], "claim_ids": gap["claim_ids"], "claim_relevance": gap["claim_relevance"], "reviewer_risk": gap["reviewer_risk"], "expected_information_gain": gap["expected_information_gain"], "estimated_cost": gap["estimated_cost"], "priority": priority, "recommended_for_execution": priority == "P1", "reason": gap["reason"]})
        counter += 1
    order = {"P1": 0, "P2": 1, "P3": 2, "SKIP": 3}
    items.sort(key=lambda item: (order[item["priority"]], item["recommendation_id"]))
    primary_contradicted = any(claim["importance"] == "primary" and claim["status"] == "UNSUPPORTED" for claim in matrix["claims"])
    document = {"schema_version": "1.0", "generated_at": now_iso(), "method_search_reopen_recommended": primary_contradicted, "active_recommendations": [item["recommendation_id"] for item in items if item["recommended_for_execution"]], "items": items}
    validate_document(document, root / "schemas" / "evidence_completion_queue.schema.json")
    destination = resolve_project_path(root, state["evidence"]["completion_queue_path"])
    atomic_yaml_write(destination, document)
    if expected_revision is not None:
        state["evidence"]["next_evidence_action"] = next(({"type": "CREATE_APPROVED_EXPERIMENT_CARD", "recommendation_id": item["recommendation_id"], "priority": "P1"} for item in items if item["priority"] == "P1"), None)
        save_state(root, state, expected_revision=expected_revision, event_type="evidence_completion_queue_built", event={"p1": document["active_recommendations"], "path": destination.relative_to(root).as_posix()})
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--expected-revision", type=int)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("claims")
    venue = sub.add_parser("venue")
    venue.add_argument("source_path")
    sub.add_parser("queue")
    args = parser.parse_args()
    try:
        if args.command == "claims":
            result = build_claim_evidence(args.root.resolve(), args.expected_revision)
        elif args.command == "venue":
            result = finalize_venue_gap(args.root.resolve(), args.source_path, args.expected_revision)
        else:
            result = build_completion_queue(args.root.resolve(), args.expected_revision)
        print(yaml.safe_dump(result, allow_unicode=True, sort_keys=False))
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
