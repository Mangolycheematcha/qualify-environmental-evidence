# Reproducibility

## Environment

- Python 3.10 or later for contract validation.
- Python 3.12 or later with the pinned `numpy` and `rasterio` versions for V4 runtime-related tests.
- Dependencies are declared in `pyproject.toml` and resolved in `uv.lock`.

## Offline Validation

These commands use repository fixtures and do not access CER, STAC, signing, raster, LLM, or model APIs. `uv --offline` requires the packages to exist in the local cache.

```text
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/validate_step1_specs.py
uv run --offline --no-project --with "jsonschema>=4.18,<5" python skill/qualify-environmental-evidence/scripts/qualify.py --check-resources --json
uv run --offline --no-project --with "jsonschema>=4.18,<5" --with "pytest>=8,<9" --with "pyyaml>=6,<7" --with "numpy==2.5.2" --with "rasterio==1.5.1" python -m pytest -o addopts="" -p no:cacheprovider -q
uv run --offline --no-project python scripts/package_skill.py --check
uv run --offline --no-project python scripts/freeze_v4_runtime_spec.py --check
uv run --offline --no-project python scripts/propose_v4.py --check
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/qualification_workflow.py examples/qualification/eop101132-request.json --json
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/evaluate_qualification.py --json
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/build_corpus_manifest.py --check
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/build_evaluation_corpus.py --check
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/build_retrieval_benchmark.py --check
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/evaluate_retrieval.py --json
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/run_e2e_demos.py --json
uv run --offline --no-project --with "jsonschema>=4.18,<5" python scripts/evaluate_security.py --json
```

An existing virtual environment with the declared dependencies may run the equivalent commands with `python` directly.

## Cached Replay Boundary

The retained Step 2B V4 run completed cached replay with network access disabled. Its live and replay assessment bytes and hashes match. Complete run packages remain local under ignored `runs/` because they contain raw responses, metadata blobs, and cached raster-derived arrays that require separate licensing and disclosure review.

Completed run packages are immutable. Do not invoke a replay writer or runtime stage against them as an ordinary reproduction command. Read-only hash and checksum verification is appropriate; a new live execution is not required for the retained scientific result.

See `docs/STEP2B_V4_CLOSURE.md` for the exact run identity, hashes, reproduced quantities, and governance limitation.

## Controlled Live Runtime

The live runtime accesses CER, STAC, signing, metadata, and raster sources and consumes a one-time Approval Protocol request. It is intentionally excluded from the quick start. Prompt text, a CI run, or repository access does not constitute approval.

Any future runtime code, policy, or runtime-spec change requires a new commit, frozen hashes, approval request, and independent human approval. The live/model/API portion of Step 3 has not started and has no supported execution command; the separate deterministic offline workflow is documented below.

## Offline Qualification And Evaluation

The qualification workflow reads ten local, schema-validated evidence documents: seven curated ACCU project records, one Safeguard facility-period extract, one ACCU/SMC definition document, and one frozen observational derivative. It builds a content-addressed memory snapshot, retrieves facts deterministically, applies authority and evidence gates, and emits a canonical result hash. The evaluator executes 80 repository-authored regression rows across 22 semantic groups twice per row, including 53 development and 27 partition-held-out rows. The qualification and deterministic evaluation paths do not access an external service.

This is the implemented deterministic, multi-project portion of Step 3. The 25-query retrieval comparison, four E2E journeys, local security controls, and performance samples are implemented. B0/B1/T1 live model/API evaluation, H1 independent human labelling, a stable live CER API integration, public hosting, and deployment remain unexecuted. See `docs/STEP3_EVALUATION.md`.

## Historical Integrity

Historical policy and run hashes are pinned by tests and audit records. The redacted derivative under `examples/` is not a substitute for a complete evidence package and must not be used to infer a later run's approval or provenance.
