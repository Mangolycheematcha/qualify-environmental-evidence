# Step 2B Policy Amendment V4

## Status

`DEMO_QUALIFICATION_POLICY_EOP101132_V4` is a pending proposal. It is not approved, is not runtime-ready, has no detached approval, and has no live run directory.

Canonical proposal SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`.

The exact approved V3 bytes remain at `policies/eop101132/step2b-proposed-policy.json` with SHA-256 `4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59`. The immutable V3 live run remains `ABSTAINED / INCONCLUSIVE / RESOURCE_LIMIT_EXCEEDED` and is not overwritten, relabelled, or reinterpreted.

## Engineering Correction

V3 applied the numeric 40 limit to raw STAC item rows. The live source inventory showed that raw rows can represent multiple tiles from one datatake and can contain multiple processing representations. V4 keeps the number 40 but applies it to independent metadata-admissible acquisition groups after deterministic metadata-only grouping and representation resolution.

This changes the engineering unit of account. It does not raise a limit to accommodate 44 observed rows, invalidate V3, predict that V4 will complete, or provide environmental evidence.

## Frozen Limits

1. `raw_stac_items_per_window_max = 200`: metadata inventory safety control. More than 200 stops without truncation before remote metadata-asset or raster access with `METADATA_INVENTORY_LIMIT_EXCEEDED` and `RESOURCE_LIMIT_EXCEEDED`.
2. `independent_admissible_acquisition_groups_per_window_max = 40`: raster-processing control applied only after complete raw inventory, deterministic grouping, deterministic processing-representation resolution, and metadata-only admissibility. More than 40 stops without truncation before raster access with `RESOURCE_LIMIT_EXCEEDED`.

## Identity And Representation

Independent acquisition identity is `platform + s2:datatake_id`, with authoritative sensing datetime and explicit MGRS tile identity required. Multiple tiles are retained spatial components counted once. Processing representations for `platform + datatake + MGRS tile` are resolved by valid source identity, highest valid processing baseline, most recent authoritative processing timestamp, and only then the lexicographically smallest item ID when preceding metadata and canonical assets are equivalent.

Environmental values cannot affect grouping or selection. Cloud cover, valid-pixel fraction, SCL distribution, NDVI, visual appearance, expected disposition, and closeness to a preferred result are prohibited inputs.

## Unchanged Scientific And Governance Controls

Project, CEA, windows, seasonal rule, collection/assets, no cloud query predicate, SCL classes and resampling, grid, three-acquisition and per-pixel observation rules, 80% joint coverage, NDVI formula, aggregation order, tau 0.03, sensitivity taus, SZA 70-degree limit, radiometry, authority ceiling, forbidden claims, and terminal semantics are unchanged.

## Contract Version

The current contract advances from `0.4.0` to `0.5.0`. Under pre-1.0 semantic versioning this is a minor capability addition: V4 adds machine-readable acquisition grouping, three fail-closed reason states, and explicit representation/group provenance records. It does not alter historical `0.4.0` artifacts.
