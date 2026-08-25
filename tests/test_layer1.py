"""Layer 1 (HQ-side FAS enrichment) activity-type coverage — Python side.

Mirrors voyager-prov-ts/tests/layer1.test.ts. Layer 2 (RAG pipeline) types are
exercised by test_emit.py + test_validate.py; this module asserts each new
Layer 1 type emits, validates, and remaps through the same code paths.
"""

from __future__ import annotations

from typing import cast, get_args

import pytest

from voyager_prov import (
    ProvRecord,
    activity_type_uri,
    emit,
    entity_uri,
    validate_prov_jsonld,
    validate_prov_record,
)
from voyager_prov.types import VOYAGER_ACTIVITY_NS, ActivityType

T0 = "2026-08-25T12:00:00Z"
T1 = "2026-08-25T12:00:01Z"

LAYER_1_TYPES: list[ActivityType] = [
    "geotag",
    "classify-commodity",
    "classify-region",
    "nlp-extract-entities",
    "ocr",
    "field-normalize",
]


def _fas_record(activity_type: ActivityType) -> ProvRecord:
    return ProvRecord(
        activity_type=activity_type,
        agent=f"urn:voyager:agent:hq-step:{activity_type}",
        used=[entity_uri("indexed-doc", "fas_wap_argentina_2026Q3")],
        generated=[entity_uri("indexed-doc", "fas_wap_argentina_2026Q3+enriched")],
        started_at=T0,
        ended_at=T1,
    )


# ------------------- emit() -------------------


@pytest.mark.parametrize("activity_type", LAYER_1_TYPES)
def test_emit_produces_valid_solr_doc(activity_type: ActivityType) -> None:
    result = emit(_fas_record(activity_type))
    assert result.solr_doc.prov_activityType == f"{VOYAGER_ACTIVITY_NS}{activity_type}"
    assert result.jsonld["prov:type"]["@id"] == f"{VOYAGER_ACTIVITY_NS}{activity_type}"
    assert result.solr_doc.id.startswith("urn:voyager:prov:activity:")
    # 32-hex slice: length 25 (urn prefix) + 32 (digest) = 57.
    assert len(result.solr_doc.id) == len("urn:voyager:prov:activity:") + 32


def test_distinct_layer1_types_produce_distinct_activity_urns() -> None:
    ids = {emit(_fas_record(t)).solr_doc.id for t in LAYER_1_TYPES}
    assert len(ids) == len(LAYER_1_TYPES)


# ------------------- validate -------------------


@pytest.mark.parametrize("activity_type", LAYER_1_TYPES)
def test_record_validates_for_layer1_type(activity_type: ActivityType) -> None:
    result = validate_prov_record(
        {
            "activity_type": activity_type,
            "agent": f"urn:voyager:agent:hq-step:{activity_type}",
            "used": [entity_uri("indexed-doc", "P1")],
            "generated": [entity_uri("indexed-doc", "P1+enriched")],
            "started_at": T0,
            "ended_at": T1,
        }
    )
    assert result.valid, result.errors


@pytest.mark.parametrize("activity_type", LAYER_1_TYPES)
def test_emit_output_validates_for_layer1_type(activity_type: ActivityType) -> None:
    result = emit(_fas_record(activity_type))
    v = validate_prov_jsonld(result.jsonld)
    assert v.valid, v.errors


# ------------------- remap -------------------


def test_layer1_types_remap_to_d110_uris_when_configured() -> None:
    remap: dict[ActivityType, str] = {
        "classify-commodity": "https://d110.ogc.org/registers/prov-activity/classify-commodity",
        "classify-region": "https://d110.ogc.org/registers/prov-activity/classify-region",
        "geotag": "https://d110.ogc.org/registers/prov-activity/geotag",
    }
    assert activity_type_uri("classify-commodity", remap) == remap["classify-commodity"]
    assert activity_type_uri("classify-region", remap) == remap["classify-region"]
    assert activity_type_uri("geotag", remap) == remap["geotag"]
    # Unmapped Layer 1 types fall back to the Voyager-internal namespace.
    assert activity_type_uri("ocr", remap) == f"{VOYAGER_ACTIVITY_NS}ocr"


# ------------------- cross-file sanity -------------------


def test_layer1_types_are_all_declared_in_the_activity_type_literal() -> None:
    """If someone deletes a Layer 1 value from ActivityType, this fails fast."""
    declared = set(get_args(cast(type, ActivityType)))
    assert set(LAYER_1_TYPES).issubset(declared)
