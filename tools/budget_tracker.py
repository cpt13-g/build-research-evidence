"""Check, reserve, release, and consume experiment budget."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from common import DEFAULT_ROOT, ProtocolError, load_state, save_state


def budget_view(state: dict[str, Any]) -> dict[str, dict[str, float]]:
    budget = state["budget"]
    keys = set(budget["limits"]) | set(budget["used"]) | set(budget["reserved"])
    remaining = {
        key: float(budget["limits"].get(key, 0))
        - float(budget["used"].get(key, 0))
        - float(budget["reserved"].get(key, 0))
        for key in keys
    }
    return {"limits": budget["limits"], "used": budget["used"], "reserved": budget["reserved"], "remaining": remaining}


def ensure_available(state: dict[str, Any], cost: dict[str, Any]) -> None:
    remaining = budget_view(state)["remaining"]
    shortages = {
        key: {"needed": float(value), "remaining": remaining.get(key, 0.0)}
        for key, value in cost.items()
        if isinstance(value, (int, float)) and float(value) > remaining.get(key, 0.0)
    }
    if shortages:
        raise ProtocolError(f"Insufficient budget: {shortages}. Recommend an extension; do not expand automatically.")


def mutate(root: Path, operation: str, cost: dict[str, Any], expected_revision: int, reason: str) -> dict[str, Any]:
    state = load_state(root)
    budget = state["budget"]
    if operation == "reserve":
        ensure_available(state, cost)
        target = budget["reserved"]
        sign = 1
    elif operation == "release":
        target = budget["reserved"]
        sign = -1
    elif operation == "consume":
        ensure_available(state, cost)
        target = budget["used"]
        sign = 1
    else:
        raise ProtocolError(f"Unknown budget operation: {operation}")
    for key, value in cost.items():
        if not isinstance(value, (int, float)) or value < 0:
            raise ProtocolError(f"Budget values must be non-negative numbers: {key}={value!r}")
        updated = float(target.get(key, 0)) + sign * float(value)
        if updated < 0:
            raise ProtocolError(f"Cannot release more {key} than reserved")
        target[key] = updated
    return save_state(root, state, expected_revision=expected_revision, event_type=f"budget_{operation}", event={"cost": cost, "reason": reason})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show")
    for command in ("reserve", "release", "consume"):
        sub = subparsers.add_parser(command)
        sub.add_argument("cost", help='YAML/JSON mapping, e.g. "{gpu_hours: 2}"')
        sub.add_argument("--expected-revision", type=int, required=True)
        sub.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        if args.command == "show":
            print(yaml.safe_dump(budget_view(load_state(args.root.resolve())), sort_keys=False))
        else:
            cost = yaml.safe_load(args.cost)
            if not isinstance(cost, dict):
                raise ProtocolError("Cost must be a mapping")
            print(mutate(args.root.resolve(), args.command, cost, args.expected_revision, args.reason)["revision"])
    except ProtocolError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

