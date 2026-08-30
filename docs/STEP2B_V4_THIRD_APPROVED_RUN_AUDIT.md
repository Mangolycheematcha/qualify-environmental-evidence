# Step 2B V4 Completed Scientific Run Record

> Superseded governance classification: subsequent independent audit returned `VALID_TECHNICAL_RUN_BUT_APPROVAL_BINDING_INVALID`. This document preserves technical observations but does not establish approval. See `docs/incidents/STEP2B_V4_APPROVAL_BINDING_FAILURE.md`.

## Identity

- Run ID: `EOP101132-STEP2B-V4-20260830T044223516364Z-73144a299e2d5763`
- Authorised execution commit: `bf0b1a33230ff2d6e259aab2cca087bc8c21dbbf`
- Policy SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`
- Runtime-spec version: `1.0.2`
- Runtime-spec SHA-256: `9bbfdd8c1e73a8a0393afbbec7570e4a28616b204dff2fbed2db17d8dd9a4508`
- Detached approval SHA-256: `c995bde4e8b7c9994f65f2b64e1ac4d03325e9a02ee1b4cdcd36920e257ef6d0`

The local approval record was consumed exactly once by the implementation, but it was self-attested and did not constitute independent human approval. The run was fresh, was not resumed from an earlier run, and remains local under the ignored `runs/` directory.

## Outcome

- Execution status: `ABSTAINED`
- Evidence disposition: `INCONCLUSIVE`
- Primary reason: `EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND`
- Network accessed: `true`
- Raster pixels read: `true`
- Step 3: `NOT EXECUTED`

The run completed CER project-page access, CEA retrieval and hash verification, pre-window STAC access, post-window STAC access, metadata gating, permitted raster reads, NDVI derivation, qualification, provenance sealing, and cached-input replay. It did not substitute a source or bypass STAC.

All 121 recorded request-attempt fields had a value of one. No operation required a retry, no raw exception history was produced, and no runtime failure record exists. The conservative `network_accessed=true` state was visible while the run was still at `RAW_STAC_INVENTORY_COMPLETE`, before raster access.

## Observation

- PRE raw STAC items: `14`
- POST raw STAC items: `44`
- PRE admissible independent acquisition groups: `7`
- POST admissible independent acquisition groups: `22`
- AOI total pixels: `14256`
- AOI valid pixels: `14252`
- Joint valid fraction: `0.9997194163860831`
- PRE NDVI median: `0.6630660903670323`
- POST NDVI median: `0.6432938994009436`
- Delta NDVI: `-0.0197721909660887`
- Primary tau: `0.03`

The primary result qualifies only the bounded observational NDVI comparison. It does not validate the ACCU, project, carbon quantity, causality, additionality, permanence, compliance, credit quality, project integrity, or investment suitability.

## Integrity

- Assessment SHA-256: `1b6297f81d1bafc847ef02dac9cb0c2ada91bf03ccedf75759bb07e4002f00dc`
- Provenance-manifest SHA-256: `5749fc7fd0b6ee55a98732b2f9ab02a47e125f874e1be9d30be8ad3f63dc3926`
- Grouping-output SHA-256: `56b3a57a9fdcca6040c8c7ad1f716ae85dc3c00353712e191b36f539e6a75599`
- Aggregation SHA-256: `6f4e51878200fb2c0cd3996a7b802b34ef2411573ffe7f1fdc59d61120393d2b`
- Run checksum verification: `332 entries, 0 mismatches`
- Offline replay: canonical assessment bytes and hash equal; network access `false`
- Post-run automated tests: `239 passed`

The first and second historical V4 attempts were compared with their independent Agent archives after this run and remained byte-identical: `136/136` and `33/33` files respectively, with zero differences. Repository policy and runtime-spec bytes remained identical to the frozen run copies.

## Boundary

STEP 2B COMPLETE — STEP 3 NOT EXECUTED.

Any later documentation or GitHub publication commit is not the commit authorised for this live execution. No future controlled run is authorised by the consumed approval.
