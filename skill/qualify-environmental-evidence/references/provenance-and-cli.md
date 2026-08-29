# Provenance And CLI

## CLI

```text
python scripts/qualify.py CASE.json [--assessment ASSESSMENT.json --manifest MANIFEST.json] [--json]
python scripts/qualify.py --check-resources [--json]
```

Paths may be absolute or relative to the caller. Packaged schemas, registries, and code resolve from the installed skill root, not the working directory. `--json` writes one compact JSON object to stdout; diagnostics go to stderr.

Exit codes:

| Code | Meaning |
| ---: | --- |
| 0 | Valid contract/specification, valid linked artifacts, or valid resource check |
| 2 | Invalid contract or broken linkage |
| 3 | Controlled authority refusal |
| 4 | Packaged resource integrity failure |
| 5 | Unexpected internal error |

The script requires Python 3.10+ and `jsonschema>=4.18,<5`. It makes no network calls.

## Audit Trail

Record input and artifact identities, canonical source identities, per-item/per-band radiometry metadata, primary and sensitivity qualification records, transformation IDs and sequence, parameter references and hashes, policy versions, rule IDs, statuses, reason codes, timestamps, and content hashes. Retrieval URIs remain separate from canonical identities and credential-bearing query strings must not be persisted. Do not request or store hidden reasoning or chain-of-thought.

A terminal COMPLETED contract requires every case source, all registered transformations in order, complete parameter and artifact lineage, and exact case/run/status/reason/hash linkage. Contract validation never proves ecological truth, ACCU integrity, compliance, or financial suitability.
