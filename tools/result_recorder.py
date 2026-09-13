"""Persist a schema-valid audited result without discarding negative outcomes."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import DEFAULT_ROOT, ProtocolError, append_memory, atomic_yaml_write, load_run_manifest, load_state, load_yaml, resolve_project_path, validate_document


def record(root: Path, result_path_text: str) -> Path:
    source = resolve_project_path(root, result_path_text)
    result = load_yaml(source)
    validate_document(result, root / "schemas" / "result_record.schema.json")
    body = result["result"]
    item_id = body["experiment_id"]
    state = load_state(root)
    item = next((entry for entry in state["experiment_registry"] if entry["id"] == item_id), None)
    if not item:
        raise ProtocolError(f"Result references an unregistered item: {item_id}")
    if item["experiment_mode"] == "cheap_evaluation" and body["evidence_classification"] != "PRELIMINARY_NON_PAPER":
        raise ProtocolError("Cheap Evaluation cannot enter formal paper Evidence")
    if body["evidence_classification"] == "FORMAL_CLAIM_EVIDENCE" and not item["paper_evidence_eligible"]:
        raise ProtocolError("This Card is not eligible for formal Claim Evidence")
    diagnosis = body["audit"]["diagnosis"]
    if diagnosis["result_type"] != body["audit"]["result_type"]:
        raise ProtocolError("Audit and Diagnosis result types disagree")
    independence = body["audit"]["independence"]
    if independence["first_pass_mode"] == "BLIND_FIRST_PASS" and independence["planner_interpretation_seen_before_verdict"]:
        raise ProtocolError("Blind-first audit cannot see the planner interpretation before its verdict")
    if independence["first_pass_mode"] == "FULL_CONTEXT_EXCEPTION" and not str(independence.get("exception_reason") or "").strip():
        raise ProtocolError("A full-context audit exception requires a reason")
    if "manifest_integrity" not in independence["deterministic_checks"]:
        raise ProtocolError("Result Audit must record the manifest_integrity deterministic check")
    load_run_manifest(
        root,
        body["execution"]["run_manifest_path"],
        expected_run_id=body["run_id"],
        expected_experiment_id=item_id,
        require_complete=body["evidence_classification"] == "FORMAL_CLAIM_EVIDENCE",
    )
    if diagnosis["failure_level"] == "F1_EXECUTION" and diagnosis["recommended_action"] not in {"DEBUG", "TUNE"}:
        raise ProtocolError("F1 Execution Failure must recommend DEBUG or TUNE")
    if diagnosis["failure_level"] == "F3_HYPOTHESIS_RISK" and diagnosis["recommended_action"] != "ESCALATE_HYPOTHESIS_RISK":
        raise ProtocolError("F3 diagnosis must recommend hypothesis-risk escalation")
    if diagnosis["failure_level"] == "F3_HYPOTHESIS_RISK" and state["status"] != "HYPOTHESIS_AT_RISK":
        raise ProtocolError("A single Result Record cannot declare F3; use the multi-Candidate hypothesis-risk gate")
    destination = root / "experiments" / item_id / "results" / f"{body['record_id']}.yaml"
    if destination.exists():
        raise ProtocolError(f"Result record already exists: {destination.relative_to(root)}")
    atomic_yaml_write(destination, result)
    audit = body["audit"]
    append_memory(
        root,
        "result_audited",
        {
            "experiment_id": item_id,
            "record_id": body["record_id"],
            "result_type": audit["result_type"],
            "failure_level": diagnosis["failure_level"],
            "recommended_action": diagnosis["recommended_action"],
            "evidence_classification": body["evidence_classification"],
            "validity": audit["validity"],
            "confidence": audit["confidence"],
            "result_path": destination.relative_to(root).as_posix(),
        },
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_path")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        print(record(args.root.resolve(), args.result_path))
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
