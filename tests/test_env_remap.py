"""Env-driven DEFAULT_REMAP tests for voyager-prov-py.

DEFAULT_REMAP is resolved once at module import — flipping the env at
runtime doesn't move it. Each test sets ``PROV_REGISTER_MAP`` and forces
a fresh import of the module so the top-level load runs again.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest


def _fresh_import_and_resolve(monkeypatch: pytest.MonkeyPatch, env_value: str | None) -> str:
    """Import voyager_prov after clearing cached modules; return the URI
    ``activity_type_uri("chunk")`` resolves to under the given env."""
    if env_value is None:
        monkeypatch.delenv("PROV_REGISTER_MAP", raising=False)
    else:
        monkeypatch.setenv("PROV_REGISTER_MAP", env_value)
    # Drop cached submodules so the top-level `_load_remap_from_env()` re-runs.
    for name in list(sys.modules):
        if name == "voyager_prov" or name.startswith("voyager_prov."):
            del sys.modules[name]
    mod = importlib.import_module("voyager_prov")
    return str(mod.activity_type_uri("chunk"))


def test_unset_env_resolves_to_internal(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        _fresh_import_and_resolve(monkeypatch, None)
        == "https://voyager.ogc/prov/activity/chunk"
    )


def test_json_string_env_resolves_to_d110(monkeypatch: pytest.MonkeyPatch) -> None:
    env = json.dumps({"chunk": "https://d110.ogc.org/registers/prov-activity/chunk"})
    assert (
        _fresh_import_and_resolve(monkeypatch, env)
        == "https://d110.ogc.org/registers/prov-activity/chunk"
    )


def test_json_file_env_resolves_to_d110(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    remap_path = tmp_path / "d110.json"
    remap_path.write_text(
        json.dumps({"chunk": "https://d110.ogc.org/registers/prov-activity/chunk"}),
        encoding="utf-8",
    )
    assert (
        _fresh_import_and_resolve(monkeypatch, str(remap_path))
        == "https://d110.ogc.org/registers/prov-activity/chunk"
    )


def test_malformed_json_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        _fresh_import_and_resolve(monkeypatch, "{this-is-not-json")
        == "https://voyager.ogc/prov/activity/chunk"
    )


def test_missing_file_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        _fresh_import_and_resolve(monkeypatch, "/no/such/file/here.json")
        == "https://voyager.ogc/prov/activity/chunk"
    )


def test_emit_uses_default_remap(monkeypatch: pytest.MonkeyPatch) -> None:
    """`emit()` with no explicit remap arg picks up DEFAULT_REMAP."""
    env = json.dumps({"chunk": "https://d110.ogc.org/registers/prov-activity/chunk"})
    monkeypatch.setenv("PROV_REGISTER_MAP", env)
    for name in list(sys.modules):
        if name == "voyager_prov" or name.startswith("voyager_prov."):
            del sys.modules[name]
    mod: Any = importlib.import_module("voyager_prov")
    result = mod.emit(
        mod.ProvRecord(
            activity_type="chunk",
            agent="urn:voyager:agent:test",
            used=[mod.entity_uri("indexed-doc", "P1+enriched")],
            generated=[mod.entity_uri("chunk", "P1_0")],
            started_at="2026-08-25T12:00:00Z",
            ended_at="2026-08-25T12:00:01Z",
        )
    )
    assert (
        result.solr_doc.prov_activityType
        == "https://d110.ogc.org/registers/prov-activity/chunk"
    )
