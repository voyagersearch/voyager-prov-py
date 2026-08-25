"""JSON Schema validation for voyager-prov records.

Two validators — one for the input ProvRecord, one for the JSON-LD output.
Mirrors voyager-prov-ts's validate.ts. SHACL shape validation is documented
in ``profile/prov-graph.shapes.ttl`` but not wired here; running SHACL from
Python requires pulling ``pyshacl`` in, which is optional for v0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Iterable

from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class ValidationError:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[ValidationError]


def _load(name: str) -> dict[str, Any]:
    text = files("voyager_prov.profile").joinpath(name).read_text()
    schema: dict[str, Any] = json.loads(text)
    return schema


_RECORD_VALIDATOR = Draft202012Validator(_load("prov-record.schema.json"))
_JSONLD_VALIDATOR = Draft202012Validator(_load("prov-jsonld.schema.json"))


def validate_prov_record(record: Any) -> ValidationResult:
    """Validate a ProvRecord (or a dict version of one) against the profile."""
    return _run(_RECORD_VALIDATOR.iter_errors(record))


def validate_prov_jsonld(jsonld: Any) -> ValidationResult:
    """Validate the JSON-LD output of :func:`emit` against the profile."""
    return _run(_JSONLD_VALIDATOR.iter_errors(jsonld))


def _run(errors: Iterable[Any]) -> ValidationResult:
    shaped: list[ValidationError] = []
    for e in errors:
        path = "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else "/"
        shaped.append(ValidationError(path=path, message=e.message))
    return ValidationResult(valid=not shaped, errors=shaped)
