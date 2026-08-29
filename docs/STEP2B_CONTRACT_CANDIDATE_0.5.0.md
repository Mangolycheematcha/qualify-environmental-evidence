# Step 2B Contract Candidate 0.5.0

## Scope

Contract `0.5.0` adds deterministic metadata-only Sentinel-2 acquisition grouping and separates metadata inventory safety from raster-processing resource accounting.

## Additions

- Pending policy `DEMO_QUALIFICATION_POLICY_EOP101132_V4`.
- Raw STAC metadata inventory limit of 200 items per window.
- Raster-processing limit of 40 independent metadata-admissible acquisition groups per window.
- `ACQUISITION_IDENTITY_UNRESOLVED`.
- `ACQUISITION_REPRESENTATION_AMBIGUOUS`.
- `METADATA_INVENTORY_LIMIT_EXCEEDED`.
- Processing-representation and acquisition-group provenance records.
- Synthetic offline grouping and boundary tests.

## Compatibility

V3 policy and its `0.4.0` run remain immutable historical evidence. V4 requires a new policy hash, detached approval, run ID, and run directory. No V3 approval can authorise V4.

## Runtime Status

V4 is pending human approval and `runtime_ready=false`. This task does not execute CER, STAC, EO, signing, metadata-asset, raster, coverage, or NDVI operations.
