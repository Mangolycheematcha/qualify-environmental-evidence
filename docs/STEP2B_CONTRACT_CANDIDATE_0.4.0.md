# Step 2B Contract Candidate 0.4.0

Status: **IMPLEMENTED AND TESTED OFFLINE; PENDING HUMAN APPROVAL**

This is a forward contract extension from `0.3.0`. It does not rewrite the accepted Step 1 `0.2.0` record or the prior Step 2B `0.3.0` candidate record.

## Version justification

The policy-only identity advances from V2 to V3. The executable contract advances from `0.3.0` to `0.4.0` because two controlled reason codes and required solar-geometry and run-hash provenance fields were added. This follows the repository's pre-1.0 forward-extension convention and is the smallest justified increment.

## Additions

- Machine-bound the ex-ante epistemic status of `tau=0.03` and rejected authoritative-threshold relabelling.
- Added `SENTINEL2_MEAN_SOLAR_ZENITH_MAX_V1`, inclusive at `70.0` degrees, resolved per item or granule with no date/location fallback.
- Added item-level `SOLAR_GEOMETRY_OUT_OF_RANGE` and `SOLAR_GEOMETRY_METADATA_UNRESOLVED` exclusions with run-level controlled-abstention semantics.
- Required a complete item inventory and separate discovered/admitted SZA summaries, plus a descriptive post-minus-pre median diagnostic.
- Froze the primary years to 2017 and 2025, prohibited post-result primary-window changes, and required new policy and run identities for future extensions.
- Added approved-policy hash binding and immutable policy/input hashes from run start through final provenance.
- Added pure static-metadata helpers and tests; no network or raster implementation was introduced.

## Policy identity

- Old: `DEMO_QUALIFICATION_POLICY_EOP101132_V2`
- Old SHA-256: `014336ca3aa4db16f1e7b26123c75c1e47013d2463381a5dae0379392e994dac`
- New: `DEMO_QUALIFICATION_POLICY_EOP101132_V3`
- New SHA-256: `4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59`

## Remaining gate

`approved_policy_sha256=null`, `approval_status=PENDING_HUMAN_APPROVAL`, and `runtime_ready=false`. No STAC query, signing, Sentinel-2 read, EO download, coverage calculation, NDVI calculation, or environmental-result inspection has occurred.
