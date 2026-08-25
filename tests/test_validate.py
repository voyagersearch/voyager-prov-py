"""JSON Schema validation tests — mirrors voyager-prov-ts's validate.test.ts."""

from __future__ import annotations

from typing import Any

from voyager_prov import (
    ProvRecord,
    emit,
    entity_uri,
    validate_prov_jsonld,
    validate_prov_record,
)

T0 = "2026-08-24T12:00:00Z"
T1 = "2026-08-24T12:00:01Z"


def _good_record_dict() -> dict[str, Any]:
    return {
        "activity_type": "chunk",
        "agent": "urn:voyager:agent:mastra-chunker@1.0.0",
        "used": [entity_uri("extracted-content", "P1")],
        "generated": [entity_uri("chunk", "P1_0")],
        "started_at": T0,
        "ended_at": T1,
    }


# ─────────────────── validate_prov_record ───────────────────


def test_accepts_a_well_formed_record() -> None:
    r = validate_prov_record(_good_record_dict())
    assert r.valid is True
    assert r.errors == []


def test_rejects_a_missing_required_field() -> None:
    bad = _good_record_dict()
    del bad["agent"]
    r = validate_prov_record(bad)
    assert r.valid is False
    assert any("agent" in e.message for e in r.errors)


def test_rejects_an_unknown_activity_type() -> None:
    bad = _good_record_dict()
    bad["activity_type"] = "nope"
    r = validate_prov_record(bad)
    assert r.valid is False
    assert any(e.path.endswith("/activity_type") for e in r.errors)


def test_rejects_a_malformed_timestamp() -> None:
    bad = _good_record_dict()
    bad["started_at"] = "yesterday"
    r = validate_prov_record(bad)
    assert r.valid is False
    assert any(e.path.endswith("/started_at") for e in r.errors)


def test_rejects_extra_properties() -> None:
    bad = _good_record_dict()
    bad["agnet"] = "typo"
    r = validate_prov_record(bad)
    assert r.valid is False
    assert any("additional" in e.message.lower() for e in r.errors)


def test_accepts_optional_extra_object() -> None:
    good = _good_record_dict()
    good["extra"] = {"model": "haiku-4.5"}
    r = validate_prov_record(good)
    assert r.valid is True
    assert r.errors == []


# ─────────────────── validate_prov_jsonld ───────────────────


def _record() -> ProvRecord:
    return ProvRecord(
        activity_type="chunk",
        agent="urn:voyager:agent:mastra-chunker@1.0.0",
        used=[entity_uri("extracted-content", "P1")],
        generated=[entity_uri("chunk", "P1_0")],
        started_at=T0,
        ended_at=T1,
    )


def test_validates_every_jsonld_emit_produces() -> None:
    result = emit(_record())
    r = validate_prov_jsonld(result.jsonld)
    assert r.valid is True
    assert r.errors == []


def test_rejects_jsonld_with_bogus_id_shape() -> None:
    result = emit(_record())
    bad = {**result.jsonld, "@id": "not-a-voyager-urn"}
    r = validate_prov_jsonld(bad)
    assert r.valid is False
    assert any(e.path == "/@id" for e in r.errors)


def test_rejects_jsonld_missing_prov_type() -> None:
    result = emit(_record())
    bad = {**result.jsonld}
    del bad["prov:type"]
    r = validate_prov_jsonld(bad)
    assert r.valid is False
    assert any("prov:type" in e.message for e in r.errors)


def test_rejects_bad_started_at_time_literal() -> None:
    result = emit(_record())
    bad = {
        **result.jsonld,
        "prov:startedAtTime": {"@value": "yesterday", "@type": "xsd:dateTime"},
    }
    r = validate_prov_jsonld(bad)
    assert r.valid is False
