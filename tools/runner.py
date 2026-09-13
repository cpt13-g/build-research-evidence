"""Minimal safe execution envelope for an active approved Card."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from common import DEFAULT_ROOT, ProtocolError, load_state, load_yaml, now_iso, resolve_project_path, validate_document


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        return None
    digest = hashlib.sha256()
    for item in files:
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(item).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _probe(command: list[str], cwd: Path, timeout: int = 5) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _git_identity(root: Path) -> dict[str, Any]:
    commit = _probe(["git", "rev-parse", "HEAD"], root)
    status = _probe(["git", "status", "--porcelain", "--", "src", "configs"], root)
    return {
        "commit": commit,
        "tracked_source_dirty": bool(status) if commit else None,
        "src_tree_sha256": _tree_sha256(root / "src"),
        "configs_tree_sha256": _tree_sha256(root / "configs"),
    }


def _environment_snapshot(root: Path) -> dict[str, Any]:
    packages = sorted(
        ({"name": distribution.metadata.get("Name") or "unknown", "version": distribution.version} for distribution in importlib.metadata.distributions()),
        key=lambda item: (item["name"].lower(), item["version"]),
    )
    gpu = None
    if shutil.which("nvidia-smi"):
        gpu = _probe(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            root,
        )
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "gpu": gpu,
        "packages": packages,
    }


def _artifact_entry(root: Path, path: Path, kind: str) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ProtocolError(f"Run artifacts must be stored inside the project: {path}") from error
    if not resolved.is_file():
        raise ProtocolError(f"Declared {kind} file does not exist: {relative}")
    return {"kind": kind, "path": relative, "sha256": _sha256(resolved), "size_bytes": resolved.stat().st_size}


def run(
    root: Path,
    item_id: str,
    command: list[str],
    timeout_seconds: int,
    metric_paths: list[Path] | None = None,
    artifact_paths: list[Path] | None = None,
) -> Path:
    if not command:
        raise ProtocolError("A command is required")
    state = load_state(root)
    item = next((entry for entry in state["experiment_registry"] if entry["id"] == item_id), None)
    if not item:
        raise ProtocolError(f"Unknown registry id: {item_id}")
    if item_id not in state["active_queue"] or item["status"] != "queued":
        raise ProtocolError("Runner requires a queued item in active_queue")
    card_path = resolve_project_path(root, item["card_path"])
    card_bytes = card_path.read_bytes()
    card = load_yaml(card_path)
    section = "experiment" if "experiment" in card else "tuning"
    if card[section]["status"] != "approved":
        raise ProtocolError("Runner requires an approved Card")

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    run_dir = root / "experiments" / item_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "run.log"
    started_at = now_iso()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
            check=False,
            env=os.environ.copy(),
        )
        output, exit_code, timed_out = completed.stdout, completed.returncode, False
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or "") + "\n[TIMEOUT]\n"
        exit_code, timed_out = 124, True
    log_path.write_text(output, encoding="utf-8")
    environment_path = run_dir / "environment.json"
    environment = _environment_snapshot(root)
    environment_path.write_text(json.dumps(environment, indent=2, ensure_ascii=False), encoding="utf-8")
    artifacts = [_artifact_entry(root, log_path, "log")]
    for path in metric_paths or []:
        artifacts.append(_artifact_entry(root, resolve_project_path(root, str(path)), "metrics"))
    for path in artifact_paths or []:
        artifacts.append(_artifact_entry(root, resolve_project_path(root, str(path)), "artifact"))
    body = card[section]
    code_identity = _git_identity(root)
    code_identity["command_sha256"] = hashlib.sha256(json.dumps(command, ensure_ascii=False).encode("utf-8")).hexdigest()
    missing_declarations = []
    if not body.get("seed_protocol"):
        missing_declarations.append("seed_protocol")
    if not body.get("datasets"):
        missing_declarations.append("datasets")
    if body.get("paper_evidence_eligible") and not any(item["kind"] == "metrics" for item in artifacts):
        missing_declarations.append("raw_metrics_artifact")
    record = {
        "schema_version": "1.0",
        "run_id": run_id,
        "experiment_id": item_id,
        "card_path": item["card_path"],
        "card_sha256": hashlib.sha256(card_bytes).hexdigest(),
        "command": command,
        "started_at": started_at,
        "ended_at": now_iso(),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "log_path": log_path.relative_to(root).as_posix(),
        "environment_path": environment_path.relative_to(root).as_posix(),
        "environment_sha256": _sha256(environment_path),
        "code_identity": code_identity,
        "configuration_identity": {
            "card_revision": body["card_revision"],
            "method_variant": body.get("method_variant"),
            "config_tree_sha256": code_identity["configs_tree_sha256"],
        },
        "data_identity": {
            "datasets": body.get("datasets", []),
            "seed_protocol": body.get("seed_protocol", {}),
        },
        "artifacts": artifacts,
        "manifest_completeness": "COMPLETE" if not missing_declarations else "PARTIAL",
        "missing_declarations": missing_declarations,
    }
    record_path = run_dir / "run_manifest.json"
    record["run_manifest_path"] = record_path.relative_to(root).as_posix()
    validate_document(record, root / "schemas" / "run_manifest.schema.json")
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--metric-file", type=Path, action="append", default=[])
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    try:
        print(run(args.root.resolve(), args.id, command, args.timeout_seconds, args.metric_file, args.artifact))
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
