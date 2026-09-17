"""Minimal, dependency-free JSON Schema validator.

`jsonschema` is not installed and `pip` is PEP 668-managed on this machine (see the
verification-integrity-defects plan, Task 1), so this implements exactly the keywords
`tests/live/runtime-evidence.schema.json` uses: `type`, `required`, `const`, `enum`,
`pattern`, `additionalProperties`, `items`, `properties`, `minLength`.

Any other keyword raises rather than being silently ignored. An ignored keyword is how
the original defect started: the schema documented `additionalProperties: false` and a
`requestUrl`/`role`/`weight`/`style` shape for each font entry, but nothing ever read the
schema, so the emitter drifted to `{family, loaded}` and nothing noticed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, List, Optional, Union

SUPPORTED_KEYWORDS = {
    "$schema", "type", "additionalProperties", "required", "properties",
    "const", "enum", "pattern", "items", "minLength",
}

_SIMPLE_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "null": type(None),
}


def _matches_type(value: Any, type_name: str) -> bool:
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _SIMPLE_TYPES[type_name])


def _describe(value: Any) -> str:
    return type(value).__name__ if value is not None else "null"


def _validate_node(value: Any, schema: dict, path: str, errors: List[str]) -> None:
    unsupported = set(schema) - SUPPORTED_KEYWORDS
    if unsupported:
        raise ValueError(f"unsupported schema keyword(s) at {path or '$'}: {sorted(unsupported)}")

    if "const" in schema:
        if value != schema["const"]:
            errors.append(f"{path}: expected constant {schema['const']!r}, got {value!r}")
        return
    if "enum" in schema:
        if value not in schema["enum"]:
            errors.append(f"{path}: {value!r} is not one of {schema['enum']}")
        return

    schema_type = schema.get("type")
    if schema_type is not None:
        type_names = schema_type if isinstance(schema_type, list) else [schema_type]
        if not any(_matches_type(value, name) for name in type_names):
            errors.append(f"{path}: expected type {schema_type}, got {_describe(value)}")
            return  # further structural checks would be meaningless against the wrong shape

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: {value!r} does not match pattern {schema['pattern']!r}")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field '{key}'")
        if schema.get("additionalProperties") is False:
            for key in sorted(set(value) - set(properties)):
                errors.append(f"{path}: unexpected field '{key}'")
        for key, subschema in properties.items():
            if key in value:
                _validate_node(value[key], subschema, f"{path}.{key}", errors)

    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate_node(item, schema["items"], f"{path}[{index}]", errors)


def validate(
    document: Any,
    schema_path: Optional[Union[str, Path]],
    *,
    schema: Optional[dict] = None,
) -> List[str]:
    """Validate `document` against the schema at `schema_path` (or the given `schema` dict).

    Returns a list of human-readable errors; an empty list means valid. Raises `ValueError`
    for a schema keyword this validator does not implement, rather than ignoring it.
    """
    if schema is None:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    errors: List[str] = []
    _validate_node(document, schema, "$", errors)
    return errors
