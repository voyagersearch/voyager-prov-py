"""Vitest-parallel tests for voyager-prov-py.

The Node.js sibling emits the same activity URN + JSON-LD structure — treat any
divergence between these two suites as a bug in one of them.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from voyager_prov import (
    EMPTY_REMAP,
    ActivityType,
    EmitOptions,
    ProvRecord,
    VOYAGER_ACTIVITY_NS,
    VOYAGER_URN_NS,
    activity_type_uri,
    emit,
    entity_uri,
)

T0 = "2026-08-24T12:00:00Z"
T1 = "2026-08-24T12:00:01Z"


def base_record() -> ProvRecord:
    return ProvRecord(
        activity_type="chunk",
        agent="urn:voyager:agent:mastra-chunker@1.0.0",
        used=[entity_uri("extracted-content", "AS_2226000_2026_178")],
        generated=[
            entity_uri("chunk", "AS_2226000_2026_178_0"),
            entity_uri("chunk", "AS_2226000_2026_178_1"),
        ],
        started_at=T0,
        ended_at=T1,
    )


# ------------------- entity_uri -------------------


def test_entity_uri_returns_deterministic_urn() -> None:
    assert entity_uri("chunk", "abc") == "urn:voyager:prov:entity:chunk:abc"
    assert entity_uri("chunk", "abc") == entity_uri("chunk", "abc")


def test_entity_uri_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError, match="kind is required"):
        entity_uri("", "x")
    with pytest.raises(ValueError, match="id is required"):
        entity_uri("k", "")


def test_entity_uri_rejects_hostile_chars() -> None:
    with pytest.raises(ValueError):
        entity_uri("k ind", "x")
    with pytest.raises(ValueError):
        entity_uri("kind", "x#y")
    with pytest.raises(ValueError):
        entity_uri("kind", "x?y")


# ------------------- activity_type_uri -------------------


def test_activity_type_uri_defaults_to_voyager_internal() -> None:
    assert activity_type_uri("embed") == f"{VOYAGER_ACTIVITY_NS}embed"
    assert activity_type_uri("embed", EMPTY_REMAP) == f"{VOYAGER_ACTIVITY_NS}embed"


def test_activity_type_uri_uses_remap_when_present() -> None:
    remap: dict[Any, str] = {"embed": "https://d110.ogc.org/registers/prov-activity/embed"}
    assert activity_type_uri("embed", remap) == remap["embed"]


def test_activity_type_uri_falls_back_for_unmapped_types() -> None:
    remap: dict[Any, str] = {"embed": "https://x/embed"}
    assert activity_type_uri("chunk", remap) == f"{VOYAGER_ACTIVITY_NS}chunk"


# ------------------- emit: return shape -------------------


def test_emit_solr_and_jsonld_share_activity_id() -> None:
    result = emit(base_record())
    assert result.solr_doc.id == result.solr_doc.prov_id == result.jsonld["@id"]
    assert result.solr_doc.id.startswith(f"{VOYAGER_URN_NS}activity:")


def test_emit_stamps_voyager_internal_activity_type_by_default() -> None:
    result = emit(base_record())
    expected = f"{VOYAGER_ACTIVITY_NS}chunk"
    assert result.solr_doc.prov_activityType == expected
    assert result.jsonld["prov:type"]["@id"] == expected


def test_emit_swaps_activity_type_when_remap_supplied() -> None:
    remap: dict[ActivityType, str] = {
        "chunk": "https://d110.ogc.org/registers/prov-activity/chunk"
    }
    result = emit(base_record(), EmitOptions(remap=remap))
    assert result.solr_doc.prov_activityType == remap["chunk"]
    assert result.jsonld["prov:type"]["@id"] == remap["chunk"]


def test_emit_sorts_used_and_generated_so_identity_is_order_insensitive() -> None:
    r1 = base_record()
    r2 = ProvRecord(
        activity_type=r1.activity_type,
        agent=r1.agent,
        used=r1.used,
        generated=list(reversed(r1.generated)),
        started_at=r1.started_at,
        ended_at=r1.ended_at,
    )
    a, b = emit(r1), emit(r2)
    assert a.solr_doc.id == b.solr_doc.id
    assert a.solr_doc.prov_generated == b.solr_doc.prov_generated


def test_emit_is_idempotent() -> None:
    a, b = emit(base_record()), emit(base_record())
    assert a.solr_doc.id == b.solr_doc.id
    assert a.solr_doc.prov_jsonld == b.solr_doc.prov_jsonld


def test_emit_extra_is_not_part_of_identity() -> None:
    with_extra = emit(
        ProvRecord(
            activity_type=base_record().activity_type,
            agent=base_record().agent,
            used=base_record().used,
            generated=base_record().generated,
            started_at=base_record().started_at,
            ended_at=base_record().ended_at,
            extra={"temperature": 0.7},
        )
    )
    without = emit(base_record())
    assert with_extra.solr_doc.id == without.solr_doc.id
    assert with_extra.jsonld["extra"] == {"temperature": 0.7}
    assert "extra" not in without.jsonld


def test_emit_carries_xsd_datetime_typed_timestamps() -> None:
    result = emit(base_record())
    assert result.jsonld["prov:startedAtTime"] == {"@value": T0, "@type": "xsd:dateTime"}
    assert result.jsonld["prov:endedAtTime"] == {"@value": T1, "@type": "xsd:dateTime"}


def test_emit_carries_used_and_generated_as_jsonld_id_refs() -> None:
    result = emit(base_record())
    assert result.jsonld["prov:used"] == [
        {"@id": "urn:voyager:prov:entity:extracted-content:AS_2226000_2026_178"}
    ]
    assert result.jsonld["prov:generated"] == [
        {"@id": "urn:voyager:prov:entity:chunk:AS_2226000_2026_178_0"},
        {"@id": "urn:voyager:prov:entity:chunk:AS_2226000_2026_178_1"},
    ]


# ------------------- emit: validation -------------------


def test_emit_rejects_unknown_activity_type() -> None:
    r = ProvRecord(
        activity_type="nope",  # type: ignore[arg-type]
        agent="a",
        used=[],
        generated=[],
        started_at=T0,
        ended_at=T1,
    )
    with pytest.raises(ValueError, match="unknown activity_type"):
        emit(r)


def test_emit_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="agent is required"):
        emit(
            ProvRecord(
                activity_type="chunk",
                agent="",
                used=[],
                generated=[],
                started_at=T0,
                ended_at=T1,
            )
        )


def test_emit_rejects_malformed_timestamps_and_inverted_intervals() -> None:
    with pytest.raises(ValueError, match="ISO 8601"):
        emit(
            ProvRecord(
                activity_type="chunk",
                agent="a",
                used=[],
                generated=[],
                started_at="yesterday",
                ended_at=T1,
            )
        )
    with pytest.raises(ValueError, match="must be <= ended_at"):
        emit(
            ProvRecord(
                activity_type="chunk",
                agent="a",
                used=[],
                generated=[],
                started_at=T1,
                ended_at=T0,
            )
        )


def test_emit_accepts_timezone_offset_iso8601() -> None:
    r = ProvRecord(
        activity_type="chunk",
        agent="a",
        used=[],
        generated=[],
        started_at="2026-08-24T04:00:00-08:00",
        ended_at="2026-08-24T04:00:01-08:00",
    )
    emit(r)  # must not raise


def test_solr_jsonld_field_parses_back_to_the_returned_jsonld() -> None:
    result = emit(base_record())
    assert json.loads(result.solr_doc.prov_jsonld) == result.jsonld


# ------------------- cross-language parity -------------------


def test_activity_id_matches_ts_reference_for_known_input() -> None:
    """Regression: this exact input produced this exact URN in voyager-prov-ts.

    If either implementation changes, this test flags the drift immediately.
    """
    r = ProvRecord(
        activity_type="chunk",
        agent="urn:voyager:agent:test",
        used=["u1"],
        generated=["g1"],
        started_at="2026-08-24T12:00:00Z",
        ended_at="2026-08-24T12:00:01Z",
    )
    result = emit(r)
    assert result.solr_doc.id == "urn:voyager:prov:activity:02956f0297bf4bc2838cf4f37b4dfce5"
