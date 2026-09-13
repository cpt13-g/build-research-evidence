"""Build a compact Figure/Table Plan and final Experiment Report from evidence references."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DEFAULT_ROOT, ProtocolError, load_state, load_yaml, resolve_project_path


def _refs(claim: dict[str, Any]) -> list[str]:
    values = claim["supporting_experiments"] + claim["contradicting_experiments"] + claim["boundary_experiments"]
    return list(dict.fromkeys(item["experiment_id"] for item in values))


def build_figure_table_plan(root: Path) -> Path:
    state = load_state(root)
    matrix = load_yaml(resolve_project_path(root, state["evidence"]["claim_evidence_path"]))
    claims = matrix["claims"]
    if not claims:
        raise ProtocolError("Figure/Table planning requires a non-empty Claim-Evidence Matrix")
    primary = [claim for claim in claims if claim["importance"] == "primary"]
    lines = ["# Figure / Table Plan", "", "The plan is Claim-first and intentionally compact.", ""]
    entries: list[dict[str, Any]] = [{
        "id": "Table 1", "type": "main result table", "purpose": "Present the controlled primary results.",
        "claim_ids": [claim["claim_id"] for claim in primary], "source_experiments": [item for claim in primary for item in _refs(claim)],
        "recommended_format": "Rows: methods/baselines; columns: primary metrics with uncertainty.",
        "key_message": "Whether the primary claims are supported under the approved protocol.",
        "must_show": "Fair baselines, seeds/statistics, and the full method.", "avoid": "Cherry-picked runs or preliminary Cheap Evaluation.",
    }]
    gap_types = {gap.get("evidence_type", "").lower() for claim in claims for gap in claim["remaining_gap"]}
    if any("ablation" in value for value in gap_types) or any(len(claim["supporting_experiments"]) > 1 for claim in claims):
        entries.append({
            "id": "Table 2", "type": "ablation table", "purpose": "Isolate necessary component contributions.",
            "claim_ids": [claim["claim_id"] for claim in claims], "source_experiments": [item for claim in claims for item in _refs(claim)],
            "recommended_format": "Controlled component removal/addition with identical protocol.", "key_message": "Which mechanism is necessary for each Claim.",
            "must_show": "Changed variable and matched controls.", "avoid": "Combining multiple changes in one row.",
        })
    analysis_claims = [claim for claim in claims if claim["boundary_experiments"] or claim["unresolved_confounds"]]
    for index, claim in enumerate(analysis_claims[:3], start=1):
        entries.append({
            "id": f"Figure {index}", "type": "boundary/failure analysis", "purpose": f"Show where {claim['claim_id']} holds or fails.",
            "claim_ids": [claim["claim_id"]], "source_experiments": _refs(claim), "recommended_format": "Compact case, curve, or grouped comparison appropriate to the metric.",
            "key_message": "The supported operating region and scientifically meaningful limitation.", "must_show": "Representative positive and boundary cases.",
            "avoid": "Hiding negative results or implying causality beyond the experiment.",
        })
    for entry in entries:
        lines.extend([
            f"## {entry['id']} — {entry['type']}", "", f"- Purpose: {entry['purpose']}",
            f"- Claim IDs: {', '.join(entry['claim_ids']) or 'none'}", f"- Source experiments: {', '.join(dict.fromkeys(entry['source_experiments'])) or 'none'}",
            f"- Recommended format: {entry['recommended_format']}", f"- Key message: {entry['key_message']}",
            f"- Must show: {entry['must_show']}", f"- Avoid: {entry['avoid']}", "",
        ])
    destination = resolve_project_path(root, state["evidence"]["figure_table_plan_path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def _claim_lines(claims: list[dict[str, Any]]) -> list[str]:
    return [f"- {claim['claim_id']} ({claim['importance']}): {claim['status']} / {claim['evidence_strength']}; formal evidence: {', '.join(_refs(claim)) or 'none'}" for claim in claims]


def build_experiment_report(root: Path) -> Path:
    state = load_state(root)
    if state["status"] != "EVIDENCE_FROZEN":
        raise ProtocolError("Final Experiment Report requires Evidence Freeze")
    matrix = load_yaml(resolve_project_path(root, state["evidence"]["claim_evidence_path"]))
    venue = load_yaml(resolve_project_path(root, state["evidence"]["venue_gap_path"]))
    readiness = load_yaml(resolve_project_path(root, state["evidence"]["readiness_path"]))
    queue = load_yaml(resolve_project_path(root, state["evidence"]["completion_queue_path"]))
    claims = matrix["claims"]
    negative = [(claim["claim_id"], item) for claim in claims for item in claim["contradicting_experiments"] + claim["boundary_experiments"]]
    gaps = [gap for gap in venue.get("gaps", []) if gap["current_status"] != "COMPLETE"]
    budget = state["budget"]
    spine = state["research_spine"]
    method = state.get("current_method") or {}
    sections = [
        ("1. Research Spine", [f"- Research question: {spine.get('research_question')}", f"- Core hypothesis: {spine.get('core_hypothesis')}", f"- Target venue: {state['venue'].get('target')}"]),
        ("2. Final Method", [f"- Method: {method.get('id', 'not recorded')}", f"- Artifact: {method.get('artifact_path', 'not recorded')}", f"- Method status: {matrix['method_status']}"]),
        ("3. Experimental Protocol", [f"- Contract: {state['experiment_contract']['path']} v{state['experiment_contract']['version']} ({state['experiment_contract']['status']})", "- Raw logs, metrics, environment, and artifacts remain under experiments/. "]),
        ("4. Main Results", _claim_lines([claim for claim in claims if claim["importance"] == "primary"])),
        ("5. Claim–Evidence Summary", _claim_lines(claims)),
        ("6. Supporting Evidence", [f"- {claim['claim_id']}: {', '.join(item['experiment_id'] for item in claim['supporting_experiments']) or 'none'}" for claim in claims]),
        ("7. Negative / Boundary Findings", [f"- {claim_id}: {item['experiment_id']} ({item['result_type']}) — {item['result_path']}" for claim_id, item in negative] or ["- None recorded."]),
        ("8. Venue Evidence Gaps", [f"- {gap['evidence_type']}: {gap['recommendation']} — {gap['reason']}" for gap in gaps] or ["- No material open gap."]),
        ("9. Remaining Weaknesses", [f"- {claim['claim_id']}: {gap['reason']}" for claim in claims for gap in claim["remaining_gap"]] or ["- No required Claim evidence gap recorded."]),
        ("10. Figure / Table Plan", [f"- See {state['evidence']['figure_table_plan_path']}. "]),
        ("11. Budget Review", [f"- Limits: {budget['limits']}", f"- Used: {budget['used']}", f"- Remaining recommendations: {len(queue['items'])}; executable P1 recommendations: {len(queue['active_recommendations'])}."]),
        ("12. Submission Readiness", [f"- Readiness: {readiness['readiness']}", f"- Hard gates: {readiness['hard_gates']}", f"- Evidence freeze: {state['evidence']['evidence_freeze']}"]),
        ("13. Recommended Next Step", [f"- {readiness['recommended_next_step']}", "- Ordinary experiment activation remains blocked while evidence is frozen."]),
    ]
    lines = ["# Final Experiment Report", ""]
    for title, body in sections:
        lines.extend([f"## {title}", "", *(body or ["- Not available."]), ""])
    destination = resolve_project_path(root, state["evidence"]["experiment_report_path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["figure-plan", "final-report"])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        print(build_figure_table_plan(args.root.resolve()) if args.command == "figure-plan" else build_experiment_report(args.root.resolve()))
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
