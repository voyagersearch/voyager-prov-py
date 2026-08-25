"""Voyager-internal → D110 register URI remap.

Mirrors voyager-prov-ts's remap.ts. Empty by default; callers pass a mapping
at emit time once D110's register URIs are known.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .types import VOYAGER_ACTIVITY_NS, ActivityType

EMPTY_REMAP: Mapping[ActivityType, str] = MappingProxyType({})


def activity_type_uri(
    activity_type: ActivityType,
    remap: Mapping[ActivityType, str] | None = None,
) -> str:
    """Return the D110 register URI if mapped, else the Voyager-internal URI."""
    if remap is not None and activity_type in remap:
        return remap[activity_type]
    return f"{VOYAGER_ACTIVITY_NS}{activity_type}"
