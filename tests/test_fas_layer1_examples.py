"""Validate the shipped declarative FAS Layer 1 example bundles.

Each bundle under ``src/voyager_prov/profile/examples/fas-layer-1/`` wraps
N single-Activity ProvJsonLd docs under a source envelope. This test walks
every bundle, feeds each activity through ``validate_prov_jsonld``, and
asserts they all pass — so a schema drift breaks this test immediately.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from voyager_prov import validate_prov_jsonld

EXAMPLES_DIR = (
    Path(__file__).parent.parent
    / "src"
    / "voyager_prov"
    / "profile"
    / "examples"
    / "fas-layer-1"
)

BUNDLES = sorted(EXAMPLES_DIR.glob("*.jsonld"))

EXPECTED_ACTIVITY_TYPES = {
    "ocr",
    "nlp-extract-entities",
    "geotag",
    "classify-commodity",
    "classify-region",
    "field-normalize",
}


def test_bundle_directory_is_populated() -> None:
    assert BUNDLES, f"no FAS Layer 1 bundles under {EXAMPLES_DIR}"
    # One file per FAS source in the deck's source table.
    assert len(BUNDLES) == 9, f"expected 9 source bundles, found {len(BUNDLES)}"


@pytest.mark.parametrize("bundle_path", BUNDLES, ids=lambda p: p.stem)
def test_every_activity_in_bundle_validates(bundle_path: Path) -> None:
    doc = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert "activities" in doc, f"{bundle_path.name} missing activities[]"
    assert doc["activities"], f"{bundle_path.name} has empty activities[]"
    for i, activity in enumerate(doc["activities"]):
        result = validate_prov_jsonld(activity)
        assert result.valid, (
            f"{bundle_path.name}#activities[{i}] failed schema: {result.errors}"
        )


@pytest.mark.parametrize("bundle_path", BUNDLES, ids=lambda p: p.stem)
def test_bundle_activity_types_are_layer1_or_ocr(bundle_path: Path) -> None:
    doc = json.loads(bundle_path.read_text(encoding="utf-8"))
    for activity in doc["activities"]:
        type_uri = activity["prov:type"]["@id"]
        assert type_uri.startswith("https://voyager.ogc/prov/activity/"), type_uri
        activity_type = type_uri.rsplit("/", 1)[-1]
        assert activity_type in EXPECTED_ACTIVITY_TYPES, (
            f"{bundle_path.name} references unknown Layer 1 op '{activity_type}'"
        )


def test_activity_urns_are_unique_across_all_bundles() -> None:
    """Declarative Activities are deterministic — collisions mean the URN
    hash isn't discriminating between distinct (source, op) pairs.
    """
    seen: dict[str, tuple[str, str]] = {}
    for bundle_path in BUNDLES:
        doc = json.loads(bundle_path.read_text(encoding="utf-8"))
        for activity in doc["activities"]:
            urn = activity["@id"]
            type_uri = activity["prov:type"]["@id"]
            if urn in seen:
                prior_source, prior_type = seen[urn]
                assert False, (
                    f"URN collision: {bundle_path.stem}/{type_uri} "
                    f"collides with {prior_source}/{prior_type}"
                )
            seen[urn] = (bundle_path.stem, type_uri)


def test_bundles_cite_the_fas_deck() -> None:
    for bundle_path in BUNDLES:
        doc = json.loads(bundle_path.read_text(encoding="utf-8"))
        cite = doc.get("hadPrimarySource", {}).get("@id", "")
        assert "docs.google.com/presentation" in cite, (
            f"{bundle_path.name} hadPrimarySource does not cite the FAS deck: {cite!r}"
        )
