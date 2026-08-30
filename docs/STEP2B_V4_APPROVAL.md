# Step 2B V4 Human Approval Gate

Policy: `DEMO_QUALIFICATION_POLICY_EOP101132_V4`

Contract: `0.5.0`

Status: `PENDING_NEW_THREE-WAY_HUMAN_APPROVAL_AFTER_PRESERVED_RUN_FAILURE`

Runtime ready: `false`

Canonical V4 proposal SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`

Frozen runtime-spec candidate version: `1.0.1`

Frozen runtime-spec SHA-256: `fba1f0547e8f4afc05bee948c8aef18403e5600f5447bb3ba0d0a669b593eab4`

The approved `1.0.0` baseline at commit `5cb475fb4fe577d25314ef1779a69405ca445b96` was consumed by run `EOP101132-STEP2B-V4-20260830T034400613962Z-441a2382987372a0`. The run is preserved as `ERROR / SOURCE_UNAVAILABLE` after a metadata transport timeout, with `raster_pixels_read=false`. Its approval cannot be reused.

Version `1.0.1` adds bounded audited retries, JSON-aware non-finite-value scanning, and primary-error-preserving failure sealing. These are runtime changes and require a new implementation commit and approval even though the V4 policy bytes are unchanged.

New approval must bind all three immutable identifiers:

- policy SHA-256;
- frozen runtime-spec SHA-256;
- exact Git commit.

The QUALIFICATION statement format is:

`批准 QUALIFICATION <policy-sha256> RUNTIME_SPEC <runtime-spec-sha256> COMMIT <git-commit>`

The detached approval record version is `2.0.0`, its allowed scope is `ONE_EOP101132_V4_PRIMARY_RUN`, and `policy_mutation_permitted` must be `false`. The approved policy and runtime-spec bytes must not be mutated to insert their own hashes.
