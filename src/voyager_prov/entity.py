"""Deterministic PROV entity URIs.

Format: ``urn:voyager:prov:entity:<kind>:<id>``. See voyager-prov-ts's
entity.ts for the sibling implementation — this module is intentionally
identical in behavior so records written by either language deserialise into
the same PROV graph.
"""

from __future__ import annotations

import re

from .types import VOYAGER_URN_NS

_ENTITY_PREFIX = f"{VOYAGER_URN_NS}entity:"
_HOSTILE_CHARS = re.compile(r"[\s#?]")


def entity_uri(kind: str, id: str) -> str:
    """Return the URN for a PROV entity of ``kind`` with natural id ``id``."""
    if not kind:
        raise ValueError("entity_uri: kind is required")
    if not id:
        raise ValueError("entity_uri: id is required")
    if _HOSTILE_CHARS.search(kind) or _HOSTILE_CHARS.search(id):
        raise ValueError(
            "entity_uri: kind and id must not contain whitespace, '#', or '?'"
        )
    return f"{_ENTITY_PREFIX}{kind}:{id}"
