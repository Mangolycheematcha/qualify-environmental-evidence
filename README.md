# qualify-environmental-evidence

**Evidence before inference.**

A reproducible proof of concept for qualifying—not validating—public
registry and Earth-observation evidence before use in regulated
financial workflows.

> **Original, owner-controlled repository material is licensed under Apache-2.0. Third-party data, metadata, source responses, derived artifacts, dependencies, services, and marks remain under their applicable terms and are not relicensed. The repository remains private pending release approval.**

## Project Status

| Area | Status |
|---|---|
| Step 1 contract and skill packaging | Contract `0.5.0`; schemas, registries, validator, and packaged skill implemented and tested |
| Step 2B real EO vertical slice | Completed for EOP101132 under frozen V4 policy and Approval Protocol V2 |
| Real raster and NDVI path | Executed against permitted live V4 assets and reproduced from cached inputs |
| Scientific result | Retained: `ABSTAINED / INCONCLUSIVE / EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND` |
| Cached replay | Assessment bytes, array hashes, grouping, composites, and joint mask reproduced |
| Canonical/governance status | Governance limitations documented; not claimed as fully canonical |
| CER qualification corpus | Seven real ACCU projects across six method types plus one real 2024-25 Safeguard facility-period row |
| Step 3 deterministic evaluation | 80/80 engineering rows across 22 semantic groups; 27 held out by group, template, subject and target evidence; four E2E journeys |
| Retrieval, security and performance | controlled 25-query Top-1: lexical 22, TF-IDF 22, hybrid 23; 7 executed security cases plus 3 explicit N/A surfaces; reproducible p50/p95 samples |
| Step 3 model/API evaluation | Adapter and matched B0/B1/T1 design implemented; 0/27 live cases per arm because no credential is configured |
| Independent human evaluation | H1 0/27; blocked pending independent annotation; repository expectations are not human gold |
| Public release and hosting | Prepared documentation and offline package only; no push, release, visibility change, API service, or deployment |

The current Step 2B closure is `SCIENCE_VALID — GOVERNANCE_LIMITATION — NO_RERUN`.

## In 30 Seconds

- The PoC binds a narrow evidence question to allowlisted sources, frozen transformations, reason codes, and explicit abstention behavior.
- It executed one real Sentinel-2 vertical slice and retained the resulting bounded scientific assessment.
- It reproduced that assessment from cached arrays without network access.
- It records two governance limitations: an erroneous diagnostic-only area value and incomplete request-level visibility into GDAL HTTP range requests and retries.
- It does not validate carbon credits, prove environmental causality, provide assurance, or make an investment decision.

## What It Does

- Validates versioned claim contracts, schemas, registries, and provenance relationships.
- Resolves metadata-only acquisition groups before raster processing.
- Computes a bounded PRE/POST Sentinel-2 NDVI comparison under a frozen policy.
- Emits structured status, disposition, reason codes, hashes, and human-review requirements.
- Preserves one-time approval consumption and cached deterministic replay evidence.
- Runs an offline evidence-memory and qualification workflow over source-attributed CER facts and the frozen Step 2B summary.
- Enforces the distinction between ACCUs and SMCs before any quality, equivalence, compliance, trading, or financial inference.

## What It Does Not Do

- It does not validate ACCUs, carbon-credit quality, project integrity, or regulatory compliance.
- It does not establish causality, carbon quantity, additionality, permanence, or scientific truth.
- It does not provide audit assurance, regulatory approval, lending, trading, or investment advice.
- It is not a production-ready agent or a general benchmark of environmental claims.

## Safe Reproduction

The shortest supported entry point is offline contract validation:

```text
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/validate_step1_specs.py
```

The end-to-end offline qualification demo is:

```text
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/qualification_workflow.py examples/qualification/eop101132-request.json --json
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/evaluate_qualification.py --json
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/run_e2e_demos.py --json
```

The complete offline suite is:

```text
uv run --offline --no-project --with "jsonschema>=4.18,<5" --with "pytest>=8,<9" --with "pyyaml>=6,<7" --with "numpy==2.5.2" --with "rasterio==1.5.1" python -m pytest -o addopts="" -p no:cacheprovider -q
uv run --offline --no-project python scripts/package_skill.py --check
uv run --offline --no-project python scripts/freeze_v4_runtime_spec.py --check
```

| Path | Network/approval boundary |
|---|---|
| Commands above | `OFFLINE-ONLY`; use repository fixtures and do not consume approval |
| Cached replay verification | `OFFLINE-ONLY`; the completed private run package is immutable, so do not invoke the replay writer against it |
| Live EO runtime | `LIVE/NETWORK` and `APPROVAL-CONSUMING`; intentionally not presented as a quick start |
| Step 3 deterministic evaluation | `OFFLINE-ONLY`; no model or external API is used |
| Step 3 model/API evaluation | Adapter implemented; no call executed; requires explicit authorization, credential and selected model |

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the full command boundary.

## Step 2B Result

The retained run is `EOP101132-STEP2B-V4-20260901T081607339902Z-703540348beaee0f`, executed at commit `9e1fabbf005dd29fba09aa82ea18046e99556e02` with:

