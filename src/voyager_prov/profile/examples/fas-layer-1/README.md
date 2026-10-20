# FAS Layer 1 — declarative provenance examples

The Voyager RAG pipeline (Layer 2, instrumented at runtime by
[voyager-prov-ts](../../..)) ingests the USDA FAS catalog through a Solr
connector. The FAS catalog itself is a **pre-built** artifact — before we
touched it, FAS ran a chain of geospatial + text ops (Download, OCR,
GeoTagging, Commodity Classification, Region Classification, NLP entity
extraction, Field Normalization) to assemble each product's records.

For CFP §5.1 alignment we need the D100 profile to describe those Layer 1
ops even though we didn't run them. This directory holds **declarative
PROV assertions** — one JSON-LD file per FAS product — that record the
semantic upstream ops as `prov:Activity` records chained via
`used`/`generated`, plus a `connectorSteps` list documenting the actual
per-step chain inside the FAS custom Python connector. All files cite
the [Voyager Search Overview for USDA FAS](https://docs.google.com/presentation/d/1IybpPfUqDYji0ge-X0n165gMV8pU2UqlZQFKxIykk5k)
deck (slides 20–29) as `prov:hadPrimarySource` evidence. Each file also
records the actual data-source URL and external dependencies invoked by
the connector.

## Files (14 FAS product types + 2 legacy assertions)

Reports & Briefs family (mostly text with OCR):

- `wap.jsonld` — World Agricultural Production (5-op: NLP → GeoTag → Commodity Classify → OCR → Field Normalize)
- `wwcb.jsonld` — Weekly Weather and Crop Bulletins (4-op)
- `cir.jsonld` — Commodity Intelligence Reports (5-op)
- `gain.jsonld` — GAIN via live newgain OAuth API (4-op, no OCR)
- `gain-legacy.jsonld` — GAIN via legacy CSV (2-op: GeoTag + Field Normalize)

PSD Online family (structured numerical):

- `psd-online.jsonld` — PSD Online per-commodity/per-country/per-year rows (3-op: GeoTag + Commodity Classify + Field Normalize)
- `psd-publications.jsonld` — Monthly commodity circulars (2-op)

Photo & map family (geospatial):

- `photo-gallery.jsonld` — PSD Photo Gallery (OCR + GeoTag + Commodity + Field Normalize)
- `crop-calendar.jsonld` — Crop Calendar (GeoTag + Commodity + OCR + Field Normalize)
- `production-maps.jsonld` — Production Maps (adds Region Classification)
- `monitor-maps.jsonld` — Cyclone + Flood Monitor Maps (4-op — GeoTag + Region + OCR + Field Normalize)
- `crop-explorer.jsonld` — Crop Explorer weather / vegetation maps (3-op — GeoTag + Region + Field Normalize)
- `commodity-explorer.jsonld` — Country × commodity × rank explorer (4-op — GeoTag + Commodity + Region + Field Normalize)
- `mage.jsonld` — Mobile Awareness GEOINT Environment crop-tour observations (3-op — GeoTag + Region + Field Normalize)

Legacy / declared without connector code available in-repo:

- `gadas-services.jsonld` — GADAS Services (GeoTag + Region Classify via ArcGIS)
- `kcna-cifs.jsonld` — KCNA CIFS Geospatial (GeoTag + Region Classify via folder connector)

## File shape

Each file is a top-level envelope:

```jsonc
{
  "@context": { "prov": "...", "xsd": "...", "voyager": "..." },
  "fasSource": "psd-online",
  "fasSourceName": "PSD Online / Publications",
  "hadPrimarySource": { "@id": "<FAS deck URL>", "deckSlides": "24" },
  "sourceUrl": "https://api.fas.usda.gov/api/psd/commodity/{code}/country/all/year/{year}",
  "externalDeps": ["USDA PSD API", "Voyager placefinder Solr"],
  "connectorSteps": [
    "C1 HTTP GET commodities list",
    "C2 HTTP GET per-commodity/per-year rows",
    "C3 delta-check via Solr fi_release_year desc",
    "..."
  ],
  "activities": [ /* semantic Layer 1 activity chain — see below */ ]
}
```

`activities` is a proper causal **chain** (not a fan): each activity's
`used` is the previous activity's `generated`. Intermediate entity URIs
are `urn:voyager:prov:entity:fas-catalog:{source}+{stage}` and the
terminal `generated` is the bare `urn:voyager:prov:entity:fas-catalog:{source}`
representing the final ingested catalog record. The head activity's
`used` is `urn:voyager:prov:entity:fas-source-raw:{source}`.

## Notes

- **Semantic vs. connector layers.** The `activities` array captures the
  CFP §5.1-aligned semantic ops (geotag, classify-commodity, ocr, etc.).
  The `connectorSteps` array records the actual per-step chain inside
  the FAS custom Python connector (download, HTML scrape, OCR job, geo
  enrichment, taxonomy assignment, etc.). Both are declarative — Layer 1
  ran upstream, we're documenting it not observing it.
- **Deterministic Activity URIs.** Each `@id` is
  `urn:voyager:prov:activity:<32-hex sha256 slice>`, computed over the
  identity tuple `[typeURI, agent, sortedUsed, sortedGenerated, startedAt, endedAt]`.
  Layer 1 assertions are stable per FAS source, not per-doc — regenerate
  by running `gen_fas_layer1_jsonld.py` if the semantic chain or metadata
  changes.
- **Agent URIs.** `urn:voyager:agent:fas-upstream:<source>.<step>` — the
  `fas-upstream` segment marks them as declared. Distinct agent URIs per
  source × step so two different FAS products' geotag activities don't
  collide.
- **Timestamps.** `startedAtTime`/`endedAtTime` are the Voyager deck's
  citation date, not the actual op time (which is unknown at FAS).
- **Schema.** These files validate against the same
  [`prov-jsonld.schema.json`](../../prov-jsonld.schema.json) as runtime
  emissions.
- **Source code.** The FAS Python connectors themselves live in a
  Google Drive folder (not in this repo). Each connector's `sourceUrl` +
  `connectorSteps` on the assertion is derived from that code.
