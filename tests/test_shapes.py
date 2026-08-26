"""SHACL gate tests for voyager-prov-py.

Complements ``test_validate.py`` (JSON Schema layer). Each test constructs a
minimal PROV JSON-LD, feeds it through :func:`validate_prov_shapes`, and
asserts the outcome the SHACL shapes should produce.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from voyager_prov import emit, entity_uri, validate_prov_shapes
from voyager_prov.types import ProvRecord

T0 = "2026-08-25T12:00:00Z"
T1 = "2026-08-25T12:00:01Z"


def _emit_valid_jsonld() -> dict[str, Any]:
    """A JSON-LD blob :func:`emit` produces for a canonical chunk activity."""
    r = ProvRecord(
        activity_type="chunk",
        agent="urn:voyager:agent:mastra-chunker@1.0.0",
        used=[entity_uri("extracted-content", "P1")],
        generated=[entity_uri("chunk", "P1_0")],
        started_at=T0,
        ended_at=T1,
    )
    return emit(r).jsonld


def test_valid_record_conforms() -> None:
    result = validate_prov_shapes(_emit_valid_jsonld())
    assert result.valid, result.errors


def test_missing_prov_type_fails() -> None:
    bad = deepcopy(_emit_valid_jsonld())
    del bad["prov:type"]
    result = validate_prov_shapes(bad)
    assert not result.valid
    assert any("prov:type" in e.message or "prov:type" in e.path for e in result.errors)


def test_startedAtTime_missing_datatype_fails() -> None:
    """SHACL constraint: prov:startedAtTime must be typed xsd:dateTime."""
    bad = deepcopy(_emit_valid_jsonld())
    # Drop the @type so the literal is a plain string, not xsd:dateTime.
    bad["prov:startedAtTime"] = {"@value": T0}
    result = validate_prov_shapes(bad)
    assert not result.valid


def test_used_as_literal_string_fails() -> None:
    """SHACL constraint: prov:used values must be IRIs, not literals."""
    bad = deepcopy(_emit_valid_jsonld())
    bad["prov:used"] = ["not-an-iri"]  # literal string, not { @id: ... }
    result = validate_prov_shapes(bad)
    assert not result.valid


def test_activity_id_outside_voyager_urn_still_passes_shacl() -> None:
    """The URN pattern check moved to JSON Schema (`prov-jsonld.schema.json`).

    SHACL is only responsible for graph shape; the @id pattern lives in
    validate_prov_jsonld() where it runs without a SPARQL engine. This test
    documents that a non-Voyager @id is well-formed as a graph — the caller
    should compose JSON Schema + SHACL for the full gate.
    """
    doc = deepcopy(_emit_valid_jsonld())
    doc["@id"] = "urn:some-other-scheme:definitely-not-us"
    result = validate_prov_shapes(doc)
    assert result.valid, result.errors


def test_non_dict_or_list_rejected_early() -> None:
    result = validate_prov_shapes("just a string")  # type: ignore[arg-type]
    assert not result.valid
    assert "expected a dict or list" in result.errors[0].message


def test_multiple_activities_in_graph_all_validated() -> None:
    """Feed a JSON-LD @graph with three activities — all should conform."""
    activities = [_emit_valid_jsonld() for _ in range(3)]
    # Give them distinct URNs so the graph doesn't merge them by @id.
    for i, a in enumerate(activities):
        a["@id"] = f"urn:voyager:prov:activity:{i:032x}"
    graph_doc = {
        "@context": activities[0]["@context"],
        "@graph": activities,
    }
    result = validate_prov_shapes(graph_doc)
    assert result.valid, result.errors


def test_bundle_examples_style_array_validates() -> None:
    """The declarative FAS bundles ship activities as a plain array under a
    top-level key — walking that shape should still validate each entry."""
    activities = [_emit_valid_jsonld() for _ in range(2)]
    for i, a in enumerate(activities):
        a["@id"] = f"urn:voyager:prov:activity:{i:032x}"
    result = validate_prov_shapes(activities)
    assert result.valid, result.errors


def test_startedAtTime_bad_value_fails() -> None:
    """Even with `@type: xsd:dateTime`, an obviously non-date lexical value
    must fail — the JSON-LD parser + SHACL together reject it.

    Values shaped like ISO but with impossible fields (`2026-13-99T99:99:99Z`)
    are accepted by SHACL per the letter of the spec; the lexical-form gate
    for those lives in the JSON Schema pattern layer.
    """
    bad = deepcopy(_emit_valid_jsonld())
    bad["prov:startedAtTime"] = {"@value": "not-a-date", "@type": "xsd:dateTime"}
    result = validate_prov_shapes(bad)
    assert not result.valid
