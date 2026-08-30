# Changelog

All notable contract and platform changes are recorded here. This project has not made a public release.

## Unreleased

- Established an audited private Git baseline.
- Added public-readiness, security, attribution, reproducibility, and release-control documentation.
- Preserved V3 policy and live-run hashes as immutable historical evidence.
- Proposed contract `0.5.0` and policy `DEMO_QUALIFICATION_POLICY_EOP101132_V4`.
- Changed the resource-accounting unit from raw STAC item rows to deterministic, metadata-admissible independent acquisition groups while retaining the limit of 40.
- Added a separate 200-raw-item metadata inventory safety limit.
- Added deterministic acquisition identity and processing-representation resolution controls.
- Added a separately hashed V4 runtime specification with exact implementation-file and package bindings.
- Added three-way detached approval binding for the V4 policy hash, runtime-spec hash, and Git commit.
- Implemented metadata-asset resolution, acquisition-group raster processing, calibrated NDVI aggregation, primary sealing, and exact AOI-cache replay.
- Added synthetic V4 runtime, array-hash, raster-calibration, coverage, assessment, and provenance tests.
- Preserved the first three-way-approved V4 run after a `SOURCE_UNAVAILABLE` metadata timeout before raster access.
- Corrected a failure-sealing scanner false positive caused by policy text and immutable source XML containing the strings `NaN` or `Infinity`.
- Added a frozen three-attempt transport retry policy and ensured failure sealing cannot replace the primary runtime reason.
- Preserved the second three-way-approved V4 run after a raw `TimeoutError` escaped the retry wrapper during post-window STAC retrieval.
- Corrected conservative network-access audit state so it is persisted before the first request, and made raw `TimeoutError` use the frozen retry policy.
- Added the missing pre-run regression for persistent raw timeout exhaustion, exact three-attempt history, and terminal `SOURCE_UNAVAILABLE` classification; the pending third approval was not consumed.
- Preserved the third three-way-approved V4 run after it completed live raster processing, NDVI qualification, provenance sealing, and cached-input replay as `ABSTAINED / INCONCLUSIVE / EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND`.
- Recorded that Step 2B is complete for the approved run and Step 3 was not executed.

## 0.4.0

- Completed the specification-first contract and platform baseline.
- Added V3 solar-geometry and radiometry gates.
- Performed the first bounded live source run, which correctly abstained before raster access because 44 POST raw STAC items exceeded the frozen raw-item limit of 40.
