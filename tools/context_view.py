"""Read-only, source-linked role views and bounded evidence/history navigation."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

from common import DEFAULT_ROOT, ProtocolError, file_sha256, load_run_manifest, load_state, load_yaml, resolve_project_path
from budget_tracker import budget_view
from experiment_registry import card_parts


POLICIES = [
    "AGENTS.md", "Research Spine.md", "docs/PROTOCOLS.md", "docs/ROLE_HANDOFFS.md",
    "docs/CONTEXT_POLICY.md", "docs/STATE_MACHINE.md",
    "docs/METHOD_REALIZATION_PROTOCOL.md", "docs/EVIDENCE_COMPLETION_PROTOCOL.md",
]
ROLES = ("orchestrator", "runner", "auditor", "venue")


def _source(root: Path, path: str) -> dict[str, Any]:
    target = resolve_project_path(root, path)
    if not target.is_file():
        raise ProtocolError(f"Missing context source: {path}")
    return {"path": target.relative_to(root.resolve()).as_posix(),
            "sha256": file_sha256(target), "size_bytes": target.stat().st_size}


def _window(values: list[Any], limit: int) -> dict[str, Any]:
    return {"items": values[:limit], "total": len(values),
            "omitted": max(0, len(values) - limit)}


def build_view(root: Path, role: str = "orchestrator", *, experiment_id: str | None = None,
               manifest_path: str | None = None, limit: int = 8) -> dict[str, Any]:
    root = root.resolve()
    if role not in ROLES or limit < 1:
        raise ProtocolError("Unknown role or non-positive context limit")
    state_path = "research/research_state.yaml"
    state_source = _source(root, state_path)
    state = load_state(root)
    packet: dict[str, Any] = {
        "view_version": 1, "role": role, "revision": state["revision"],
        "sources": [state_source],
        "policy_sources": [_source(root, path) for path in POLICIES],
        "use": "Read-only projection, not authorization or a scientific verdict. Rebuild after source changes.",
    }
    if role in {"runner", "auditor"}:
        if not experiment_id:
            raise ProtocolError(f"{role} requires --experiment")
        item = next((x for x in state["experiment_registry"] if x["id"] == experiment_id), None)
        if item is None:
            raise ProtocolError(f"Unknown experiment: {experiment_id}")
        contract_path = state["experiment_contract"]["path"]
        packet["sources"].extend([_source(root, item["card_path"]), _source(root, contract_path)])
        _, card, section, _ = card_parts(root, item["card_path"])
        contract = load_yaml(resolve_project_path(root, contract_path))
        # Cards/contracts stay complete: fairness, confounds and stop conditions must not be summarized away.
        packet.update({"card": card, "contract": contract})
        if role == "runner":
            method_artifacts = []
            envelope_id = None
            for field, index in (("candidate_id", "candidate_registry"), ("design_iteration_id", "design_iterations")):
                artifact_id = card[section].get(field)
                if not artifact_id:
                    continue
                ref = next((x for x in state[index] if x["id"] == artifact_id), None)
                if ref is None:
                    raise ProtocolError(f"Missing approved method reference: {artifact_id}")
                packet["sources"].append(_source(root, ref["path"]))
                document = load_yaml(resolve_project_path(root, ref["path"]))
                method_artifacts.append({"path": ref["path"], "document": document})
                for value in document.values():
                    if isinstance(value, dict) and value.get("design_envelope_id"):
                        envelope_id = value["design_envelope_id"]
            if envelope_id:
                ref = next((x for x in state["design_envelopes"] if x["id"] == envelope_id), None)
                if ref is None:
                    raise ProtocolError(f"Missing Design Envelope: {envelope_id}")
                packet["sources"].append(_source(root, ref["path"]))
                method_artifacts.append({"path": ref["path"], "document": load_yaml(resolve_project_path(root, ref["path"]))})
            packet.update({
                "method_artifacts": method_artifacts,
                "execution_state": {"status": state["status"], "human_gates": state["human_gates"],
                    "contract_reference": state["experiment_contract"], "registry_item": item,
                    "in_active_queue": experiment_id in state["active_queue"],
                    "dependency_status": {x: x in state["completed_experiments"] for x in card[section].get("dependencies", [])},
                    "budget": budget_view(state), "method_phase": state["method_search"]["phase"]},
                "execution_rule": "Use Registry/Runner gates; this view cannot approve or activate work.",
            })
        else:
            if not manifest_path:
                raise ProtocolError("auditor requires --run-manifest")
            packet["sources"].append(_source(root, manifest_path))
            manifest = load_run_manifest(root, manifest_path, expected_experiment_id=experiment_id,
                require_complete=bool(card[section].get("paper_evidence_eligible")))
            if manifest["card_path"] != item["card_path"]:
                raise ProtocolError("Audit manifest does not reference the registered Card")
            packet["sources"].append(_source(root, manifest["environment_path"]))
            packet["sources"].extend(_source(root, x["path"]) for x in manifest["artifacts"])
            packet.update({"run_manifest": manifest,
                "deterministic_checks": ["manifest_integrity"],
                "evidence_review_required": True,
                "audit_rule": "No planner verdict, claim status, next action or history is included. Inspect raw metrics, protocol checks and relevant logs/artifacts before the first verdict. Integrity is not scientific validity."})
        if check_fresh(root, packet):
            raise ProtocolError("Context sources changed during view construction; rebuild the view")
        return packet

    packet.update({"status": state["status"], "stage": state["current_stage"],
        "research_spine": state["research_spine"], "claims": state["claims"],
        "evidence_questions": state["evidence_questions"], "venue": state["venue"],
        "human_gates": state["human_gates"], "evidence": state["evidence"],
        "unresolved_risks": state["unresolved_risks"]})
    if role == "venue":
        for key in ("claim_evidence_path", "venue_gap_path", "readiness_path"):
            path = state["evidence"][key]
            packet["sources"].append(_source(root, path))
            packet[key] = path
        packet["authorization_rule"] = "P0 substantially complete and explicit Orchestrator authorization are still required."
    else:
        active = set(state["active_queue"])
        candidate_ids = set(state["method_search"]["active_candidate_ids"]
            + state["method_search"]["selected_candidate_ids"] + state["method_search"]["reserve_candidate_ids"])
        packet.update({"budget": budget_view(state), "next_action": state["next_action"],
            "method_search": state["method_search"], "current_method": state["current_method"],
            "functional_requirements": state["functional_requirements"],
            "design_envelopes": state["design_envelopes"], "claim_status": state["claim_status"],
            "contract_reference": state["experiment_contract"], "active_queue": state["active_queue"],
            "active_items": [x for x in state["experiment_registry"] if x["id"] in active],
            "backlog": _window(state["backlog"], limit),
            "candidate_registry": _window(state["candidate_registry"], limit),
            "active_candidates": [x for x in state["candidate_registry"] if x["id"] in candidate_ids],
            "design_iterations": _window(state["design_iterations"], limit),
            "registry_counts": dict(Counter(x["status"] for x in state["experiment_registry"])),
            "history_index": {"registry": state_path, "memory": state.get("memory_path"),
                "completed_count": len(state["completed_experiments"]), "failed_count": len(state["failed_experiments"])},
            "expansion_rule": "Omitted items are not resolved or irrelevant. Retrieve relevant candidates, dependencies, negative results and gaps before selection, Gate, reopening or Freeze decisions."})
    if check_fresh(root, packet):
        raise ProtocolError("Context sources changed during view construction; rebuild the view")
    return packet


def check_fresh(root: Path, packet: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for source in [*packet["sources"], *packet["policy_sources"]]:
        path = resolve_project_path(root, source["path"])
        if not path.is_file() or file_sha256(path) != source["sha256"]:
            changed.append(source["path"])
    return sorted(set(changed))


def history_view(root: Path, *, experiment_id: str | None = None, event_type: str | None = None,
                 limit: int = 10, before_line: int | None = None) -> dict[str, Any]:
    if limit < 1 or (before_line is not None and before_line < 1):
        raise ProtocolError("History limits and line cursors must be positive")
    state = load_state(root)
    path = resolve_project_path(root, state.get("memory_path", "evidence/experiment_memory.jsonl"))
    matches: deque[dict[str, Any]] = deque(maxlen=limit)
    count = 0
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if before_line is not None and number >= before_line:
                    break
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ProtocolError(f"Invalid memory event at line {number}") from error
                if not isinstance(event, dict):
                    raise ProtocolError(f"Invalid memory event at line {number}")
                if experiment_id and event.get("experiment_id", event.get("id")) != experiment_id:
                    continue
                if event_type and event.get("event_type") != event_type:
                    continue
                matches.append({"line": number, "event": event})
                count += 1
    return {"revision": state["revision"], "path": path.relative_to(root.resolve()).as_posix(),
        "items": list(matches), "matched_before_cursor": count, "omitted": max(0, count-len(matches)),
        "next_before_line": matches[0]["line"] if count > len(matches) else None}


def excerpt(root: Path, path: str, *, start_line: int = 1, lines: int = 60,
            max_chars: int = 8000) -> dict[str, Any]:
    if min(start_line, lines, max_chars) < 1:
        raise ProtocolError("Excerpt bounds must be positive")
    source = _source(root, path)
    selected: list[dict[str, Any]] = []
    used = 0
    total = 0
    partial_line = None
    with resolve_project_path(root, path).open(encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, 1):
            total = number
            if number < start_line or len(selected) >= lines or used >= max_chars:
                continue
            text = line.rstrip("\n\r")
            available = max_chars - used
            selected.append({"line": number, "text": text[:available]})
            used += min(len(text), available)
            if len(text) > available:
                partial_line = number
    last = selected[-1]["line"] if selected else start_line - 1
    return {"source": source, "items": selected, "total_lines": total,
        "partial_line": partial_line, "next_start_line": partial_line or (last+1 if last < total else None),
        "review_notice": "Navigation excerpt only. A partial line requires a larger max_chars; inspect all evidence relevant to the verdict, including failures and outliers."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--pretty", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show")
    show.add_argument("--role", choices=ROLES, default="orchestrator")
    show.add_argument("--experiment")
    show.add_argument("--run-manifest")
    show.add_argument("--limit", type=int, default=8)
    verify = sub.add_parser("verify")
    verify.add_argument("packet", help="A previously saved JSON view, relative to the project")
    history = sub.add_parser("history")
    history.add_argument("--experiment")
    history.add_argument("--event")
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--before-line", type=int)
    log = sub.add_parser("excerpt")
    log.add_argument("path")
    log.add_argument("--start-line", type=int, default=1)
    log.add_argument("--lines", type=int, default=60)
    log.add_argument("--max-chars", type=int, default=8000)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "show":
            output = build_view(root, args.role, experiment_id=args.experiment,
                manifest_path=args.run_manifest, limit=args.limit)
        elif args.command == "verify":
            packet = json.loads(resolve_project_path(root, args.packet).read_text(encoding="utf-8"))
            changed = check_fresh(root, packet)
            output = {"fresh": not changed, "changed_sources": changed}
        elif args.command == "history":
            output = history_view(root, experiment_id=args.experiment, event_type=args.event,
                limit=args.limit, before_line=args.before_line)
        else:
            output = excerpt(root, args.path, start_line=args.start_line, lines=args.lines, max_chars=args.max_chars)
        print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":")))
        return 1 if args.command == "verify" and not output["fresh"] else 0
    except (ProtocolError, OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
