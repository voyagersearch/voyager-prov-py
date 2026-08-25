"""Emit a PROV record for one activity in the Voyager RAG pipeline.

Mirrors voyager-prov-ts's emit.ts. Produces two artefacts from the same input:

- a Solr doc ready to index into the shared ``main`` collection (matches the
  ``prov_*`` fields defined in the D100 plan);
- a PROV-JSON-LD blob conformant with the W3C PROV subset the D100 profile
  cares about.

The activity URN is a SHA-256 hash of identity-defining inputs so retries
converge on the same id.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Mapping, Optional

from .remap import activity_type_uri
from .types import (
    VOYAGER_URN_NS,
    ActivityType,
    EmitOptions,
    EmitResult,
    ProvJsonLd,
    ProvRecord,
    SolrProvDoc,
)

_ACTIVITY_URN_PREFIX = f"{VOYAGER_URN_NS}activity:"
_ACTIVITY_TYPES: set[ActivityType] = {
    "connect",
    "extract",
    "chunk",
    "embed",
    "retrieve",
    "generate",
}
# ISO 8601 with Z or ±HH:MM offset; millisecond precision optional.
_ISO_INSTANT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$"
)


def emit(record: ProvRecord, options: Optional[EmitOptions] = None) -> EmitResult:
    _validate(record)
    remap = options.remap if options is not None else None
    type_uri = activity_type_uri(record.activity_type, remap)
    activity_id = _derive_activity_id(record, type_uri)

    used_sorted = sorted(record.used)
    generated_sorted = sorted(record.generated)

    jsonld: ProvJsonLd = {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "voyager": VOYAGER_URN_NS,
        },
        "@id": activity_id,
        "@type": "prov:Activity",
        "prov:type": {"@id": type_uri},
        "prov:wasAssociatedWith": {"@id": record.agent},
        "prov:used": [{"@id": u} for u in used_sorted],
        "prov:generated": [{"@id": g} for g in generated_sorted],
        "prov:startedAtTime": {"@value": record.started_at, "@type": "xsd:dateTime"},
        "prov:endedAtTime": {"@value": record.ended_at, "@type": "xsd:dateTime"},
    }
    if record.extra is not None:
        jsonld["extra"] = dict(record.extra)

    solr_doc = SolrProvDoc(
        id=activity_id,
        prov_id=activity_id,
        prov_activityType=type_uri,
        prov_agent=record.agent,
        prov_used=used_sorted,
        prov_generated=generated_sorted,
        prov_startedAt=record.started_at,
        prov_endedAt=record.ended_at,
        prov_jsonld=json.dumps(jsonld, separators=(",", ":"), sort_keys=False),
    )
    return EmitResult(solr_doc=solr_doc, jsonld=jsonld)


def _validate(record: ProvRecord) -> None:
    if not record.activity_type:
        raise ValueError("emit: activity_type is required")
    if record.activity_type not in _ACTIVITY_TYPES:
        raise ValueError(
            f"emit: unknown activity_type '{record.activity_type}'; "
            f"expected one of {sorted(_ACTIVITY_TYPES)}"
        )
    if not record.agent:
        raise ValueError("emit: agent is required")
    if not isinstance(record.used, list):
        raise TypeError("emit: used must be a list")
    if not isinstance(record.generated, list):
        raise TypeError("emit: generated must be a list")
    if not _is_iso_instant(record.started_at):
        raise ValueError(
            f"emit: started_at must be ISO 8601 UTC (got {record.started_at!r})"
        )
    if not _is_iso_instant(record.ended_at):
        raise ValueError(
            f"emit: ended_at must be ISO 8601 UTC (got {record.ended_at!r})"
        )
    if _parse_iso(record.started_at) > _parse_iso(record.ended_at):
        raise ValueError("emit: started_at must be <= ended_at")


def _is_iso_instant(s: Any) -> bool:
    if not isinstance(s, str) or _ISO_INSTANT_RE.match(s) is None:
        return False
    try:
        _parse_iso(s)
        return True
    except ValueError:
        return False


def _parse_iso(s: str) -> datetime:
    # datetime.fromisoformat accepts Z from 3.11+; normalize for 3.10 compatibility.
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _derive_activity_id(record: ProvRecord, type_uri: str) -> str:
    identity = json.dumps(
        [
            type_uri,
            record.agent,
            sorted(record.used),
            sorted(record.generated),
            record.started_at,
            record.ended_at,
        ],
        separators=(",", ":"),
        sort_keys=False,
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    return f"{_ACTIVITY_URN_PREFIX}{digest}"
