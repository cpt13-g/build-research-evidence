"""Register Cards and enforce approval, priority, dependency, and budget gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from budget_tracker import ensure_available
from common import DEFAULT_ROOT, ProtocolError, atomic_yaml_write, load_state, load_yaml, resolve_project_path, save_state, validate_document


TERMINAL_P0 = {"audited"}


def validate_card_semantics(body: dict[str, Any], kind: str) -> None:
    if kind == "tuning":
        return
    mode = body["experiment_mode"]
    role = body["experiment_role"]
    completion = body["completion_contract"]
    if not completion["stop_when_decided"] or not completion["extension_requires_evidence_gap"]:
        raise ProtocolError("Scientific Cards must stop when decided and require a named evidence gap for extension")
    if mode == "cheap_evaluation":
        if role != "P0_SUPPORT" or body["paper_evidence_eligible"] is not False or body["evidence_label"] != "PRELIMINARY_NON_PAPER":
            raise ProtocolError("Cheap Evaluation must be P0_SUPPORT and PRELIMINARY_NON_PAPER")
        if not body.get("candidate_id") or not isinstance(body.get("cheap_protocol"), dict):
            raise ProtocolError("Cheap Evaluation requires candidate_id and a fair cheap_protocol")
    elif body["evidence_label"] == "PRELIMINARY_NON_PAPER" and body["paper_evidence_eligible"] is True:
        raise ProtocolError("Preliminary evidence cannot be paper-evidence eligible")
    if mode == "refinement_validation" and not body.get("design_iteration_id"):
        raise ProtocolError("Refinement validation requires design_iteration_id")
    role_priority = {
        "CORE_P0": {"P0"},
        "P0_SUPPORT": {"P0", "P0_BLOCKER"},
        "P1_SUPPORT": {"P1"},
        "P2_COMPLETENESS": {"P2"},
        "P3_OPTIONAL": {"P3"},
        "DEBUG": {"P0_BLOCKER"},
    }
    if body["priority"] not in role_priority[role]:
        raise ProtocolError(f"Experiment role {role} disagrees with priority {body['priority']}")


def card_parts(root: Path, card_path_text: str) -> tuple[Path, dict[str, Any], str, str]:
    card_path = resolve_project_path(root, card_path_text)
    card = load_yaml(card_path)
    if "experiment" in card:
        section, kind, schema = "experiment", "scientific", "experiment_card.schema.json"
    elif "tuning" in card:
        section, kind, schema = "tuning", "tuning", "tuning_card.schema.json"
    else:
        raise ProtocolError("Card must contain experiment or tuning")
    validate_document(card, root / "schemas" / schema)
    validate_card_semantics(card[section], kind)
    return card_path, card, section, kind


def register(root: Path, card_path_text: str, expected_revision: int) -> dict[str, Any]:
    card_path, card, section, kind = card_parts(root, card_path_text)
    body = card[section]
    item_id = body["experiment_id"] if kind == "scientific" else body["tuning_id"]
    if item_id.startswith("E") != (kind == "scientific"):
        raise ProtocolError("Card identifier and kind disagree")
    state = load_state(root)
    if any(item["id"] == item_id for item in state["experiment_registry"]):
        raise ProtocolError(f"Duplicate registry id: {item_id}")
    priority = body.get("priority", "P0_BLOCKER")
    experiment_role = body.get("experiment_role", "TUNING")
    experiment_mode = body.get("experiment_mode", "tuning")
    paper_evidence_eligible = bool(body.get("paper_evidence_eligible", False))
    state["experiment_registry"].append({
        "id": item_id,
        "kind": kind,
        "priority": priority,
        "experiment_role": experiment_role,
        "experiment_mode": experiment_mode,
        "paper_evidence_eligible": paper_evidence_eligible,
        "candidate_id": body.get("candidate_id"),
        "design_iteration_id": body.get("design_iteration_id"),
        "status": body["status"],
        "card_path": card_path.relative_to(root).as_posix(),
    })
    if item_id not in state["backlog"]:
        state["backlog"].append(item_id)
    return save_state(root, state, expected_revision=expected_revision, event_type="experiment_registered", event={"id": item_id, "card_path": card_path_text})


def approve(root: Path, item_id: str, actor: str, expected_revision: int) -> dict[str, Any]:
    state = load_state(root)
    if state["revision"] != expected_revision:
        raise ProtocolError(f"Stale state revision: expected {expected_revision}, current {state['revision']}")
    item = next((entry for entry in state["experiment_registry"] if entry["id"] == item_id), None)
    if not item:
        raise ProtocolError(f"Unknown registry id: {item_id}")
    card_path, card, section, _ = card_parts(root, item["card_path"])
    body = card[section]
    body["status"] = "approved"
    body["approval"] = {"approved_by": actor, "approved_at": state["project"]["updated_at"]}
    validate_document(card, root / "schemas" / ("experiment_card.schema.json" if section == "experiment" else "tuning_card.schema.json"))
    atomic_yaml_write(card_path, card)
    item["status"] = "approved"
    return save_state(root, state, expected_revision=expected_revision, event_type="card_approved", event={"id": item_id, "actor": actor})


def activate(root: Path, item_id: str, expected_revision: int) -> dict[str, Any]:
    state = load_state(root)
    if state["status"] == "EVIDENCE_FROZEN":
        raise ProtocolError("Evidence is frozen")
    item = next((entry for entry in state["experiment_registry"] if entry["id"] == item_id), None)
    if not item:
        raise ProtocolError(f"Unknown registry id: {item_id}")
    if state["human_gates"]["gate_1"] != "approved" or state["experiment_contract"]["status"] != "approved":
        raise ProtocolError("Gate 1 and an approved experiment contract are required for every experiment")
    contract_path = resolve_project_path(root, state["experiment_contract"]["path"])
    contract = load_yaml(contract_path)
    validate_document(contract, root / "schemas" / "experiment_contract.schema.json")
    if contract["contract"]["status"] != "approved" or contract["contract"]["version"] != state["experiment_contract"]["version"]:
        raise ProtocolError("State and the approved experiment contract file disagree")
    if item["status"] != "approved":
        raise ProtocolError(f"Card is not approved: {item['status']}")
    _, card, section, _ = card_parts(root, item["card_path"])
    body = card[section]
    dependencies = body.get("dependencies", [])
    incomplete = [dependency for dependency in dependencies if dependency not in state["completed_experiments"]]
    if incomplete:
        raise ProtocolError(f"Incomplete dependencies: {incomplete}")
    if item["experiment_role"] in {"P1_SUPPORT", "P2_COMPLETENESS", "P3_OPTIONAL"}:
        unfinished_p0 = [entry["id"] for entry in state["experiment_registry"] if entry["experiment_role"] == "CORE_P0" and entry["status"] not in TERMINAL_P0]
        if unfinished_p0 or state["human_gates"]["gate_2"] != "approved":
            raise ProtocolError(f"P0 gate blocks {item_id}; unfinished P0: {unfinished_p0}")
    if item["experiment_mode"] == "cheap_evaluation":
        if state["method_search"]["phase"] != "CHEAP_EVALUATE":
            raise ProtocolError("Cheap Evaluation can run only in CHEAP_EVALUATE phase")
        candidate = next((entry for entry in state["candidate_registry"] if entry["id"] == item.get("candidate_id")), None)
        if not candidate or candidate["status"] != "screened_in":
            raise ProtocolError("Cheap Evaluation requires a screened-in active Candidate")
        signature = hashlib.sha256(json.dumps(body["cheap_protocol"], sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        existing_signature = state["method_search"]["cheap_protocol_signature"]
        if existing_signature and existing_signature != signature:
            raise ProtocolError("All Candidates in the active Cheap Evaluation must use the same protocol")
        state["method_search"]["cheap_protocol_signature"] = signature
    if item["candidate_id"] and item["experiment_mode"] == "full_evaluation" and state["method_search"]["phase"] != "FULL_EVALUATE":
        raise ProtocolError("Candidate Full Evaluation requires FULL_EVALUATE phase")
    ensure_available(state, body["estimated_budget"])
    reserved_budget = {
        key: float(value)
        for key, value in body["estimated_budget"].items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    for key, value in reserved_budget.items():
        state["budget"]["reserved"][key] = float(state["budget"]["reserved"].get(key, 0)) + value
    item["reserved_budget"] = reserved_budget
    item["status"] = "queued"
    state["backlog"] = [value for value in state["backlog"] if value != item_id]
    if item_id not in state["active_queue"]:
        state["active_queue"].append(item_id)
    return save_state(root, state, expected_revision=expected_revision, event_type="experiment_activated", event={"id": item_id, "priority": item["priority"]})


def set_status(root: Path, item_id: str, status: str, expected_revision: int, reason: str) -> dict[str, Any]:
    allowed = {"running", "completed", "failed", "audited", "blocked"}
    if status not in allowed:
        raise ProtocolError(f"Unsupported status update: {status}")
    state = load_state(root)
    item = next((entry for entry in state["experiment_registry"] if entry["id"] == item_id), None)
    if not item:
        raise ProtocolError(f"Unknown registry id: {item_id}")
    item["status"] = status
    reserved_budget = item.pop("reserved_budget", {}) if status in {"completed", "failed", "blocked"} else {}
    for key, value in reserved_budget.items():
        current_reserved = float(state["budget"]["reserved"].get(key, 0))
        state["budget"]["reserved"][key] = max(0.0, current_reserved - float(value))
        if status in {"completed", "failed"}:
            state["budget"]["used"][key] = float(state["budget"]["used"].get(key, 0)) + float(value)
    if status in {"completed", "failed", "audited", "blocked"}:
        state["active_queue"] = [value for value in state["active_queue"] if value != item_id]
    if status in {"completed", "audited"} and item_id not in state["completed_experiments"]:
        state["completed_experiments"].append(item_id)
    if status == "failed" and item_id not in state["failed_experiments"]:
        state["failed_experiments"].append(item_id)
    return save_state(root, state, expected_revision=expected_revision, event_type="experiment_status", event={"id": item_id, "status": status, "reason": reason})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--id", help="Read one complete registry entry")
    list_parser.add_argument("--status", help="Filter by registry status")
    list_parser.add_argument("--limit", type=int, default=8)
    list_parser.add_argument("--all", action="store_true", help="Print all matching entries as YAML")
    register_parser = subparsers.add_parser("register")
    register_parser.add_argument("card_path")
    register_parser.add_argument("--expected-revision", type=int, required=True)
    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("id")
    approve_parser.add_argument("--actor", required=True)
    approve_parser.add_argument("--expected-revision", type=int, required=True)
    activate_parser = subparsers.add_parser("activate")
    activate_parser.add_argument("id")
    activate_parser.add_argument("--expected-revision", type=int, required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("id")
    status_parser.add_argument("status")
    status_parser.add_argument("--reason", required=True)
    status_parser.add_argument("--expected-revision", type=int, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "list":
            if args.limit < 1:
                raise ProtocolError("Registry limit must be positive")
            entries = load_state(root)["experiment_registry"]
            if args.id:
                entries = [entry for entry in entries if entry["id"] == args.id]
                if not entries:
                    raise ProtocolError(f"Unknown registry id: {args.id}")
            if args.status:
                entries = [entry for entry in entries if entry["status"] == args.status]
            if args.all:
                print(yaml.safe_dump(entries, sort_keys=False))
            else:
                print(json.dumps({"items": entries[:args.limit], "total": len(entries),
                    "omitted": max(0, len(entries)-args.limit)}, ensure_ascii=False, separators=(",", ":")))
        elif args.command == "register":
            print(register(root, args.card_path, args.expected_revision)["revision"])
        elif args.command == "approve":
            print(approve(root, args.id, args.actor, args.expected_revision)["revision"])
        elif args.command == "activate":
            print(activate(root, args.id, args.expected_revision)["revision"])
        elif args.command == "status":
            print(set_status(root, args.id, args.status, args.expected_revision, args.reason)["revision"])
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
