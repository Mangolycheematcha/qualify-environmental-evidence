# Step 2B Contract Candidate 0.3.0

Status: **IMPLEMENTED AND TESTED OFFLINE; PENDING HUMAN APPROVAL**

This is a forward contract extension. It does not rewrite or retroactively expand the accepted Step 1 `0.2.0` record.

## Contract changes

- Added the primary `POC_OPERATIONAL_INDIFFERENCE_BAND_V1` with inclusive `tau=0.03` and secondary sensitivity values `0.01`, `0.02`, and `0.05`.
- Added a machine-enforced complete-measurement abstention for `EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND`.
- Added fail-closed `RADIOMETRY_METADATA_UNRESOLVED` and `RESOURCE_LIMIT_EXCEEDED` reasons.
- Added item- and band-specific radiometry records and primary/sensitivity qualification records to runtime provenance.
- Added delta, tau, descriptive distribution, and sensitivity fields to assessment observations.
- Added active V2 completed-statement templates while retaining V1 template identities as historical registry entries.
- Narrowed and machine-bound the EOP101132 claim to the CEA, exact windows, aggregation, joint pixel population, metric, tau, and policy version.
- Added a pure offline contract module. It contains no STAC client, signing code, raster reader, or network dependency.
- Increased the packaged authoritative resource allowlist from 10 to 12 files to include the pending policy proposal and offline module.

## Policy identity

- Previous proposal SHA-256: `e2e174ea34de8855429c3134c4063475063d55f2ae5157a2ed042f53cfa67c39`
- Revised policy: `DEMO_QUALIFICATION_POLICY_EOP101132_V2`
- Revised proposal SHA-256: `014336ca3aa4db16f1e7b26123c75c1e47013d2463381a5dae0379392e994dac`

## Boundary reconciliation

The analysis boundary is the frozen CER CEA, SHA-256 `3761b2c8b004308db31e06236bb40f2b00c2e0590ec7039554c7339f8820fef2`, with a projected research-check area of `1.4275251809199722 km2`. `project_boundary_area_km2` remains null because no corresponding project-boundary artifact was recomputed and identity-bound in this offline task. The project KML cannot substitute for the CEA.

## Remaining gate

`runtime_ready=false`, approval is `PENDING_HUMAN_APPROVAL`, and Sentinel-2 access is prohibited. Real source acquisition, raster processing, measurements, runtime provenance, replay, and scientific review remain outstanding.

## Offline verification

Executed from the repository root on 2026-08-29:

```text
uv run --no-project --with 'jsonschema>=4.18,<5' python scripts/validate_step1_specs.py
```

Exit 0. Active contracts were valid at `0.3.0`; EOP101132 retained the exact six Step 2 pending fields.

```text
uv run --no-project python skill/qualify-environmental-evidence/scripts/qualify.py --check-resources --json
```

Exit 0. Output was `RESOURCES_VALID`, `ABSTAINED/INCONCLUSIVE`, `runtime_ready=false`, `scientific_execution_available=false`, and `empirical_environmental_result=false`.

```text
uv run --no-project --with 'jsonschema>=4.18,<5' --with 'pytest>=8,<9' --with 'pyyaml>=6,<7' python -m pytest -o addopts='' -p no:cacheprovider -q
```

Exit 0: `168 passed in 9.06s`.

```text
uv run --no-project python scripts/package_skill.py --check
```

Exit 0: `Skill resources checked: 12 files; no drift.`

```text
uv run --no-project --with 'jsonschema>=4.18,<5' --with 'pytest>=8,<9' --with 'pyyaml>=6,<7' python -m pytest -o addopts='' -p no:cacheprovider -q tests/test_skill_package.py::test_standalone_skill_copy_runs_without_repository
```

Exit 0: `1 passed in 0.95s`.

The accepted skill-creator quick-validation command also returned exit 0: `Skill is valid!`
