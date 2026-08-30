# Step 2B V4 Third Approval Preflight

## Approval Identity

- Policy SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`
- Runtime-spec version: `1.0.2`
- Runtime-spec SHA-256: `9bbfdd8c1e73a8a0393afbbec7570e4a28616b204dff2fbed2db17d8dd9a4508`
- Approved Git commit: `863169af556c5e93dac541131bc92abe00d3e028`

## Preflight Result

The approval was not consumed. No detached approval record, Run ID, or network execution was created.

The repository passed its existing 238 tests, exact Git/policy/runtime-spec checks, and prior-run immutability checks. Direct inspection then found that regression coverage did not exercise the required terminal branch where a raw `TimeoutError` persists through all three frozen attempts.

Existing tests covered:

- bounded retries that succeed on the third attempt;
- raw `TimeoutError` that succeeds on the second attempt;
- conservative network-access state persistence;
- preservation of an already-classified `SOURCE_UNAVAILABLE` failure.

They did not directly prove that three persistent raw timeouts remain `SOURCE_UNAVAILABLE`, retain exactly three attempt records, and do not become `DETERMINISTIC_PROCESSING_ERROR`.

## Correction

A focused regression test was added without changing runtime code, policy bytes, runtime-spec semantics, retry counts, timeout thresholds, source configuration, or qualification rules. Because the Git commit changes, the supplied approval cannot authorize a future live run even though the policy and runtime-spec hashes remain unchanged.

Post-correction verification: `239 passed`; runtime-spec `VALID`. The corrective Git commit is reported externally to avoid self-reference.
