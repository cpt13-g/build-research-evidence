"""Validate schemas, templates, live state, Skill metadata, and references."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import yaml

from common import DEFAULT_ROOT, ProtocolError, load_yaml, validate_document


DOCUMENTS = {
    "templates/research_state.yaml": "schemas/research_state.schema.json",
    "templates/experiment_contract.yaml": "schemas/experiment_contract.schema.json",
    "templates/functional_requirement.yaml": "schemas/functional_requirement.schema.json",
    "templates/design_envelope.yaml": "schemas/design_envelope.schema.json",
    "templates/candidate_mechanism.yaml": "schemas/candidate_mechanism.schema.json",
    "templates/candidate_screening.yaml": "schemas/candidate_screening.schema.json",
    "templates/candidate_decision.yaml": "schemas/candidate_decision.schema.json",
    "templates/design_iteration.yaml": "schemas/design_iteration.schema.json",
    "templates/experiment_card.yaml": "schemas/experiment_card.schema.json",
    "templates/tuning_card.yaml": "schemas/tuning_card.schema.json",
    "templates/result_record.yaml": "schemas/result_record.schema.json",
    "templates/method_lineage.yaml": "schemas/method_lineage.schema.json",
    "templates/gate2_summary.yaml": "schemas/gate2_summary.schema.json",
    "templates/claim_evidence.yaml": "schemas/claim_evidence.schema.json",
    "templates/venue_gap.yaml": "schemas/venue_gap.schema.json",
    "templates/evidence_completion_queue.yaml": "schemas/evidence_completion_queue.schema.json",
    "templates/readiness.yaml": "schemas/readiness.schema.json",
    "research/research_state.yaml": "schemas/research_state.schema.json",
    "research/experiment_contract.yaml": "schemas/experiment_contract.schema.json",
    "evidence/method_lineage.yaml": "schemas/method_lineage.schema.json",
    "evidence/claim_evidence.yaml": "schemas/claim_evidence.schema.json",
    "evidence/venue_gap.yaml": "schemas/venue_gap.schema.json",
    "evidence/evidence_completion_queue.yaml": "schemas/evidence_completion_queue.schema.json",
    "evidence/readiness.yaml": "schemas/readiness.schema.json",
}

SKILLS = ["experiment-orchestrator", "experiment-runner", "result-auditor", "venue-evidence-audit"]

RUNTIME_DOCUMENTS = [
    "AGENTS.md",
    "Research Spine.md",
    "docs/PROTOCOLS.md",
    "docs/ROLE_HANDOFFS.md",
    "docs/STATE_MACHINE.md",
    "docs/METHOD_REALIZATION_PROTOCOL.md",
    "docs/EVIDENCE_COMPLETION_PROTOCOL.md",
]

REFERENCE_PREFIXES = ("research/", "docs/", "tools/", "templates/", "schemas/", ".agents/")
REFERENCE_PATTERN = re.compile(r"`([^`\n]+\.(?:md|yaml|py|json))`")


def _tracked_files(root: Path) -> set[str] | None:
    """Return Git-tracked files, or None for a source archive without Git metadata."""
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return {
        item.decode("utf-8").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def _validate_runtime_reference(root: Path, reference: str, tracked: set[str] | None) -> None:
    normalized = reference.replace("\\", "/")
    if not normalized.startswith(REFERENCE_PREFIXES):
        return
    if not (root / normalized).exists():
        raise ProtocolError(f"Broken runtime reference: {normalized}")
    if tracked is not None and normalized not in tracked:
        raise ProtocolError(
            f"Runtime reference is present locally but absent from the published repository: {normalized}"
        )


def validate_runtime_documents(root: Path) -> list[str]:
    """Ensure runtime instructions are self-contained in a clone or source archive."""
    tracked = _tracked_files(root)
    sources = [*RUNTIME_DOCUMENTS, *(f".agents/skills/{skill}/SKILL.md" for skill in SKILLS)]
    messages: list[str] = []
    for source in sources:
        source_path = root / source
        if not source_path.exists():
            raise ProtocolError(f"Missing runtime document: {source}")
        if tracked is not None and source.replace("\\", "/") not in tracked:
            raise ProtocolError(f"Runtime document is not included in the published repository: {source}")
        for reference in REFERENCE_PATTERN.findall(source_path.read_text(encoding="utf-8")):
            _validate_runtime_reference(root, reference, tracked)
        messages.append(f"runtime document OK: {source}")
    return messages


def validate_project(root: Path) -> list[str]:
    messages: list[str] = []
    for schema_text in sorted((root / "schemas").glob("*.json")):
        schema = json.loads(schema_text.read_text(encoding="utf-8"))
        if not isinstance(schema, dict) or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ProtocolError(f"Invalid or unsupported schema declaration: {schema_text}")
        messages.append(f"schema OK: {schema_text.relative_to(root)}")
    for document_text, schema_text in DOCUMENTS.items():
        validate_document(load_yaml(root / document_text), root / schema_text)
        messages.append(f"document OK: {document_text}")
    for skill in SKILLS:
        skill_dir = root / ".agents" / "skills" / skill
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", skill_text, flags=re.DOTALL)
        if not match:
            raise ProtocolError(f"Invalid frontmatter: {skill}")
        frontmatter = yaml.safe_load(match.group(1))
        if frontmatter.get("name") != skill or not frontmatter.get("description"):
            raise ProtocolError(f"Skill identity mismatch: {skill}")
        openai = load_yaml(skill_dir / "agents" / "openai.yaml")
        default_prompt = openai.get("interface", {}).get("default_prompt", "")
        if f"${skill}" not in default_prompt:
            raise ProtocolError(f"Default prompt must mention ${skill}")
        messages.append(f"skill OK: {skill}")
    messages.extend(validate_runtime_documents(root))
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        for message in validate_project(args.root.resolve()):
            print(message)
    except (ProtocolError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
