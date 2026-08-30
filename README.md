# Qualify Environmental Evidence

Specification-first proof of concept for bounded, provenance-linked qualification of environmental observations. The repository constrains evidence identity, transformations, abstention behavior, and authority before any environmental statement can be emitted.

> **No licence has yet been selected. Private repository only. Public reuse permission has not been granted.**

## Current Status

| Area | Status |
|---|---|
| Contract and platform implementation | Contract `0.5.0` and the V4 runtime baseline are implemented and tested offline |
| First live source run | Completed and correctly abstained at the frozen V3 resource gate |
| Real raster and NDVI path | Implemented and tested with synthetic arrays; not yet executed against live V4 assets |
| Behavioural evaluation | Not yet executed |
| Green Agent orchestration | Not built |
| Public release | Not approved |

The immutable V3 live run used `DEMO_QUALIFICATION_POLICY_EOP101132_V3` and ended `ABSTAINED / INCONCLUSIVE / RESOURCE_LIMIT_EXCEEDED`. It did not produce coverage, NDVI, an environmental qualification result, or any causal, carbon, compliance, credit-quality, or financial conclusion.

V4 keeps the 40-acquisition raster-processing limit but applies it after deterministic metadata-only grouping and admissibility checks. Its live runtime is frozen separately so approval can bind the unchanged policy bytes, runtime semantics, and exact Git commit without a self-referential hash.

V4 policy SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`.

## Repository Layout

- `cases/`: bounded claim contracts.
- `config/`: evidence, transformation, reason-code, statement, and forbidden-inference registries.
- `policies/`: immutable historical policies and pending proposals.
- `schemas/`: JSON Schemas for contract artifacts.
- `scripts/`: deterministic validators, offline logic, packaging, and proposal generation.
- `tests/`: synthetic offline tests.
- `examples/`: reviewed derivatives safe for private baseline tracking.
- `skill/qualify-environmental-evidence/`: allowlisted packaged skill resources.

The complete live `runs/` directory remains local and ignored. Raw HTTP payloads, caches, raster assets, signed URLs, and credentials are not tracked.

## Reproducibility

Use Python 3.10 or later and `uv`:

```text
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/validate_step1_specs.py
uv run --offline --no-project --with "jsonschema>=4.18,<5" --with "pytest>=8,<9" --with "pyyaml>=6,<7" --with "numpy==2.5.2" --with "rasterio==1.5.1" python -m pytest -o addopts="" -p no:cacheprovider -q
uv run --offline --no-project python scripts/package_skill.py --check
uv run --offline --no-project python scripts/freeze_v4_runtime_spec.py --check
```

Regenerate the pending V4 proposal deterministically:

```text
uv run --offline --no-project python scripts/propose_v4.py --check
```

All V4 grouping tests use static synthetic metadata. They make no CER, STAC, EO, signing, raster, LLM, or model API request.

## Data Sources And Attribution

The contract identifies official Clean Energy Regulator project records and Microsoft Planetary Computer Sentinel-2 L2A metadata as allowed sources. Source identity in a policy or example is attribution and provenance, not affiliation, endorsement, partnership, regulatory approval, or scientific validation. Sentinel-2 data remains subject to its source terms. Raw source payloads require separate licensing and disclosure review before any public release.

## Limitations

- The only live run stopped before raster access.
- The V4 raster and replay implementation has synthetic coverage but remains unexecuted against live Sentinel-2 assets.
- A single bounded PoC cannot establish causality, carbon quantity, additionality, permanence, compliance, ACCU quality, project integrity, or financial suitability.
- V4 corrects an engineering unit of account; it does not invalidate V3 or imply that a future run will complete.

See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), [REPRODUCIBILITY.md](REPRODUCIBILITY.md), [DATA_SOURCES.md](DATA_SOURCES.md), and [PUBLIC_RELEASE_CHECKLIST.md](PUBLIC_RELEASE_CHECKLIST.md).
