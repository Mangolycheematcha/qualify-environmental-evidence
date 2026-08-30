# Step 2B V4 Human Approval Gate

Policy: `DEMO_QUALIFICATION_POLICY_EOP101132_V4`

Contract: `0.5.0`

Status: `PENDING_THIRD_THREE-WAY_HUMAN_APPROVAL_AFTER_SECOND_PRESERVED_RUN_FAILURE`

Runtime ready: `false`

Canonical V4 proposal SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`

Frozen runtime-spec candidate version: `1.0.2`

Frozen runtime-spec SHA-256: `9bbfdd8c1e73a8a0393afbbec7570e4a28616b204dff2fbed2db17d8dd9a4508`

The approved `1.0.0` baseline at commit `5cb475fb4fe577d25314ef1779a69405ca445b96` was consumed by run `EOP101132-STEP2B-V4-20260830T034400613962Z-441a2382987372a0`. The run is preserved as `ERROR / SOURCE_UNAVAILABLE` after a metadata transport timeout, with `raster_pixels_read=false`. Its approval cannot be reused.

The approved `1.0.1` baseline at commit `b355df332e2e42a0ed4515d71781bfd859f86abf` was consumed by run `EOP101132-STEP2B-V4-20260830T041242319779Z-24e3f17288b106b7`. It is preserved as `ERROR / DETERMINISTIC_PROCESSING_ERROR` after a raw transport `TimeoutError` bypassed the retry wrapper during post-window STAC retrieval. It read no raster pixels and produced no NDVI, qualification, or Step 3 result. Its approval cannot be reused.

Version `1.0.2` makes raw `TimeoutError` use the frozen retry policy and persists conservative network-access state before the first request. These runtime changes require a new implementation commit and approval even though the V4 policy bytes are unchanged.

New approval must bind all three immutable identifiers:

- policy SHA-256;
- frozen runtime-spec SHA-256;
- exact Git commit.

The QUALIFICATION statement format is:

`批准 QUALIFICATION <policy-sha256> RUNTIME_SPEC <runtime-spec-sha256> COMMIT <git-commit>`

The detached approval record version is `2.0.0`, its allowed scope is `ONE_EOP101132_V4_PRIMARY_RUN`, and `policy_mutation_permitted` must be `false`. The approved policy and runtime-spec bytes must not be mutated to insert their own hashes.
