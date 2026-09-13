"""Assess submission readiness and apply the user-approved Evidence Freeze."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from common import DEFAULT_ROOT, ProtocolError, atomic_yaml_write, load_state, load_yaml, now_iso, resolve_project_path, save_state, validate_document


def assess_readiness(root: Path, expected_revision: int | None = None) -> dict[str, Any]:
    state = load_state(root)
    matrix = load_yaml(resolve_project_path(root, state["evidence"]["claim_evidence_path"]))
    queue = load_yaml(resolve_project_path(root, state["evidence"]["completion_queue_path"]))
    venue = load_yaml(resolve_project_path(root, state["evidence"]["venue_gap_path"]))
    claims = matrix["claims"]
    primary = [claim for claim in claims if claim["importance"] == "primary"]
    primary_has_evidence = bool(primary) and all(bool(claim["supporting_experiments"]) for claim in primary)
    evaluation_valid = bool(primary) and all(claim["assessment"]["validity"] == "VALID" for claim in primary)
    baseline_fair = bool(primary) and all("BASELINE_UNFAIR" not in claim["assessment"]["hard_failures"] for claim in primary)
    reproducible = bool(primary) and all(claim["assessment"]["consistency"] == "CONSISTENT" for claim in primary)
    hard_gates = {
        "primary_claim_has_evidence": primary_has_evidence,
        "evaluation_valid": evaluation_valid,
        "baseline_fair": baseline_fair,
        "results_reproducible": reproducible,
    }
    blocking = [name for name, passed in hard_gates.items() if not passed]
    p1_pending = bool(queue["active_recommendations"])
    primary_unsupported = any(claim["status"] == "UNSUPPORTED" for claim in primary)
    important_missing = any(claim["evidence_strength"] == "INSUFFICIENT" for claim in claims)
    venue_complete = venue.get("search_stopped") is True and not any(gap.get("recommendation") == "P1" and gap.get("current_status") != "COMPLETE" for gap in venue.get("gaps", []))
    presentation_ready = resolve_project_path(root, state["evidence"]["figure_table_plan_path"]).exists()

    if blocking:
        readiness = "NOT_READY"
    elif primary_unsupported:
        readiness = "D"
    elif important_missing:
        readiness = "C"
    elif p1_pending or not venue_complete or not presentation_ready:
        readiness = "B"
    else:
        readiness = "A"
    if readiness == "NOT_READY":
        next_step = f"Resolve hard gates: {', '.join(blocking)}."
    elif readiness == "D":
        next_step = "Escalate the contradicted primary claim for user review; do not silently change the Research Spine."
    elif readiness == "C":
        next_step = "Complete the important Claim-linked evidence gaps."
    elif readiness == "B":
        next_step = "Complete only remaining P1 work and presentation planning; P2 remains ROI-dependent."
    else:
        next_step = "Recommend Gate 3 Evidence Freeze."

    document = {
        "schema_version": "1.0",
        "assessed_at": now_iso(),
        "hard_gates": hard_gates,
        "dimensions": {
            "core_evidence": matrix["evidence_status"],
            "fairness": "PASS" if baseline_fair else "FAIL",
            "reproducibility": "PASS" if reproducible else "FAIL",
            "mechanism_evidence": "COMPLETE" if all(claim["status"] == "SUPPORTED" for claim in claims) else "PARTIAL",
            "venue_completeness": "COMPLETE" if venue_complete else "PARTIAL",
            "presentation_readiness": "READY" if presentation_ready else "MISSING",
        },
        "readiness": readiness,
        "blocking_reasons": blocking,
        "recommended_next_step": next_step,
    }
    validate_document(document, root / "schemas" / "readiness.schema.json")
    destination = resolve_project_path(root, state["evidence"]["readiness_path"])
    atomic_yaml_write(destination, document)
    if expected_revision is not None:
        state["evidence"]["submission_readiness"] = readiness
        if readiness in {"A", "B"} and not p1_pending:
            state["evidence"]["evidence_freeze"]["status"] = "recommended"
        state["evidence"]["next_evidence_action"] = {"type": "READINESS_ACTION", "readiness": readiness, "reason": next_step}
        save_state(root, state, expected_revision=expected_revision, event_type="submission_readiness_assessed", event={"readiness": readiness, "hard_gates": hard_gates, "path": destination.relative_to(root).as_posix()})
    return document


def freeze_evidence(root: Path, expected_revision: int, actor: str, reason: str) -> dict[str, Any]:
    if not actor.strip() or not reason.strip():
        raise ProtocolError("Evidence Freeze requires an explicit actor and reason")
    state = load_state(root)
    if state["human_gates"]["gate_3"] != "approved":
        raise ProtocolError("Evidence Freeze requires explicit user approval at Gate 3")
    if state["current_stage"] not in {"S9_VENUE_EVIDENCE_AUDIT", "S10_EVIDENCE_FREEZE_REPORT"}:
        raise ProtocolError("Evidence Freeze is available only after Venue Evidence Audit")
    readiness_doc = load_yaml(resolve_project_path(root, state["evidence"]["readiness_path"]))
    queue = load_yaml(resolve_project_path(root, state["evidence"]["completion_queue_path"]))
    if readiness_doc["readiness"] not in {"A", "B"}:
        raise ProtocolError("Evidence Freeze requires readiness A or B")
    if queue["active_recommendations"]:
        raise ProtocolError("Complete or explicitly resolve all P1 recommendations before Evidence Freeze")
    state["status"] = "EVIDENCE_FROZEN"
    state["current_stage"] = "S10_EVIDENCE_FREEZE_REPORT"
    state["evidence"]["evidence_status"] = "FROZEN"
    state["evidence"]["evidence_freeze"] = {"status": "approved", "approved_by": actor, "approved_at": now_iso(), "reason": reason}
    state["evidence"]["next_evidence_action"] = {"type": "BUILD_FINAL_EXPERIMENT_REPORT", "reason": "Evidence is frozen; ordinary experiment activation is stopped."}
    return save_state(root, state, expected_revision=expected_revision, event_type="evidence_frozen", event={"actor": actor, "reason": reason})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("assess")
    audit.add_argument("--expected-revision", type=int)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--expected-revision", type=int, required=True)
    freeze.add_argument("--actor", required=True)
    freeze.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        if args.command == "assess":
            print(yaml.safe_dump(assess_readiness(args.root.resolve(), args.expected_revision), allow_unicode=True, sort_keys=False))
        else:
            print(freeze_evidence(args.root.resolve(), args.expected_revision, args.actor, args.reason)["revision"])
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
