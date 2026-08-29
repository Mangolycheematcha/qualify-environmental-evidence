# EOP101132 Step 2B Final Runtime Report

Report date: 2026-08-29 (Australia/Sydney)

1. **Run ID:** `EOP101132-STEP2B-20260829T105228553596Z-be9fe09f`.

2. **Approved policy SHA-256:** `4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59` for `DEMO_QUALIFICATION_POLICY_EOP101132_V3`. The approved policy bytes were not mutated.

3. **Detached approval SHA-256:** `703ba24e89c8a0ced7a0b18953cd5a423681ffd96884071bc2c5dc6b9cd76fe1`. Mode was `QUALIFICATION`, scope was one primary EOP101132 run, and policy mutation was forbidden.

4. **CER retrieval and boundary verification:** The official project page returned HTTP 200 at the canonical/final CER URL with `text/html; charset=UTF-8`, 149,412 bytes, and raw SHA-256 `e40258fdd1c9ca3eda0cb39153cac0f0e51cf597ba044ad1972d577ae34e9a1b`. Project ID EOP101132 and project name `Sunday Morning Hills Revegetation` were extracted. The CEA ZIP was 10,219 bytes and exactly matched frozen SHA-256 `3761b2c8b004308db31e06236bb40f2b00c2e0590ec7039554c7339f8820fef2`. It parsed as a valid EPSG:7844 MultiPolygon with 10 exterior polygons and 65 interior rings, role `CEA`, and projected area 1,427,525.1884765625 m2. The original CEA HTTP status, content type, and final URL were not durably captured because a local parser exception occurred before response metadata was saved; this limitation is not backfilled with invented values.

5. **STAC requests and item counts:** Only `sentinel-2-l2a` and the approved CEA/windows were queried, with no `eo:cloud_cover` predicate. PRE used one HTTP request and returned 14 items; POST used two paginated HTTP requests and returned 41 plus 3 items. Counts before/after deduplication were PRE 14/14 and POST 44/44, with zero duplicate STAC item IDs. The POST count exceeded the frozen maximum of 40.

6. **Admitted/excluded item counts:** Item-admissibility evaluation did not run because `RESOURCE_LIMIT_EXCEEDED` is an earlier fail-closed gate. All 58 discovered items remain visible with `admissible: null` and `admissibility_status: NOT_EVALUATED_RESOURCE_LIMIT_EXCEEDED`. Therefore, zero items were determined admitted, zero were determined excluded by solar/radiometry rules, and 58 were explicitly not evaluated. This is not evidence that the 58 items were inadmissible.

7. **Independent acquisition counts:** Not calculated. The run stopped before the frozen acquisition-resolution and admissibility stage; tile/item counts must not be presented as independent acquisition counts.

8. **Processing-baseline distribution:** Discovered PRE items: `02.12` = 14. Discovered POST items: `05.11` = 44.

9. **Solar-geometry summaries:** Diagnostic STAC property `s2:mean_solar_zenith` was finite for all discovered items. PRE: n=14, min 55.2346255, q25 60.2224297, median 64.2027651, q75 65.3938567, max 66.2504892 degrees. POST: n=44, min 53.4818934, q25 59.8601342, median 64.5138852, q75 65.8146137, max 66.3346804 degrees. Discovered median difference was +0.3111201 degrees. Authoritative per-item solar admissibility resolution was not run, so admitted-item summaries and exclusion counts are not available.

10. **AOI grid, pixel count, and rasterised area:** Not calculated because raster processing was prohibited after the resource-limit gate. The verified vector CEA area is 1,427,525.1884765625 m2; no rasterised area or grid-cell comparison exists.

11. **PRE/POST coverage:** Not run; no raster assets were read.

12. **Joint coverage fraction:** Not available.

13. **PRE NDVI median:** Not available.

14. **POST NDVI median:** Not available.

15. **Delta NDVI:** Not available.

16. **Primary result:** `execution_status = ABSTAINED`; `evidence_disposition = INCONCLUSIVE`; human review required. This is not an empirical environmental result.

