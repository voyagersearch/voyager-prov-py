"""Minimal CLI for voyager-prov-py: read a ProvRecord JSON on stdin, print the
Solr doc, JSON-LD, or full result.

Installed as the ``voyager-prov`` console script by pyproject.toml.
"""

from __future__ import annotations

import json
import sys

from .emit import emit
from .types import ProvRecord

USAGE = """voyager-prov <emit|solr|jsonld>
  emit    — print { solrDoc, jsonld } (default)
  solr    — print only the Solr doc
  jsonld  — print only the JSON-LD blob

Reads a JSON ProvRecord from stdin. Field naming follows the Python API:
  activity_type, agent, used, generated, started_at, ended_at, extra?
"""


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "emit"
    if cmd not in ("emit", "solr", "jsonld"):
        sys.stderr.write(USAGE)
        return 2

    try:
        raw = json.load(sys.stdin)
    except json.JSONDecodeError as err:
        sys.stderr.write(f"voyager-prov: could not parse JSON on stdin: {err}\n")
        return 2

    try:
        record = ProvRecord(
            activity_type=raw["activity_type"],
            agent=raw["agent"],
            used=list(raw["used"]),
            generated=list(raw["generated"]),
            started_at=raw["started_at"],
            ended_at=raw["ended_at"],
            extra=raw.get("extra"),
        )
    except KeyError as err:
        sys.stderr.write(f"voyager-prov: missing required field {err}\n")
        return 2

    try:
        result = emit(record)
    except (ValueError, TypeError) as err:
        sys.stderr.write(f"voyager-prov: emit failed: {err}\n")
        return 1

    if cmd == "solr":
        sys.stdout.write(json.dumps(result.solr_doc.as_dict(), indent=2) + "\n")
    elif cmd == "jsonld":
        sys.stdout.write(json.dumps(result.jsonld, indent=2) + "\n")
    else:
        sys.stdout.write(
            json.dumps(
                {"solrDoc": result.solr_doc.as_dict(), "jsonld": result.jsonld},
                indent=2,
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
