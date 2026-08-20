import copy
import re
from typing import Any

from jsonschema import Draft202012Validator

ALLOWED_TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}
ALLOWED_KEYWORDS = {"$schema", "type", "properties", "items", "required", "description", "enum", "additionalProperties", "minimum", "maximum", "minLength", "maxLength", "pattern", "format", "title", "default", "examples"}


def validate_processor_schema(schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    root_type = schema.get("type")
    if root_type != "object":
        raise ValueError("Processor schema root must be an object")

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        unknown = set(node) - ALLOWED_KEYWORDS
        if unknown:
            raise ValueError(f"Unsupported JSON Schema keyword: {sorted(unknown)[0]}")
        types = node.get("type", [])
        types = [types] if isinstance(types, str) else types
        if any(item not in ALLOWED_TYPES for item in types):
            raise ValueError("Unsupported JSON Schema type")
        for child in node.get("properties", {}).values():
            walk(child)
        if isinstance(node.get("items"), dict):
            walk(node["items"])
    walk(schema)


def json_path_tokens(path: str) -> list[str | int]:
    if not path.startswith("$"):
        raise ValueError("Invalid JSON path")
    return [int(index) if index else key for key, index in re.findall(r"\.([^\.\[]+)|\[(\d+)\]", path)]


def get_path(data: Any, path: str) -> Any:
    current = data
    for token in json_path_tokens(path):
        current = current[token]
    return current


def set_path(data: Any, path: str, value: Any) -> None:
    tokens = json_path_tokens(path)
    current = data
    for token in tokens[:-1]:
        current = current[token]
    if not tokens:
        raise ValueError("Cannot replace root")
    current[tokens[-1]] = value


def apply_overrides(raw: dict[str, Any], overrides: list[Any]) -> dict[str, Any]:
    effective = copy.deepcopy(raw)
    latest: dict[str, Any] = {}
    for override in overrides:
        latest[override.json_path] = override
    for path, override in latest.items():
        if override.action == "reset":
            continue
        if override.action == "correct":
            set_path(effective, path, override.override_value)
    return effective


def flatten_leaves(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        return [item for key, child in value.items() for item in flatten_leaves(child, f"{path}.{key}")]
    if isinstance(value, list):
        return [item for index, child in enumerate(value) for item in flatten_leaves(child, f"{path}[{index}]")]
    return [(path, value)]
