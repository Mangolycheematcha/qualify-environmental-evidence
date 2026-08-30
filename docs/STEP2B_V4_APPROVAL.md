# Step 2B V4 Human Approval Gate

Policy: `DEMO_QUALIFICATION_POLICY_EOP101132_V4`

Contract: `0.5.0`

Status: `THIRD_THREE-WAY_APPROVAL_CONSUMED_STEP2B_COMPLETE`

Runtime ready: `false`

Canonical V4 proposal SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`

Frozen runtime-spec candidate version: `1.0.2`

Frozen runtime-spec SHA-256: `9bbfdd8c1e73a8a0393afbbec7570e4a28616b204dff2fbed2db17d8dd9a4508`

The approved `1.0.0` baseline at commit `5cb475fb4fe577d25314ef1779a69405ca445b96` was consumed by run `EOP101132-STEP2B-V4-20260830T034400613962Z-441a2382987372a0`. The run is preserved as `ERROR / SOURCE_UNAVAILABLE` after a metadata transport timeout, with `raster_pixels_read=false`. Its approval cannot be reused.

The approved `1.0.1` baseline at commit `b355df332e2e42a0ed4515d71781bfd859f86abf` was consumed by run `EOP101132-STEP2B-V4-20260830T041242319779Z-24e3f17288b106b7`. It is preserved as `ERROR / DETERMINISTIC_PROCESSING_ERROR` after a raw transport `TimeoutError` bypassed the retry wrapper during post-window STAC retrieval. It read no raster pixels and produced no NDVI, qualification, or Step 3 result. Its approval cannot be reused.

Version `1.0.2` makes raw `TimeoutError` use the frozen retry policy and persists conservative network-access state before the first request. These runtime changes require a new implementation commit and approval even though the V4 policy bytes are unchanged.

The subsequent approval bound to commit `863169af556c5e93dac541131bc92abe00d3e028` was not consumed because preflight inspection found missing direct regression coverage for persistent raw timeout exhaustion. A focused test was added, producing a new Git commit while leaving policy and runtime-spec bytes unchanged.

The new approval bound to commit `bf0b1a33230ff2d6e259aab2cca087bc8c21dbbf` was consumed exactly once by run `EOP101132-STEP2B-V4-20260830T044223516364Z-73144a299e2d5763`. The run completed the frozen Step 2B workflow as `ABSTAINED / INCONCLUSIVE / EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND`, read permitted raster pixels, calculated NDVI, and passed cached-input replay. Step 3 was not executed. See `STEP2B_V4_THIRD_APPROVED_RUN_AUDIT.md`.

That single-use approval cannot be reused. Any future controlled execution requires a new exact commit and new three-way approval.

Any future approval must bind all three immutable identifiers:

- policy SHA-256;
- frozen runtime-spec SHA-256;
- exact Git commit.

The QUALIFICATION statement format is:

`批准 QUALIFICATION <policy-sha256> RUNTIME_SPEC <runtime-spec-sha256> COMMIT <git-commit>`

The detached approval record version is `2.0.0`, its allowed scope is `ONE_EOP101132_V4_PRIMARY_RUN`, and `policy_mutation_permitted` must be `false`. The approved policy and runtime-spec bytes must not be mutated to insert their own hashes.
