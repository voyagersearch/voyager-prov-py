"""SHACL gate for PROV JSON-LD (D100).

Complements :func:`validate_prov_jsonld` (JSON Schema, validates the envelope
shape) with graph-level constraints: every ``prov:Activity`` has exactly one
``prov:type`` IRI, exactly one ``prov:wasAssociatedWith`` IRI, timestamps
typed as ``xsd:dateTime``, ``prov:used[]`` / ``prov:generated[]`` values are
IRIs, and the activity ``@id`` matches the Voyager URN slot.

The shapes graph is
:file:`voyager_prov/profile/prov-graph.shapes.ttl`, shipped inside the
package. Callers pass a JSON-LD document (dict) — the same shape
:func:`voyager_prov.emit` returns as ``result.jsonld``.

Zero I/O beyond parsing the shapes file at first call. The parsed graph is
cached module-level because rdflib turtle parsing is not free.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

import pyshacl
import rdflib
from rdflib.namespace import Namespace

from .validate import ValidationError, ValidationResult

_SH = Namespace("http://www.w3.org/ns/shacl#")
_SHAPES_RESOURCE = "prov-graph.shapes.ttl"

# Lazy cache — first call parses the shapes; subsequent calls reuse the graph.
_shapes_graph: rdflib.Graph | None = None


def _load_shapes() -> rdflib.Graph:
    global _shapes_graph
    if _shapes_graph is not None:
        return _shapes_graph
    ttl = (
        resources.files("voyager_prov")
        .joinpath("profile")
        .joinpath(_SHAPES_RESOURCE)
        .read_text(encoding="utf-8")
    )
    g = rdflib.Graph()
    g.parse(data=ttl, format="turtle")
    _shapes_graph = g
    return g


def validate_prov_shapes(jsonld: Any) -> ValidationResult:
    """Validate a PROV JSON-LD document against the D100 SHACL shapes.

    Returns :class:`ValidationResult` matching :func:`validate_prov_jsonld`'s
    shape so both gates can be composed in CI.

    ``jsonld`` may be a single activity dict (what :func:`emit` returns), a
    JSON-LD ``@graph`` container wrapping N activities, or a bundle file's
    ``activities[]`` array — anything rdflib can parse. Anything not a dict
    or list is rejected up front so a bad type doesn't reach the parser.
    """
    if not isinstance(jsonld, (dict, list)):
        return ValidationResult(
            valid=False,
            errors=[
                ValidationError(
                    path="/",
                    message=f"expected a dict or list, got {type(jsonld).__name__}",
                )
            ],
        )
    try:
        data_graph = rdflib.Graph()
        data_graph.parse(data=json.dumps(jsonld), format="json-ld")
    except Exception as e:  # noqa: BLE001
        return ValidationResult(
            valid=False,
            errors=[ValidationError(path="/", message=f"JSON-LD parse failed: {e}")],
        )

    conforms, results_graph, _ = pyshacl.validate(
        data_graph,
        shacl_graph=_load_shapes(),
        inference="none",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=True,        # SPARQL-based shape (activity URN pattern) requires this
    )
    if conforms:
        return ValidationResult(valid=True, errors=[])
    return ValidationResult(valid=False, errors=_extract_errors(results_graph))


def _extract_errors(results_graph: rdflib.Graph) -> list[ValidationError]:
    """Walk the pyshacl results graph, pull one ValidationError per violation.

    Each violation carries a ``sh:focusNode`` (the offending node), a
    ``sh:resultPath`` (the field, when the constraint targets a property),
    and a ``sh:resultMessage`` (the human-readable text). We combine focus +
    path into ``path`` so the error line points somewhere useful.
    """
    errors: list[ValidationError] = []
    for r in results_graph.subjects(rdflib.RDF.type, _SH.ValidationResult):
        focus = results_graph.value(r, _SH.focusNode)
        path = results_graph.value(r, _SH.resultPath)
        message = results_graph.value(r, _SH.resultMessage)
        location = str(focus or "?")
        if path is not None:
            location += f" · {path}"
        errors.append(
            ValidationError(path=location, message=str(message or "SHACL violation"))
        )
    return errors