17. **Primary reason code:** `RESOURCE_LIMIT_EXCEEDED`.

18. **Sensitivity classifications:** Not run. The sensitivity artifact is sealed with `status: NOT_RUN` and no results.

19. **Delta-distribution summary:** Not run; no joint-eligible per-pixel delta array exists.

20. **Primary assessment SHA-256:** `f46822f29ef00c511fdc340c3adf240b5255aa6aec9e9a32e0dd692d1217dcf9`.

21. **Runtime provenance-manifest SHA-256:** `69d3e3c0b054dc9f4ba2ac9610332a78e6ed104b53e115cb5539be39f434e407`.

22. **Live versus offline replay:** Replay used cached inputs with logical network access disabled. Live and replay canonical assessment bytes were exactly equal, both assessment hashes were `f46822f...dcf9`, and there were no derived-array hashes because raster processing did not run. No intentionally variable assessment fields were required.

23. **Validation results:** The complete offline suite passed `197 passed in 21.47s`. The standalone-copy test passed `1 passed in 5.53s`. Package drift check returned `Skill resources checked: 12 files; no drift.` Skill quick validation returned `Skill is valid!`. Linked validation returned `VALID_LINKED_CONTRACT`, runtime mode `EXECUTION`, status `ABSTAINED`, disposition `INCONCLUSIVE`, and reason `RESOURCE_LIMIT_EXCEEDED`. All 67 generated JSON files parsed; the non-finite JSON scan found zero `NaN`/`Infinity` values. All 79 checksum entries matched.

24. **Security scans:** Generated artifacts had zero matches for signed URL/SAS/signature parameters, common credential/private-key patterns, and local machine absolute paths. No signed asset URL was persisted, and no raster signing or asset read occurred.

25. **Complete generated-file list:** The immutable run directory contains 81 files. `runs/EOP101132-STEP2B-20260829T105228553596Z-be9fe09f/checksums.sha256` lists and hashes 79 of them. The two intentionally self-excluded files are that current checksum manifest itself and `source/invalid-attempt-001-ring-as-polygon/derived-before-corrected-query/checksums.sha256`. Together these form the complete 81-file list. Raw source evidence, corrected derived artifacts, replay outputs, diagnostics, and the preserved invalid attempt are all retained under the run directory.

26. **Remaining limitations:** The POST resource limit prevented item-level solar/radiometry adjudication, independent acquisition resolution, raster reads, grid/AOI mask construction, coverage, NDVI, sensitivity, and dispersion calculations. The discovered solar values are diagnostic STAC properties only. The CEA response metadata limitation is described in item 4. An initial local geometry parser incorrectly treated all 75 rings as exteriors; its files were preserved under `source/invalid-attempt-001-ring-as-polygon/`. The corrected parser grouped 10 exteriors and 65 holes and reran the exact STAC query; counts remained 14/44. The primary assessment was preserved byte-for-byte.

27. **No post-result policy change:** Confirmed. No policy ID/hash, temporal window, CEA scope, collection, item limit, threshold, SCL class, acquisition rule, grid, aggregation order, or claim wording was changed after observing results. No Step 3 evaluation, LLM API call, model comparison, orchestration layer, or expanded-year rerun was performed.

## Key Artifacts

- `runs/EOP101132-STEP2B-20260829T105228553596Z-be9fe09f/assessment.json`
- `runs/EOP101132-STEP2B-20260829T105228553596Z-be9fe09f/provenance-manifest.json`
- `runs/EOP101132-STEP2B-20260829T105228553596Z-be9fe09f/run-summary.md`
- `runs/EOP101132-STEP2B-20260829T105228553596Z-be9fe09f/checksums.sha256`
- `runs/EOP101132-STEP2B-20260829T105228553596Z-be9fe09f/inventory/scene-inventory.csv`
- `runs/EOP101132-STEP2B-20260829T105228553596Z-be9fe09f/replay/replay-validation.json`
