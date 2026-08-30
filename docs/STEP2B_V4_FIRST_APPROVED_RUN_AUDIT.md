# Step 2B V4 First Approved Run Audit

## Identity

- Run ID: `EOP101132-STEP2B-V4-20260830T034400613962Z-441a2382987372a0`
- Policy SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`
- Runtime-spec SHA-256: `3ac7684ed5dad74428d03496a41f676a125c12be1f7930aad3121cc05a5054cb`
- Git commit: `5cb475fb4fe577d25314ef1779a69405ca445b96`
- Detached approval SHA-256: `e7e6cc9bf2e1dd733bd237fe2e85c9917f74608699286ecf42804e2488a21835`

## Preserved Outcome

- Stage: `ERROR`
- Primary reason: `SOURCE_UNAVAILABLE`
- Network accessed: `true`
- Raster pixels read: `false`
- Ended at: `2026-08-30T03:48:05.204262Z`

The primary failure was a Windows transport timeout while retrieving post-window Sentinel-2 metadata. The pre-window metadata pass completed first and formed seven admissible independent acquisition groups. The run did not produce an assessment, coverage result, NDVI measurement, qualification, or Step 3 evaluation.

## Secondary Finding

Failure sealing then encountered a scanner false positive. The frozen runtime specification contains the policy string `NaN/Infinity`, and immutable Sentinel product XML can contain source-level text values such as `NaN`. The byte-regex scanner treated those strings as generated non-finite numeric output and masked the primary error at the command boundary. The preserved run state and `diagnostics/runtime-failure.json` retained the correct primary reason.

## Disposition

The run is immutable and cannot resume under the same run ID. Runtime-spec `1.0.1` corrects the scanner semantics, adds a finite audited retry policy, and prevents secondary sealing errors from replacing the primary exception. A new commit, runtime-spec hash, and human approval are required before another live run.
