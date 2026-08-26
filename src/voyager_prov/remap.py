"""Voyager-internal → D110 register URI remap.

Mirrors voyager-prov-ts's remap.ts. Callers get D110 URIs at emit time by
setting ``PROV_REGISTER_MAP`` in the environment before the package is
imported — no code change on any emission site.

``PROV_REGISTER_MAP`` can point to either:

- a local JSON file whose contents are a mapping (usual container case), or
- a JSON string (``PROV_REGISTER_MAP='{"chunk":"..."}'`` — handy for tests).

Missing / unreadable / malformed → falls back silently to the internal
namespace. Emission MUST NOT fail because a register can't be loaded.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, cast

from .types import VOYAGER_ACTIVITY_NS, ActivityType

logger = logging.getLogger(__name__)

REGISTER_ENV_VAR = "PROV_REGISTER_MAP"

EMPTY_REMAP: Mapping[ActivityType, str] = MappingProxyType({})


def _load_remap_from_env() -> Mapping[ActivityType, str]:
    raw = os.environ.get(REGISTER_ENV_VAR, "").strip()
    if not raw:
        return EMPTY_REMAP
    text: str | None
    if raw.startswith("{"):
        text = raw
    else:
        try:
            path = Path(raw)
            if not path.exists():
                return EMPTY_REMAP
            text = path.read_text(encoding="utf-8")
        except OSError:
            return EMPTY_REMAP
    try:
        parsed: Any = json.loads(text)
        if isinstance(parsed, dict):
            return MappingProxyType(cast(dict[ActivityType, str], parsed))
    except json.JSONDecodeError as e:
        logger.error(
            "[voyager-prov] failed to parse %s (%s); falling back to internal namespace.",
            REGISTER_ENV_VAR,
            e,
        )
    return EMPTY_REMAP


# Resolved once at module import — flipping the register at runtime means
# restarting the process, which is the deploy contract we want anyway
# (the same records shouldn't switch namespaces mid-run and produce two
# different activity URNs for the same emission).
DEFAULT_REMAP: Mapping[ActivityType, str] = _load_remap_from_env()


def activity_type_uri(
    activity_type: ActivityType,
    remap: Mapping[ActivityType, str] | None = None,
) -> str:
    """Return the D110 register URI if mapped, else the Voyager-internal URI.

    When called without an explicit ``remap``, uses whatever ``DEFAULT_REMAP``
    resolved to at import time (env-driven). Pass a ``remap`` explicitly to
    override — useful for tests or for a caller that keeps both URIs around.
    """
    source = remap if remap is not None else DEFAULT_REMAP
    if activity_type in source:
        return source[activity_type]
    return f"{VOYAGER_ACTIVITY_NS}{activity_type}"
