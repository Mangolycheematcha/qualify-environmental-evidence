# Step 2B V4 Closure

## Decision

Step 2B is closed as:

`SCIENCE_VALID — GOVERNANCE_LIMITATION — NO_RERUN`

The scientific result and cached replay are retained. The run is not described as fully canonical under Approval Protocol V2. The two identified defects are future-runtime work and do not justify another live execution of this case.

Step 3 has not started.

## Run Identity

- Run ID: `EOP101132-STEP2B-V4-20260901T081607339902Z-703540348beaee0f`
- Executable commit: `9e1fabbf005dd29fba09aa82ea18046e99556e02`
- Policy SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`
- Runtime-spec version: `1.1.1`
- Runtime-spec SHA-256: `e7671981e1edbe9b17d2198d68bd873750c40c9489923c403790c34ae9059b51`
- Approval evidence: GitHub Issue `#2`, authored by `Mangolycheematcha`
- Approval evidence SHA-256: `a286ab4ed8f801dbd928a910f5fe799f8183add8ca7c54dc0bfd292b67c00e9b`
- Approval consumption SHA-256: `1eed63f0dc1a5bd7859270c16832b07d620f2d8169836077cb3205441a0a3647`
- Maximum/actual consumption: `1/1`

The approval was created before retrieval and consumption, and consumption preceded environmental-data access. The complete evidence package remains local under the ignored `runs/` directory; this document records its reviewable identities without publishing raw responses, signed URLs, metadata blobs, raster inputs, or caches.

## Scientific Result

- Execution status: `ABSTAINED`
- Evidence disposition: `INCONCLUSIVE`
- Reason: `EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND`
- PRE median NDVI: `0.6630660903670323`
- POST median NDVI: `0.6432938994009436`
- POST-minus-PRE delta: `-0.0197721909660887`
- Primary tau: `0.03`
- AOI pixels: `14256`
- Joint-eligible pixels: `14252`
- Joint coverage: `0.9997194163860831`

The disposition applies only to the frozen observational comparison. It does not validate ACCUs, carbon integrity, causality, additionality, permanence, compliance, project quality, or financial suitability.

## Provenance And Replay

- Assessment SHA-256: `759a173dbdbe2bee8a5689996ae38d226fdc7601118e4c60364a3b9f8561c01f`
- Provenance-manifest SHA-256: `b42cb95d1fa8aeeae7aff758cc18b41986e3d376a758e1a498218fd88bd2471c`
- Aggregation SHA-256: `6f4e51878200fb2c0cd3996a7b802b34ef2411573ffe7f1fdc59d61120393d2b`
- Grouping-output SHA-256: `56b3a57a9fdcca6040c8c7ad1f716ae85dc3c00353712e191b36f539e6a75599`
- AOI-mask SHA-256: `b985f6b5cba77154806b2f2cb6c3982747f442c621eac6a9e4aca116370c0544`
- PRE-composite SHA-256: `69d75c17321a492a6704465b6fc23971afb575423402a039f50370be0ce092fb`
- POST-composite SHA-256: `3499e6f54706ca83801ccf60ffc1fcb523116ad10bb7ea86ff912622df28c7bf`
- Joint-mask SHA-256: `39f4d09af26d3685adab74bab912606b5af1c203649eb401c0f06a95a7e31e53`
- Checksum manifest SHA-256: `34d7cfd94b179f413f93d2a93c1ee5b4fc83bd7d4832089f6af743d497a570ac`

The package contains 337 files. Its checksum manifest covers the other 336 files with no missing, extra, or mismatched entry. Cached replay made no network request and reproduced canonical assessment bytes, all 29 acquisition-array hashes, grouping, composites, and the joint mask.

This establishes deterministic reproducibility from the retained cached arrays. It does not establish a byte-complete record of every HTTP range response used to obtain the original COG windows.

## Diagnostic Area Impact

`diagnostics/target-grid.json` contains an impossible `projected_area_m2` value because coordinates already transformed to `EPSG:32754` were passed to a legacy helper that projects longitude/latitude into UTM. The independently calculated area is approximately `1,427,525.180664 m²`.

The faulty area calculation occurs after target bounds, affine transform, width, height, AOI rasterization, AOI pixel count, and AOI-mask hash are established. No scientific decision rule reads the field. An offline in-memory reconstruction matched:

- bounds, transform, and `258 x 200` shape;
- the 14,256-pixel AOI mask byte-for-byte;
- 116 component-array hashes and 29 acquisition-array hashes;
- PRE and POST composites, joint mask, coverage, medians, delta, and distribution statistics.

Classification: `SCIENCE_UNAFFECTED_DIAGNOSTIC_ONLY`.

## Governance Limitations

The runtime records signing-service and metadata GET attempts, but Rasterio/GDAL performs internal HTTP range requests below that request-level ledger. Those range requests are not individually enumerated. The GDAL configuration also used its own retry count and fixed delay, so the run cannot claim complete compliance with the frozen logical maximum-three-attempt and `0/2/5` backoff semantics.

These facts limit transport provenance and the canonical governance claim. They do not change the selected STAC item, canonical unsigned asset identity, target grid, cached raster-derived arrays, assessment, or offline replay.

- Scientific result: `VALID`
- Transport provenance: `PARTIAL`
- Frozen retry semantics: `NONCOMPLIANT`
- Rerun decision: `NO_RERUN`

## Future Runtime Work

Future runtime development should:

1. calculate projected area directly in the target CRS and add a regression test proving that diagnostic area is not a scientific input;
2. either disable GDAL internal retry and place frozen retry/event handling around each logical raster read, or explicitly exclude internal GDAL range requests from the request-level provenance claim;
3. require a new commit, runtime-spec hash, approval request, and human approval before any future controlled live run.

No historical run artifact, approval record, policy, assessment, provenance manifest, or cached array should be rewritten to apply those changes retrospectively.
