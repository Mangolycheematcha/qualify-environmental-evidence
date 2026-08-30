# Step 2B V4 Second Approved Run Audit

## Run Identity

- Run ID: `EOP101132-STEP2B-V4-20260830T041242319779Z-24e3f17288b106b7`
- Created UTC: `2026-08-30T04:12:42.319779Z`
- Ended UTC: `2026-08-30T04:14:05.114160Z`
- Approval: `批准 QUALIFICATION 3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd RUNTIME_SPEC fba1f0547e8f4afc05bee948c8aef18403e5600f5447bb3ba0d0a669b593eab4 COMMIT b355df332e2e42a0ed4515d71781bfd859f86abf`
- Detached approval SHA-256: `fdfe3eed195f9270db2a5326bdab78848c4ba019a292efbb42f381cc7e950bc6`
- Policy SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`
- Runtime-spec: `1.0.1`, SHA-256 `fba1f0547e8f4afc05bee948c8aef18403e5600f5447bb3ba0d0a669b593eab4`
- Execution Git commit: `b355df332e2e42a0ed4515d71781bfd859f86abf`

## Source And Execution Result

- Sources requested: CER project page, frozen CER CEA archive, and Microsoft Planetary Computer `sentinel-2-l2a` STAC pre/post searches.
- Successful source access: CER project page, CEA archive, and the complete 14-item pre-window STAC response.
- Failed source access: post-window STAC response timed out before a response artifact was persisted.
- Recorded run-state network access: `false` due to the audit-state defect described below.
- Independently verified actual network access: `true`, established by persisted HTTP 200 metadata, retrieval timestamps, response hashes, and source payloads.
- Retry history: successful CER/CEA/pre-STAC requests used one attempt each; the failed raw `TimeoutError` bypassed the retry wrapper, so no retry was performed or recorded for the post request.
- Product/granule metadata access: not started.
- Raster pixel read: `false`.
- NDVI result: not generated.
- Qualification result: not generated.
- Step 3: **NOT EXECUTED**.
- Hidden fallback or source substitution: none.

The preserved terminal state is `ERROR / DETERMINISTIC_PROCESSING_ERROR`. The run must not be resumed, replayed, overwritten, or reclassified.

## Defects And Correction

1. A raw `TimeoutError` from `urlopen` escaped the `RuntimeFailure`-only retry wrapper and was classified by the command boundary as `DETERMINISTIC_PROCESSING_ERROR`.
2. `network_accessed=true` was persisted only after both STAC windows completed, leaving the immutable run-state value false despite verified source retrievals.

Runtime-spec `1.0.2` corrects both defects by treating raw `TimeoutError` as retryable under the unchanged three-attempt policy and persisting conservative network-access state before the first request. Regression tests were added. No corrective code was applied to this run and its approval was not reused.

## Evidence And Integrity

- Run root: `runs/EOP101132-STEP2B-V4-20260830T041242319779Z-24e3f17288b106b7/`
- Approval: `approval/approval.json`
- Frozen inputs: `frozen/policy.json`, `frozen/runtime-spec.json`
- Failure: `diagnostics/runtime-failure.json`
- State: `run-state.json`
- Source evidence: `source/`
- Boundary cache: `cache/`
- Checksums: `checksums.sha256`

Key SHA-256 values:

- `run-state.json`: `71d9081dff4060c1f746a47cd6500f89b7be66907f5833476739ef82ca9e9eaf`
- `diagnostics/runtime-failure.json`: `45f99ae696aa5b084bf8faffe55c501130bb0a3004fe7bc51172a49dce56dde7`
- `checksums.sha256`: `989f103ca291f4a9827edeaf6913e3fad4a502d9ec903d2e548fdb625d926920`
- `source/cer-project-page.metadata.json`: `097d5662e78aaecd133cceb4f7d808ff0050d8be5bb71865e8faf531390c6757`
- `source/eop101132-cea.metadata.json`: `083ae831945de6c826211d6a419b4e97ba032f526dedd1585e14354b9c76fe7c`
- `source/stac-pre-requests.json`: `cd6943a4267c71dfbc541989aa6dda9de701e35b89b5f558eb1e391ee55230cc`
- `source/stac-pre.raw.json`: `11817c0ff51da1972bc3f8f0556bef7fc118463451e53353386668dafd918421`

## Verification

- Pre-run full suite: `236 passed`.
- Post-defect full suite after regression additions: `238 passed`.
- Previous approved run compared with its archived copy: `136/136` files, zero differences.
- Policy mutation: none.
- Runtime-spec mutation during execution: none.
- Evidence overwrite: none.
- Final Git status after corrective freeze commit: clean; commit identity is reported externally to avoid a self-referential document.
