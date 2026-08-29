# Step 2B Policy Approval Checkpoint

Status: **PENDING_HUMAN_APPROVAL**
Proposed execution mode: **QUALIFICATION**
Runtime ready: **false**
Policy: `DEMO_QUALIFICATION_POLICY_EOP101132_V3`
Contract candidate: `0.4.0`

Previous policy: `DEMO_QUALIFICATION_POLICY_EOP101132_V2`
Previous proposal SHA-256: `014336ca3aa4db16f1e7b26123c75c1e47013d2463381a5dae0379392e994dac`
V3 proposal bytes: `31,386`
V3 proposal SHA-256: `4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59`

No Planetary Computer STAC item query, signed asset request, Sentinel-2 raster read, EO evidence download, empirical AOI coverage calculation, NDVI calculation, or environmental-result inspection occurred. This hash is not approved and cannot authorise network execution.

## Exact bounded claim

> Within the frozen EOP101132 carbon-estimation-area boundary, the AOI median of per-pixel temporal-median Sentinel-2 L2A NDVI for the seasonally matched 2025-06-01 to 2025-08-31 window is higher than the corresponding 2017-06-01 to 2017-08-31 pre-model-start window by more than the frozen 0.03 NDVI PoC operational indifference band, among pixels satisfying the joint observation-coverage policy.

Qualification remains bounded to this seasonally matched CEA-level NDVI comparison. It does not establish causality, persistence, carbon quantity, additionality, ACCU validity or quality, compliance, assurance, project-wide performance, legal liability, financial suitability, or tokenisation readiness.

## Tau rationale and epistemic status

`tau=0.03 NDVI` under `POC_OPERATIONAL_INDIFFERENCE_BAND_V1` was frozen before any Sentinel-2 item query or NDVI result. It is a conservative PoC governance margin that prevents sign-only or numerically small positive or negative differences from automatically forcing `CORROBORATING` or `CONTRADICTORY`.

The motivating uncertainty layers are Sentinel-2 L2A surface-reflectance uncertainty, SCL and cloud-edge limitations, residual processing-baseline and radiometric differences, BRDF and illumination geometry, and classification-boundary and resampling effects. See the approved primary sources for [Sentinel-2 products](https://sentiwiki.copernicus.eu/web/s2-products) and [Sentinel-2 processing](https://sentiwiki.copernicus.eu/web/s2-processing).

The number `0.03` was not derived from a project-specific end-to-end uncertainty budget. It is not a quantitatively derived detection limit, official Sentinel-2 threshold, ecological threshold, CER rule, regulatory threshold, audit criterion, assurance standard, or market standard. It requires future domain validation.

The registered secondary values are `0.01`, `0.02`, and `0.05`. They test whether a classification is dependent on the primary operational choice. Each result is stored separately and cannot replace, overwrite, or retroactively reinterpret the primary `0.03` disposition.

## Solar-zenith scene admissibility

The frozen rule is:

| Field | Value |
|---|---|
| Rule ID | `SENTINEL2_MEAN_SOLAR_ZENITH_MAX_V1` |
| Metadata field | `mean_solar_zenith_angle` |
| Maximum | `70.0 degrees`, inclusive |
| Resolution | `PER_ITEM_OR_GRANULE` |
| Date/location inference | `FORBIDDEN` |
| Application stage | `BEFORE_ACQUISITION_COUNT_AND_COVERAGE` |
| Basis | `COPERNICUS_QUANTITATIVE_USE_LIMIT` |

Runtime must resolve authoritative mean SZA independently for every item. Date, latitude, season, another item, or a window average may never supply a fallback. A finite numeric value at or below `70.0` is admitted. A value above `70.0` receives `SOLAR_GEOMETRY_OUT_OF_RANGE`; missing, non-finite, contradictory, string/unparseable, or otherwise unresolved metadata receives `SOLAR_GEOMETRY_METADATA_UNRESOLVED`.

Every discovered item remains in the scene inventory. An excluded item contributes to neither independent-acquisition count, valid-pixel coverage, nor NDVI. Exclusion is a deterministic observation-quality decision, not a system `ERROR`. Remaining admitted evidence may continue when every frozen acquisition and coverage gate passes; otherwise the run uses the applicable existing `ABSTAINED/INCONCLUSIVE` sufficiency guard. No selectively chosen replacement outside the frozen search policy is allowed.

Per-item provenance records item ID, acquisition datetime, platform, datatake identity, mean SZA or null, metadata source, parse/cross-check status, admissibility, exclusion reason, and processing baseline. Each window separately reports discovered and admitted count, minimum, q25, median, q75, maximum, missing count, above-limit exclusions, and unresolved exclusions. Post-minus-pre median SZA is descriptive only, not a new threshold or symmetry gate. Residual BRDF and illumination effects remain a limitation.

## Baseline-year immutability

The primary windows remain exactly:

- Pre: `2017-06-01` through `2017-08-31`
- Post: `2025-06-01` through `2025-08-31`

Machine-readable scope freezes `primary_pre_years=[2017]`, `primary_post_years=[2025]`, and `additional_baseline_years=[]`. The PoC uses one pre-model-start seasonal year and therefore does not estimate interannual baseline variability or establish that 2017 is climatologically typical.

Post-result window changes are prohibited. Any future 2016 JJA, other additional year, or multi-year analysis must be a separately declared secondary or exploratory extension with a new policy ID, policy hash, and run ID. It cannot overwrite, replace, or retroactively reinterpret the frozen primary disposition.

## Approved-hash binding

Before any network access, runtime must receive an explicit approved policy SHA-256 and calculate the local policy byte hash. The values must match exactly. The approved hash is recorded at run start and again in the final manifest; input and policy hashes must remain unchanged throughout the run. A mutation terminates before STAC access. The V3 proposal currently has `approved_policy_sha256=null`, `approval_status=PENDING_HUMAN_APPROVAL`, and `runtime_ready=false`.

## Remaining limitations

- No empirical EO result exists.
- One pre-year does not estimate interannual variability or climatological typicality.
- The operational tau is not a project-specific uncertainty budget or scientific detection limit.
- Seasonal matching and the 70-degree per-item guard do not eliminate residual BRDF or illumination effects.
- SCL, reflectance, processing-baseline, registration, resampling, and cloud-edge limitations remain.
- Scientific review, real-source replay, and Step 3 evaluation remain outstanding.

## Decision required

- `批准 QUALIFICATION 4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59`
- `批准 MEASUREMENT_ONLY 4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59`
- `修改：具体项目和值`

The original task prompt and this proposal do not constitute approval. Stop before EO access until one exact decision is explicitly recorded.
