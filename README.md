# qualify-environmental-evidence

A reproducible proof of concept for qualifying — not validating — public environmental evidence before it enters regulated financial workflows.

The repository constrains evidence identity, transformations, abstention behavior, and authority before any environmental statement can be emitted.

> **No licence has yet been selected. Private repository only. Public reuse permission has not been granted.**

## Current Status

| Area | Status |
|---|---|
| Contract and platform implementation | Contract `0.5.0` and frozen V4 runtime `1.0.2` are implemented and tested |
| Live source runs | V3 and three approved V4 runs are preserved locally; the third V4 run completed the frozen Step 2B path |
| Real raster and NDVI path | Executed against permitted live V4 assets and reproduced from cached inputs |
| Step 2B qualification | `ABSTAINED / INCONCLUSIVE / EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND` |
| Step 3 | Not executed and not approved |
| Green Agent orchestration | Not built |
| Public release | Not approved |

The immutable V3 live run used `DEMO_QUALIFICATION_POLICY_EOP101132_V3` and ended `ABSTAINED / INCONCLUSIVE / RESOURCE_LIMIT_EXCEEDED`. The first approved V4 run ended `ERROR / SOURCE_UNAVAILABLE` on a metadata transport timeout. The second approved V4 run, `EOP101132-STEP2B-V4-20260830T041242319779Z-24e3f17288b106b7`, ended `ERROR / DETERMINISTIC_PROCESSING_ERROR` when a raw `TimeoutError` escaped the frozen retry wrapper.

The third approved V4 run, `EOP101132-STEP2B-V4-20260830T044223516364Z-73144a299e2d5763`, completed the frozen Step 2B workflow at authorised execution commit `bf0b1a33230ff2d6e259aab2cca087bc8c21dbbf`. It read permitted raster pixels, computed a pre-window NDVI median of `0.6630660903670323`, a post-window median of `0.6432938994009436`, and delta NDVI of `-0.0197721909660887`. The primary policy therefore abstained as `INCONCLUSIVE` because the bounded observation fell within the operational indifference band. Offline replay reproduced the canonical assessment hash. Step 3 was not executed.

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

Automated tests use static synthetic metadata and make no CER, STAC, EO, signing, raster, LLM, or model API request. Live run artifacts remain local and ignored.

## Data Sources And Attribution

The contract identifies official Clean Energy Regulator project records and Microsoft Planetary Computer Sentinel-2 L2A metadata as allowed sources. Source identity in a policy or example is attribution and provenance, not affiliation, endorsement, partnership, regulatory approval, or scientific validation. Sentinel-2 data remains subject to its source terms. Raw source payloads require separate licensing and disclosure review before any public release.

## Limitations

- The third V4 result is one bounded observational comparison; it does not generalise beyond the frozen claim, AOI, windows, sources, and policy.
- A single bounded PoC cannot establish causality, carbon quantity, additionality, permanence, compliance, ACCU quality, project integrity, or financial suitability.
- V4 corrects an engineering unit of account; it does not invalidate V3 or retrospectively alter either failed V4 run.

See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), [REPRODUCIBILITY.md](REPRODUCIBILITY.md), [DATA_SOURCES.md](DATA_SOURCES.md), and [PUBLIC_RELEASE_CHECKLIST.md](PUBLIC_RELEASE_CHECKLIST.md).