- policy SHA-256 `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`;
- runtime-spec SHA-256 `e7671981e1edbe9b17d2198d68bd873750c40c9489923c403790c34ae9059b51`;
- PRE median NDVI `0.6630660903670323`;
- POST median NDVI `0.6432938994009436`;
- POST-minus-PRE delta `-0.0197721909660887`;
- joint coverage `0.9997194163860831`;
- frozen primary tau `0.03`.

Under the frozen primary policy, the result is `ABSTAINED / INCONCLUSIVE` because the observation falls within the operational indifference band. This is a qualification outcome, not a scientific detection threshold.

Offline replay reproduced the assessment bytes and array hashes. The run is not claimed as fully canonical under Approval Protocol V2 because one diagnostic area field was erroneous and GDAL internal HTTP range requests and retries were not fully represented in request-level transport provenance.

Read the [Step 2B closure and impact audit](docs/STEP2B_V4_CLOSURE.md), its [provenance and replay record](docs/STEP2B_V4_CLOSURE.md#provenance-and-replay), and the documented [governance limitations](docs/STEP2B_V4_CLOSURE.md#governance-limitations). Earlier run history remains available in the [historical V4 audit](docs/STEP2B_V4_THIRD_APPROVED_RUN_AUDIT.md) and [approval-binding incident](docs/incidents/STEP2B_V4_APPROVAL_BINDING_FAILURE.md).

The [qualification workflow](docs/QUALIFICATION_WORKFLOW.md) now provides deterministic retrieval and bounded memo generation over curated CER public facts and the frozen summary. The [Step 3 evaluation](docs/STEP3_EVALUATION.md) reports exactly what has and has not been tested; [deployment guidance](docs/DEPLOYMENT.md) describes the supported offline package and future service gates.

## Repository Layout

- `cases/`: bounded claim contracts.
- `config/`: evidence, transformation, reason-code, statement, and forbidden-inference registries.
- `policies/`: immutable historical policies and proposals.
- `schemas/`: JSON Schemas for contract artifacts.
- `scripts/`: deterministic validators, offline logic, packaging, and controlled runtime code.
- `tests/`: synthetic offline tests.
- `examples/`: reviewed derivatives; not complete run packages.
- `data/cer/`: curated, source-attributed CER public fact snapshots; not raw pages or complete exports.
- `evaluation/`: versioned offline qualification benchmark.
- `skill/qualify-environmental-evidence/`: allowlisted packaged skill resources.

Complete live `runs/` directories remain local and ignored. Raw HTTP payloads, caches, raster assets, signed URLs, and credentials are not tracked.

## Data, Licensing, And Citation

The contract identifies official Clean Energy Regulator records and Microsoft Planetary Computer Sentinel-2 L2A metadata as allowed sources. Source identity is attribution and provenance, not affiliation, endorsement, partnership, regulatory approval, or scientific validation.

Original code and other owner-controlled repository material are licensed under [Apache-2.0](LICENSE). That licence does not relicense CER material, Sentinel-2 or Planetary Computer data and metadata, raw network responses, derived or cached artifacts, third-party dependencies, services, or marks. See the [licence scope inventory](docs/DATA_AND_ARTIFACT_LICENSING.md), [third-party notices](THIRD_PARTY_NOTICES.md), [NOTICE](NOTICE), and [CITATION.cff](CITATION.cff).

## Limitations

- The result is one bounded observational comparison and does not generalise beyond its frozen claim, AOI, windows, sources, and policy.
- The incorrect projected-area value in `target-grid.json` is diagnostic-only. Bounds, transform, shape, AOI mask, coverage, arrays, composites, NDVI, disposition, and sensitivity did not read that value and were independently reproduced.
- Request-level provenance does not enumerate GDAL's internal HTTP range requests, and the GDAL retry configuration cannot be claimed as compliant with the frozen logical `0/2/5` retry semantics.
- Cached array-level replay proves deterministic reconstruction from retained inputs; it does not prove complete original COG transport-byte provenance.
- CER snapshots are time-stamped curated facts, not a live API or continuously refreshed register mirror.
- Evidence memory is local and content-addressed; it is not user memory, a vector database, or a claim of semantic completeness.
- The Step 3 unsupported-assertion metric evaluates the deterministic rule system only, not an LLM hallucination rate.
- The 80 rows are repository-authored deterministic regression cases across 22 semantic groups, not 80 independent substantive scenarios, expert labels, or comparative model evidence.
- The 25 retrieval queries are a small repository-authored controlled set with structured subject filters, not independent human queries; the hybrid Top-1 gain was 1/25.
- A single PoC cannot establish causality, carbon quantity, additionality, permanence, compliance, ACCU quality, project integrity, or financial suitability.
- Step 3 B0/B1/T1 live model evaluation and H1 independent annotation have not run. Multi-project deterministic evaluation has run; hosting has not.

See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), [DATA_SOURCES.md](DATA_SOURCES.md), and [PUBLIC_RELEASE_CHECKLIST.md](PUBLIC_RELEASE_CHECKLIST.md).
