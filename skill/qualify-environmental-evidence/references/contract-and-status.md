# Contract And Status

## Inputs

The case JSON must conform to `schemas/claim-contract.schema.json` and use only IDs in the packaged registries. Pair validation requires both an assessment conforming to `schemas/assessment-output.schema.json` and a provenance manifest conforming to `schemas/provenance-manifest.schema.json`.

## Status Semantics

- `COMPLETED`: allowed only for a fully linked, complete contract result. This skill validates such artifacts but does not execute environmental processing or create a COMPLETED empirical result.
- `ABSTAINED` / `INCONCLUSIVE`: required information or evidence is unresolved, or all upstream checks pass and complete delta/tau measurements lie inside the inclusive primary operational indifference band. Null observations are allowed; internally valid PARTIAL observations remain audit-only.
- `REFUSED` / null disposition: the requested conclusion exceeds authority. Observations are null.
- `ERROR` / null disposition: deterministic validation or processing failed. Observations are null.

The machine-readable reason matrix is authoritative in `config/reason-codes.json`. It binds each reason to allowed statuses, dispositions, quality-check states, incompatibilities, and human review. `EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND` requires every upstream check to pass, complete finite delta/tau measurements, and the inclusive primary comparison. It cannot substitute for missing radiometry, low coverage, resource limits, or processing failure.

The EOP101132 package case remains specification-only and `runtime_ready=false` while human approval and the six Step 2 fields remain pending. The proposed 0.03 NDVI band is an operational PoC rule, not a detection limit or ecological, CER, audit, assurance, or market standard.
