# voyager-prov-py

PROV emission middleware for Voyager workflows — the Python half of the
**D100 Workflow Profiler** deliverable for OGC OSPD 2026. Companion to
[voyager-prov-ts](../voyager-prov-ts).

Given a description of one activity in the Voyager RAG pipeline
(ingest → extract → chunk → embed → retrieve → generate), `emit()` returns
two artifacts:

- A **Solr doc** ready to index into the shared `main` collection.
- A **PROV-JSON-LD** blob conformant with W3C PROV (subset).

Both implementations produce the **same activity URN** for the same input, so
records written by either side deserialise into the same graph.

## Install

```bash
pip install voyager-prov-py
```

## Usage

```python
from voyager_prov import ProvRecord, emit, entity_uri

parent_id = "AS_2226000_2026_178"

result = emit(ProvRecord(
    activity_type="chunk",
    agent="urn:voyager:agent:mastra-chunker@1.0.0",
    used=[entity_uri("extracted-content", parent_id)],
    generated=[
        entity_uri("chunk", f"{parent_id}_0"),
        entity_uri("chunk", f"{parent_id}_1"),
    ],
    started_at="2026-08-24T12:00:00Z",
    ended_at="2026-08-24T12:00:01Z",
))

# result.solr_doc — dataclass, ready for Solr indexing
# result.jsonld    — dict, the PROV-JSON-LD graph representation
```

## D110 register remap

Until D110's process-type register hardens, `emit()` writes
`https://voyager.ogc/prov/activity/<type>` as the `activityType` URI. Pass a
remap at emit time to swap in D110 URIs:

```python
from voyager_prov import EmitOptions, emit

D110 = {
    "chunk": "https://d110.ogc.org/registers/prov-activity/chunk",
    "embed": "https://d110.ogc.org/registers/prov-activity/embed",
}

emit(record, EmitOptions(remap=D110))
```

Missing entries fall back to the Voyager-internal URI.

## CLI

```bash
voyager-prov emit    < record.json     # print { solrDoc, jsonld }
voyager-prov solr    < record.json     # print only the Solr doc
voyager-prov jsonld  < record.json     # print only the JSON-LD blob
```

Field naming on stdin follows the Python API: `activity_type`, `agent`,
`used`, `generated`, `started_at`, `ended_at`, `extra?`.

## Solr schema

Same as voyager-prov-ts — see the [ts README](../voyager-prov-ts/README.md#solr-schema).

## Testing

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q       # 20 unit tests, including cross-language URN parity
.venv/bin/mypy src        # strict mode
```

## Cross-language parity

The `test_activity_id_matches_ts_reference_for_known_input` test in
`tests/test_emit.py` locks the expected activity URN for a canonical input.
The Node.js CLI produces the same URN — any drift between the two suites
means one implementation has diverged and needs a fix, not a schema tweak.

## License

Same as the parent Voyager platform.
