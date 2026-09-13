"""Small dependency-free validator for the JSON Schema subset used by this project."""

from __future__ import annotations

import re
from typing import Any


class SchemaValidationError(ValueError):
    pass


TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise SchemaValidationError(f"Only local schema references are supported: {reference}")
    target: Any = root_schema
    for part in reference[2:].split("/"):
        target = target[part.replace("~1", "/").replace("~0", "~")]
    if not isinstance(target, dict):
        raise SchemaValidationError(f"Reference does not resolve to a schema: {reference}")
    return target


def validate(instance: Any, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def visit(value: Any, rule: dict[str, Any], path: str) -> None:
        if "$ref" in rule:
            visit(value, _resolve_ref(schema, rule["$ref"]), path)
            return
        expected = rule.get("type")
        if expected is not None:
            expected_types = expected if isinstance(expected, list) else [expected]
            valid = any(
                isinstance(value, TYPE_MAP[item]) and not (item in {"integer", "number"} and isinstance(value, bool))
                for item in expected_types
            )
            if not valid:
                errors.append(f"{path}: expected type {expected_types}, got {type(value).__name__}")
                return
        if "const" in rule and value != rule["const"]:
            errors.append(f"{path}: expected constant {rule['const']!r}")
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{path}: {value!r} is not one of {rule['enum']!r}")
        if isinstance(value, dict):
            for required in rule.get("required", []):
                if required not in value:
                    errors.append(f"{path}: missing required property {required!r}")
            properties = rule.get("properties", {})
            for key, child_rule in properties.items():
                if key in value:
                    visit(value[key], child_rule, f"{path}.{key}")
            if "minProperties" in rule and len(value) < rule["minProperties"]:
                errors.append(f"{path}: requires at least {rule['minProperties']} properties")
            additional = rule.get("additionalProperties")
            if isinstance(additional, dict):
                for key, child in value.items():
                    if key not in properties:
                        visit(child, additional, f"{path}.{key}")
        if isinstance(value, list):
            if "minItems" in rule and len(value) < rule["minItems"]:
                errors.append(f"{path}: requires at least {rule['minItems']} items")
            if isinstance(rule.get("items"), dict):
                for index, child in enumerate(value):
                    visit(child, rule["items"], f"{path}[{index}]")
        if isinstance(value, str):
            if "minLength" in rule and len(value) < rule["minLength"]:
                errors.append(f"{path}: string is shorter than {rule['minLength']}")
            if "pattern" in rule and not re.search(rule["pattern"], value):
                errors.append(f"{path}: {value!r} does not match {rule['pattern']!r}")
        if isinstance(value, int) and not isinstance(value, bool) and "minimum" in rule and value < rule["minimum"]:
            errors.append(f"{path}: {value} is less than {rule['minimum']}")

    visit(instance, schema, "<root>")
    return errors

