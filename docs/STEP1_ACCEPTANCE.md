# Step 1 Acceptance Record

## Decision

Step 1 contract specification and Step 1.1 hardening are **accepted** for version 0.2.0. The accepted scope is deterministic validation of bounded claim contracts, assessments, provenance, source identity, status/reason semantics, and synthetic schema fixtures.

This acceptance does not cover network retrieval, CEA or Sentinel-2 processing, scientific-policy selection, pixel or NDVI calculation, empirical environmental results, ACCU validity, compliance, legal conclusions, or financial decisions.

## Requirement Traceability

| Requirement | Implementation evidence | Test evidence | Status |
| --- | --- | --- | --- |
| FR-01 bounded versioned claim | `schemas/claim-contract.schema.json`; `validate_case()` | case, pending-field, forbidden-inference tests | Accepted |
| FR-02 source allowlist and identity | `config/evidence-sources.json`; URI identity guards | unknown/duplicate source and URI-confusion tests | Accepted |
| FR-03 ordered transformation allowlist | `config/allowed-transformations.json`; manifest sequence checks | reorder/delete/duplicate and lineage tests | Accepted |
| FR-04 published CEA as AOI | case-bound `CER_PUBLISHED_CEA` identity and boundary fields | wrong-host/project/path tests | Contract accepted; artifact remains pending |
| FR-05 AOI coverage policy | assessment numeric invariants; pending case field | complete/partial/impossible-pixel tests | Contract accepted; calculation deferred |
| FR-06 frozen scientific rules | claim schema and `runtime_ready` gate | pending specification-mode tests | Contract accepted; rules remain pending |
| FR-07 bounded summaries | assessment schema, registered templates, authority ceiling | observation and statement-render tests | Contract accepted; no empirical summary produced |
| FR-08 status/disposition separation | assessment schema and observation-state policy | COMPLETED/ABSTAINED/REFUSED/ERROR fixtures | Accepted |
| FR-09 authority ceiling | forbidden registry and refusal semantics | authority reason/status tests | Accepted |
| FR-10 stable reason codes | `config/reason-codes.json` semantics matrix | ordering, contradiction, and quality-state tests | Accepted |
| FR-11 complete provenance | provenance schema and `validate_linked_result()` | empty-source, skipped-stage, linkage, and hash tests | Accepted |
| FR-12 canonical reproducibility | strict JSON loader and canonical byte/hash functions | independent golden vectors and tamper test | Accepted |

All Step 1 quantitative targets S1-QT-01 through S1-QT-08 are represented by the validator and regression suite. Scientific execution targets remain later-PoC work.

## Audit Findings

| Finding | Disposition | Evidence |
| --- | --- | --- |
| A1 non-finite JSON and circular hash oracle | Fixed | strict `parse_constant`, recursive finite checks, `allow_nan=False`, static fixture digests, independent Unicode/type-sensitive golden vectors |
| A2 attacker-controlled evidence URI | Fixed | per-source exact scheme/host/path/project/collection policy; separate temporary `retrieval_uri`; signed canonical parameters rejected |
| A3 invariants only in COMPLETED | Fixed | every non-null observation is checked; ABSTAINED permits valid PARTIAL only; REFUSED/ERROR require null |
| A4 semantically false hashed statement | Fixed | project, windows, policy, values, template, comparison, disposition, render, case, and hash are linked |
| A5 misleading manifest validator | Fixed | narrow helper renamed `validate_manifest_structure()`; authoritative `validate_linked_result()` requires all contexts and complete provenance |
| A6 descriptive reason defaults | Fixed | machine-readable status/disposition/quality/incompatibility/review matrix enforced |
| A7 drifting README JSON | Fixed | both designated JSON examples are deterministically extracted and validated in tests |
| A8 vacuous negative tests | Fixed | schema-valid wrong values and targeted guard messages replace broad or min-length-only failures |

## Verification

Executed from the repository root on 2026-08-29:

```text
uv run --no-project --with 'jsonschema>=4.18,<5' python scripts/validate_step1_specs.py
```

Result: exit 0; `Step 1 contracts valid (version 0.2.0; fixtures: COMPLETED, ABSTAINED, REFUSED, ERROR).` The validator also reported the exact six pending Step 2 fields.

```text
uv run --no-project --with 'jsonschema>=4.18,<5' --with 'pytest>=8,<9' python -m pytest -o addopts='' -q
```

Result: exit 0; `110 passed in 0.74s`.

The repository-required `python -m pytest -q` form was also run through the same `uv` environment and completed at 100% with exit 0.

Versions: contract/schema/validator 0.2.0; Python 3.14.7; jsonschema 4.26.0; pytest 8.4.2; uv 0.12.5.

## Deliberately Pending

- `BOUNDARY_FILE_AND_CHECKSUM`
- `PRE_WINDOW`
- `POST_WINDOW`
- `SEASONAL_MATCHING_RULE`
- `SCL_VALIDITY_RULE`
- `OBSERVATION_COVERAGE_POLICY`

## Residual Risks

The fixtures prove contract behavior, not ecological or remote-sensing accuracy. `CANONICAL_JSON_V1` intentionally preserves the existing distinction between `1` and `1.0` and is not RFC 8785/JCS. Publisher URI policies will require controlled updates if authoritative endpoints change. These are explicit boundaries, not Step 1 acceptance blockers.
