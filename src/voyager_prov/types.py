"""Type shapes for voyager-prov-py, mirroring voyager-prov-ts.

Loose W3C PROV concepts (Activity, Agent, Entity, wasStartedAt, used, generated)
subsetted for the D100 Workflow Profiler deliverable. Kept intentionally thin
so downstream services can adopt PROV emission without pulling in a full RDF
toolchain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional

# Voyager pipeline activityType stubs.
#
# Layer 2 (RAG pipeline, main plan): connect | extract | chunk | embed | retrieve | generate.
# Layer 1 (HQ-side FAS enrichment, Appendix A — CFP §5.1 geospatial-ops
# alignment): geotag | classify-commodity | classify-region |
# nlp-extract-entities | ocr | field-normalize.
#
# When D110's register hardens, `activity_type_uri()` swaps any of these to
# register URIs at emission time — the shape is stable across both layers.
ActivityType = Literal[
    # Layer 2 — RAG pipeline
    "connect",
    "extract",
    "chunk",
    "embed",
    "retrieve",
    "generate",
    # Layer 1 — HQ-side FAS enrichment
    "geotag",
    "classify-commodity",
    "classify-region",
    "nlp-extract-entities",
    "ocr",
    "field-normalize",
]

# Voyager-internal namespace for activityType URIs.
VOYAGER_ACTIVITY_NS = "https://voyager.ogc/prov/activity/"

# Voyager-internal namespace for entity + activity URNs.
VOYAGER_URN_NS = "urn:voyager:prov:"

# Partial mapping: only activityTypes with a known D110 URI need entries.
RemapTable = Mapping[ActivityType, str]


@dataclass(frozen=True)
class ProvRecord:
    """Input to :func:`voyager_prov.emit`."""

    activity_type: ActivityType
    agent: str
    used: list[str]
    generated: list[str]
    started_at: str
    ended_at: str
    extra: Optional[Mapping[str, Any]] = None


@dataclass(frozen=True)
class SolrProvDoc:
    """Ready-to-index Solr doc for the shared ``main`` collection."""

    id: str
    prov_id: str
    prov_activityType: str
    prov_agent: str
    prov_used: list[str]
    prov_generated: list[str]
    prov_startedAt: str
    prov_endedAt: str
    prov_jsonld: str

    def as_dict(self) -> dict[str, Any]:
        """Return the doc as a plain dict, matching Solr's JSON field naming."""
        return {
            "id": self.id,
            "prov_id": self.prov_id,
            "prov_activityType": self.prov_activityType,
            "prov_agent": self.prov_agent,
            "prov_used": list(self.prov_used),
            "prov_generated": list(self.prov_generated),
            "prov_startedAt": self.prov_startedAt,
            "prov_endedAt": self.prov_endedAt,
            "prov_jsonld": self.prov_jsonld,
        }


# JSON-LD is a plain dict at runtime — a typed dict shape is documented in the
# emit() docstring, but returning ``dict[str, Any]`` keeps callers honest that
# it's data, not a rich model.
ProvJsonLd = dict[str, Any]


@dataclass(frozen=True)
class EmitResult:
    """Return value of :func:`voyager_prov.emit`."""

    solr_doc: SolrProvDoc
    jsonld: ProvJsonLd


@dataclass(frozen=True)
class EmitOptions:
    """Options passed to :func:`voyager_prov.emit`.

    ``remap`` — a partial mapping from activityType to D110 register URIs.
    Missing entries fall back to :data:`VOYAGER_ACTIVITY_NS` + activityType.
    """

    remap: Mapping[ActivityType, str] = field(default_factory=dict)
