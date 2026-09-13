"""Shared deterministic I/O and validation helpers."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from schema_validator import validate


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


class ProtocolError(RuntimeError):
    """Raised when a project protocol or invariant is violated."""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ProtocolError(f"Missing YAML file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProtocolError(f"Expected a YAML mapping: {path}")
    return data


def atomic_yaml_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def validate_document(document: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = validate(document, schema)
    if errors:
        raise ProtocolError("Schema validation failed:\n- " + "\n- ".join(errors[:20]))


def state_paths(root: Path) -> tuple[Path, Path]:
    return root / "research" / "research_state.yaml", root / "schemas" / "research_state.schema.json"


def load_state(root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    state_path, schema_path = state_paths(root)
    state = load_yaml(state_path)
    validate_document(state, schema_path)
    return state


def save_state(
    root: Path,
    state: dict[str, Any],
    *,
    expected_revision: int,
    event_type: str,
    event: dict[str, Any],
) -> dict[str, Any]:
    state_path, schema_path = state_paths(root)
    current = load_yaml(state_path)
    actual_revision = current.get("revision")
    if actual_revision != expected_revision:
        raise ProtocolError(
            f"Stale state revision: expected {expected_revision}, current {actual_revision}. Reload before writing."
        )
    state["revision"] = expected_revision + 1
    state["project"]["updated_at"] = now_iso()
    validate_document(state, schema_path)
    atomic_yaml_write(state_path, state)
    append_memory(root, event_type, {"state_revision": state["revision"], **event})
    return state


def append_memory(root: Path, event_type: str, payload: dict[str, Any]) -> None:
    state_path = root / "research" / "research_state.yaml"
    state = load_yaml(state_path)
    relative = state.get("memory_path", "evidence/experiment_memory.jsonl")
    memory_path = root / relative
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": now_iso(), "event_type": event_type, **payload}
    with memory_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def resolve_project_path(root: Path, path_text: str) -> Path:
    candidate = (root / path_text).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as error:
        raise ProtocolError(f"Path escapes project root: {path_text}") from error
    return candidate


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_run_manifest(
    root: Path,
    path_text: str,
    *,
    expected_run_id: str | None = None,
    expected_experiment_id: str | None = None,
    require_complete: bool = False,
) -> dict[str, Any]:
    path = resolve_project_path(root, path_text)
    if not path.exists():
        raise ProtocolError(f"Missing run manifest: {path_text}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProtocolError(f"Invalid run manifest: {path_text}") from error
    validate_document(manifest, root / "schemas" / "run_manifest.schema.json")
    if expected_run_id and manifest["run_id"] != expected_run_id:
        raise ProtocolError("Result and run manifest run_id disagree")
    if expected_experiment_id and manifest["experiment_id"] != expected_experiment_id:
        raise ProtocolError("Result and run manifest experiment_id disagree")
    if manifest["run_manifest_path"] != path.relative_to(root.resolve()).as_posix():
        raise ProtocolError("Run manifest self-reference is stale")
    card_path = resolve_project_path(root, manifest["card_path"])
    if not card_path.is_file() or file_sha256(card_path) != manifest["card_sha256"]:
        raise ProtocolError("Run manifest Card hash mismatch")
    environment_path = resolve_project_path(root, manifest["environment_path"])
    if not environment_path.is_file() or file_sha256(environment_path) != manifest["environment_sha256"]:
        raise ProtocolError("Run manifest environment hash mismatch")
    for artifact in manifest["artifacts"]:
        artifact_path = resolve_project_path(root, artifact["path"])
        if not artifact_path.is_file() or file_sha256(artifact_path) != artifact["sha256"] or artifact_path.stat().st_size != artifact["size_bytes"]:
            raise ProtocolError(f"Run artifact integrity mismatch: {artifact['path']}")
    if require_complete and manifest["manifest_completeness"] != "COMPLETE":
        raise ProtocolError(f"Formal Claim Evidence requires a complete run manifest; missing: {manifest['missing_declarations']}")
    return manifest


def set_nested(mapping: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    target: dict[str, Any] = mapping
    for part in parts[:-1]:
        child = target.get(part)
        if not isinstance(child, dict):
            raise ProtocolError(f"Not a mapping at {part!r} in {dotted_path!r}")
        target = child
    if parts[-1] not in target:
        raise ProtocolError(f"Unknown state field: {dotted_path}")
    target[parts[-1]] = value
