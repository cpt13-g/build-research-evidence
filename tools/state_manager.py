"""Read and atomically update the sole project decision-state file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from common import DEFAULT_ROOT, ProtocolError, load_state, load_yaml, now_iso, resolve_project_path, save_state, set_nested


TRANSITIONS: dict[str, set[str]] = {
    "S0_INTAKE_RECOVERY": {"S1_RESEARCH_VENUE_CONTRACT"},
    "S1_RESEARCH_VENUE_CONTRACT": {"S2_CLAIM_FORMALIZATION"},
    "S2_CLAIM_FORMALIZATION": {"S3_METHOD_REALIZATION"},
    "S3_METHOD_REALIZATION": {"S4_EXPERIMENTAL_PROTOCOL"},
    "S4_EXPERIMENTAL_PROTOCOL": {"S3_METHOD_REALIZATION", "S5_INFRASTRUCTURE_BASELINE"},
    "S5_INFRASTRUCTURE_BASELINE": {"S4_EXPERIMENTAL_PROTOCOL", "S6_P0_MAIN_EXPERIMENTS"},
    "S6_P0_MAIN_EXPERIMENTS": {"S7_CLAIM_AUDIT_REFINEMENT"},
    "S7_CLAIM_AUDIT_REFINEMENT": {
        "S3_METHOD_REALIZATION",
        "S6_P0_MAIN_EXPERIMENTS",
        "S8_SUPPORTING_EXPERIMENTS",
    },
    "S8_SUPPORTING_EXPERIMENTS": {"S6_P0_MAIN_EXPERIMENTS", "S9_VENUE_EVIDENCE_AUDIT"},
    "S9_VENUE_EVIDENCE_AUDIT": {"S8_SUPPORTING_EXPERIMENTS", "S10_EVIDENCE_FREEZE_REPORT"},
    "S10_EVIDENCE_FREEZE_REPORT": {"S8_SUPPORTING_EXPERIMENTS"},
}

GATE_FOR_TRANSITION = {
    ("S4_EXPERIMENTAL_PROTOCOL", "S5_INFRASTRUCTURE_BASELINE"): "gate_1",
    ("S7_CLAIM_AUDIT_REFINEMENT", "S8_SUPPORTING_EXPERIMENTS"): "gate_2",
    ("S9_VENUE_EVIDENCE_AUDIT", "S10_EVIDENCE_FREEZE_REPORT"): "gate_3",
}


def transition(root: Path, target: str, expected_revision: int, reason: str) -> dict[str, Any]:
    state = load_state(root)
    source = state["current_stage"]
    if target not in TRANSITIONS.get(source, set()):
        raise ProtocolError(f"Illegal transition: {source} -> {target}")
    gate = GATE_FOR_TRANSITION.get((source, target))
    if gate and state["human_gates"].get(gate) != "approved":
        raise ProtocolError(f"Transition requires approved {gate}")
    if state["status"] == "EVIDENCE_FROZEN" and target != "S10_EVIDENCE_FREEZE_REPORT":
        raise ProtocolError("Evidence is frozen; user-approved unfreeze is required before transition")
    if target == "S10_EVIDENCE_FREEZE_REPORT":
        readiness = load_yaml(resolve_project_path(root, state["evidence"]["readiness_path"]))
        queue = load_yaml(resolve_project_path(root, state["evidence"]["completion_queue_path"]))
        if readiness.get("readiness") not in {"A", "B"}:
            raise ProtocolError("Evidence Freeze requires submission readiness A or B")
        if queue.get("active_recommendations"):
            raise ProtocolError("Evidence Freeze requires all P1 recommendations to be completed or resolved")
    state["current_stage"] = target
    if target == "S10_EVIDENCE_FREEZE_REPORT":
        state["status"] = "EVIDENCE_FROZEN"
        state["evidence"]["evidence_status"] = "FROZEN"
        state["evidence"]["evidence_freeze"] = {"status": "approved", "approved_by": "gate_3", "approved_at": now_iso(), "reason": reason}
        state["evidence"]["next_evidence_action"] = {"type": "BUILD_FINAL_EXPERIMENT_REPORT", "reason": "Evidence is frozen."}
    return save_state(
        root,
        state,
        expected_revision=expected_revision,
        event_type="state_transition",
        event={"from": source, "to": target, "reason": reason},
    )


def update_gate(root: Path, gate: str, decision: str, expected_revision: int, actor: str) -> dict[str, Any]:
    if gate not in {"gate_1", "gate_2", "gate_3"}:
        raise ProtocolError(f"Unknown gate: {gate}")
    if decision not in {"pending", "approved", "rejected"}:
        raise ProtocolError(f"Invalid gate decision: {decision}")
    state = load_state(root)
    state["human_gates"][gate] = decision
    return save_state(
        root,
        state,
        expected_revision=expected_revision,
        event_type="human_gate_decision",
        event={"gate": gate, "decision": decision, "actor": actor},
    )


def parse_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show")

    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("path")
    set_parser.add_argument("value")
    set_parser.add_argument("--expected-revision", type=int, required=True)
    set_parser.add_argument("--reason", required=True)

    transition_parser = subparsers.add_parser("transition")
    transition_parser.add_argument("target")
    transition_parser.add_argument("--expected-revision", type=int, required=True)
    transition_parser.add_argument("--reason", required=True)

    gate_parser = subparsers.add_parser("gate")
    gate_parser.add_argument("gate")
    gate_parser.add_argument("decision")
    gate_parser.add_argument("--actor", required=True)
    gate_parser.add_argument("--expected-revision", type=int, required=True)

    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "show":
            print(yaml.safe_dump(load_state(root), allow_unicode=True, sort_keys=False))
        elif args.command == "set":
            state = load_state(root)
            set_nested(state, args.path, parse_value(args.value))
            saved = save_state(root, state, expected_revision=args.expected_revision, event_type="state_update", event={"path": args.path, "reason": args.reason})
            print(saved["revision"])
        elif args.command == "transition":
            print(transition(root, args.target, args.expected_revision, args.reason)["revision"])
        elif args.command == "gate":
            print(update_gate(root, args.gate, args.decision, args.expected_revision, args.actor)["revision"])
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
