# qualify-environmental-evidence

## Project title | 项目标题

**English:** Qualify Environmental Evidence — A Reproducible Skill PoC for Registry and Earth-Observation Evidence
**中文：** 环境证据限定与资格判断——面向注册信息与地球观测证据的可复现 Skill PoC

> **A reproducible proof of concept for qualifying—not validating—public registry and Earth-observation evidence before use in regulated financial workflows.**

> **一个可复现的概念验证：在公开注册信息与地球观测证据进入受监管金融流程前，限定其可以支持的主张，而不是验证环境资产本身。**

**Status:** Step 2B contract candidate v0.4.0 and policy `DEMO_QUALIFICATION_POLICY_EOP101132_V3`, SHA-256 `4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59`, pending human approval. Historical Step 1 v0.2.0 and the V2 policy bytes remain preserved. No Sentinel-2 item query, signed URL, raster read, EO download, empirical coverage or NDVI result, project-quality conclusion, ACCU-integrity conclusion or model-comparison result is claimed.

---

## Project objective | 项目目标

### English

Build a small, deterministic, auditable and reproducible skill that receives a bounded observational claim about a registry-recorded environmental project and decides whether explicitly allowlisted public evidence can support that claim within a frozen spatial, temporal and evidentiary scope.

The skill must:

- validate the claim before retrieving evidence;
- use only allowlisted evidence sources and transformations;
- complete a bounded qualification when every required control passes;
- abstain when evidence or a required scientific policy is insufficient;
- refuse a request that exceeds the authority of the evidence;
- emit a schema-valid assessment, stable reason codes and a complete provenance manifest; and
- make every material output traceable to its source, transformation and policy version.

The PoC qualifies evidence for a narrow use. It does not validate an ACCU, certify a project, estimate carbon abatement, determine regulatory compliance or make a financial decision.

### 中文

构建一个小型、确定性、可审计、可复现的 skill。它接收一条关于已登记环境项目的**有界观察性主张**，只使用明确列入 allowlist 的公开证据和转换步骤，判断这些证据能否在冻结的空间、时间与权威边界内支持该主张。

该 skill 必须：

- 在调取证据前先验证 claim contract；
- 只使用获准的 evidence sources 与 transformations；
- 所有控制通过时完成有限的证据资格判断；
- 证据或科学规则不足时必须 abstain；
- 用户要求超出证据权威时必须 refuse；
- 输出符合 schema 的 assessment、稳定 reason codes 和完整 provenance manifest；
- 让每个关键输出都能追溯到来源、转换步骤和政策版本。

本 PoC 限定证据可以支持什么，不判断 ACCU 或项目本身是否“有效”。

---

## Skill contract at a glance | Skill 合同总览

| Contract element | Frozen definition |
| --- | --- |
| Input | A versioned claim contract plus case specification; runtime execution is prohibited while required Step 2 fields remain pending. |
| Allowed evidence | Four machine-readable source IDs covering the CER register, the EOP101132 record, its published CEA mapping artifact and Sentinel-2 L2A. |
| Allowed reasoning | A fixed, ordered transformation registry; unregistered or reordered operations are rejected. |
| Output | A versioned assessment using a registered bounded-statement template and linked to a schema-valid provenance manifest. |
| Abstention | Missing/unfrozen specifications, unresolved source versions, inadequate observations, spatial/temporal failure or unresolved evidence conflict. |
| Refusal | Any request for causality, carbon quantity, ACCU quality, compliance, legal liability, financial action or another forbidden inference. |
| Audit trail | Canonical source identifiers, checksums, acquisition IDs, transformation records, parameter hashes, policy versions, software versions and output hashes. |
| Success | Schema validity, negative-test rejection, allowlist integrity, complete lineage, deterministic replay and three bounded demonstration outcomes. |

---

## Explicit need | 明确需求

Public Earth-observation data can be technically accessible while still being unsafe to use as financial evidence. The central failure is often not missing data but **inference expansion**: a descriptive observation is silently upgraded into a statement about causality, carbon quantity, project integrity, compliance or investment quality.

公开地球观测数据即使可以获取，也不代表它能直接成为金融证据。核心风险通常不是“没有数据”，而是**推断膨胀**：系统把描述性观察静默升级为因果、碳量、项目完整性、监管合规或投资质量判断。

The PoC therefore inserts a deterministic assurance boundary between:

1. registry facts;
2. published project-boundary facts;
3. Earth-observation measurements;
4. evidence qualification; and
5. conclusions reserved for regulators, methodology experts, auditors or financial decision-makers.

### Functional requirements

| ID | Requirement | Acceptance meaning |
| --- | --- | --- |
| FR-01 | Accept only a versioned, bounded claim contract | Project, observable, comparison, authority ceiling and forbidden inferences are explicit. |
| FR-02 | Enforce an evidence-source allowlist | Every evidence source ID exists in the source registry and is used only for its permitted purpose. |
| FR-03 | Enforce an ordered transformation allowlist | Every executed operation is registered, parameterised and recorded in the permitted sequence. |
| FR-04 | Use the CER-published CEA as the AOI | A hand-drawn, tile-level or visually enlarged area cannot substitute for the published boundary. |
| FR-05 | Calculate AOI-level valid-observation coverage | Scene-level eo:cloud_cover may pre-filter candidates but cannot qualify AOI coverage. |
| FR-06 | Apply frozen spatial, temporal, seasonal and SCL rules | Scientific rules cannot be chosen after observing the result. |
| FR-07 | Produce descriptive AOI-bounded summaries | Initial runtime metrics are observation coverage and seasonally matched NDVI summaries. |
| FR-08 | Separate execution status from evidence disposition | COMPLETED, ABSTAINED, REFUSED and ERROR have non-overlapping semantics. |
| FR-09 | Enforce the authority ceiling | Requests for forbidden conclusions are refused before expensive evidence processing. |
| FR-10 | Emit stable reason codes | Free-form verdicts cannot substitute for registered reasons. |
| FR-11 | Emit complete provenance | Every structured response points to a manifest that records attempted and completed operations. |
| FR-12 | Reproduce canonical outputs | Frozen inputs, code and policy versions produce identical canonical assessment content. |

### Non-functional requirements

- **Auditability:** every material observation and disposition is traceable to a source, rule and transformation.
- **Determinism:** scientific calculations and qualification rules are deterministic.
- **Portability:** the initial PoC uses public sources and ordinary Python tooling.
- **Minimalism:** no vector database, persistent memory, multi-agent orchestration, API service or production UI.
- **Reviewability:** a third party can inspect schemas, registries, case specifications, manifests and tests.
- **No hidden reasoning requirement:** the audit trail records inputs, operations, parameters and rules—not private chain-of-thought.

---

## Worked case and current datasets | 案例与当前数据

The current worked case is **EOP101132 — Sunday Morning Hills Revegetation, Victoria, Australia**. The Clean Energy Regulator project page reports a model start date of **2017-10-06** and provides carbon-estimation-area and project-area mapping files.

### Evidence-source allowlist

Step 1 freezes these stable source IDs in config/evidence-sources.json.

| Source ID | Public source | Permitted use | Prohibited use |
| --- | --- | --- | --- |
| CER_ACCU_PROJECT_REGISTER | [CER ACCU Project and Contract Register](https://cer.gov.au/markets/reports-and-data/accu-project-and-contract-register) | Resolve public register context and registry attributes | Transaction tape, project-quality proof or causal evidence |
| CER_PROJECT_RECORD | [CER project EOP101132](https://cer.gov.au/schemes/australian-carbon-credit-unit-scheme/accu-project-and-contract-register/project/EOP101132) for this case | Resolve project identity, public dates, method description and mapping references | Proof that the project caused an observed change |
| CER_PUBLISHED_CEA | CER-published carbon-estimation-area mapping artifact linked from the project record | Freeze the case-specific AOI geometry after retrieval, validation and hashing | Hand-drawn replacement AOI or proof of ecological condition |
| MSPC_SENTINEL2_L2A | [Microsoft Planetary Computer Sentinel-2 L2A](https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a) | Resolve STAC items and B04, B08 and SCL assets for bounded observations | Causality, carbon quantity, additionality, ACCU validity or compliance |

The [Planetary Computer zonal-statistics notebook](https://github.com/microsoft/PlanetaryComputerExamples/blob/main/tutorials/zonal_statistics.ipynb) is an implementation reference. It is not an evidence source and must never appear as empirical support.

### Source-authority rules

- Registry sources establish only the fields actually published by the CER.
- The CEA artifact defines the spatial scope only after its exact file and checksum are frozen.
- Sentinel-2 L2A supports descriptive spectral observations only.
- Signed asset URLs are temporary access mechanisms, not canonical provenance identifiers.
- No unregistered source may be silently substituted, even if it appears technically similar.
- FullCAM, proponent data, field data and independent ecological evidence are absent; conclusions that require them remain unavailable.

### Data not used in the initial PoC

- FullCAM outputs;
- project-proponent private data;
- field measurements;
- confidential bank data;
- ACCU transaction or broker-price data;
- tokenisation or blockchain data;
- third-party carbon ratings.

---

## Allowed transformation contract | 获准转换合同

Step 1 freezes the following ordered operation IDs in config/allowed-transformations.json. It defines their contracts but does not implement the geospatial operations.

| Order | Transformation ID | Controlled purpose |
| ---: | --- | --- |
| 1 | VALIDATE_CLAIM_CONTRACT | Reject malformed, unbounded or runtime-ineligible inputs. |
| 2 | CHECK_AUTHORITY_SCOPE | Refuse forbidden claims before evidence processing. |
| 3 | RESOLVE_REGISTRY_FACTS | Resolve allowlisted CER facts and versions. |
| 4 | RESOLVE_CEA_BOUNDARY | Retrieve, validate and hash the published CEA artifact. |
| 5 | SEARCH_SENTINEL2_L2A | Identify candidate items within frozen spatial and temporal constraints. |
| 6 | ALIGN_AOI_RASTERS | Align AOI, SCL, B04 and B08 grids under a frozen policy. |
| 7 | APPLY_SCL_VALIDITY_MASK | Apply only the frozen valid/invalid SCL mapping. |
| 8 | CALCULATE_AOI_VALID_COVERAGE | Calculate valid pixels divided by eligible AOI pixels. |
| 9 | CALCULATE_AOI_NDVI | Calculate descriptive AOI-level NDVI from B08 and B04. |
| 10 | AGGREGATE_SEASONAL_WINDOWS | Aggregate only under the frozen seasonal-matching rule. |
| 11 | QUALIFY_OBSERVATIONAL_CLAIM | Apply coverage, conflict and authority gates to the bounded claim. |
| 12 | EMIT_ASSESSMENT_AND_PROVENANCE | Emit linked, schema-valid assessment and audit artifacts. |

### Transformation invariants

- The operation order is fixed; a case may stop early but cannot reorder or insert operations.
- On REFUSED, operations 3–11 are recorded as skipped and operation 12 emits the refusal trail.
- On ABSTAINED or ERROR, unexecuted downstream operations are recorded as skipped with a registered reason.
- Every executed operation records implementation version, parameter-set identity, input artifact references, output artifact references and status.
- An LLM may later help formalise a natural-language request, but it cannot invent sources, transformations, measurements or verdicts.

---

## Functional boundary | 功能边界

### In scope after the relevant rules are frozen

- validate a versioned claim contract;
- resolve and version allowlisted registry and mapping sources;
- align the published CEA with Sentinel-2 pixels;
- calculate valid observations inside the AOI using a frozen SCL policy;
- report per-acquisition and per-window observation coverage;
- calculate seasonally matched, descriptive AOI-level NDVI summaries;
- qualify one bounded observational comparison;
- abstain or refuse with stable reason codes;
- emit linked assessment and provenance artifacts.

### Forbidden inferences

The skill must not infer or state:

1. causal attribution;
2. carbon quantity;
3. additionality;
4. ACCU validity, quality or integrity;
5. regulatory or methodology compliance;
6. permanence;
7. project performance beyond the bounded observation;
8. greenwashing or legal liability;
9. investment, lending, purchase or trading recommendations; or
10. tokenisation readiness.

The skill does not replace the CER, an auditor, a remote-sensing or methodology expert, or a financial decision-maker.

---

## Primary user scenario | 主要用户场景

### User

An analyst performing early-stage due diligence on a registry-recorded land-based environmental asset before public evidence enters a regulated financial workflow.

### Bounded question

> Within the frozen EOP101132 CEA, is the 2025 seasonally matched AOI median of per-pixel temporal-median Sentinel-2 L2A NDVI higher than the corresponding 2017 pre-model-start value by more than the frozen 0.03 NDVI PoC operational indifference band, among pixels satisfying the joint observation-coverage policy?

This is an observational comparison. It is not equivalent to “Do satellite data prove that the ACCUs are valid?”

### Final pre-runtime policy closure

- `tau=0.03` was selected before observation as a conservative PoC operational margin. It is not a scientific detection limit, official Sentinel-2 threshold, ecological threshold, CER rule, regulatory criterion or assurance standard. Sensitivity taus `0.01`, `0.02` and `0.05` remain secondary and cannot replace the primary disposition.
- `SENTINEL2_MEAN_SOLAR_ZENITH_MAX_V1` admits a scene only when authoritative per-item or per-granule mean SZA is a finite numeric value at or below `70.0` degrees. Date, latitude, season, another item and window averages are forbidden fallbacks. Excluded items remain in provenance and cannot enter acquisition count, coverage or NDVI.
- Primary years remain exactly pre-2017 and post-2025. The design does not estimate interannual baseline variability or establish that 2017 is climatologically typical. Future years require a new policy ID, policy hash and run ID and cannot overwrite the primary result.
- An explicitly approved policy hash must match the local policy bytes before network access. Policy and input hashes are immutable throughout a run. The current proposal has no approved hash and `runtime_ready=false`.

### Three demonstration outcomes

| Scenario | Execution status | Evidence disposition |
| --- | --- | --- |
| Every frozen control passes and delta is outside the inclusive +/-0.03 operational band | COMPLETED | CORROBORATING or CONTRADICTORY |
| Every upstream control passes and delta is inside or on the inclusive +/-0.03 operational band | ABSTAINED | INCONCLUSIVE |
| A required rule/source is unresolved or observations fail the frozen sufficiency policy | ABSTAINED | INCONCLUSIVE |
| The requested conclusion exceeds observational authority | REFUSED | null |

No outcome is selected before the relevant inputs and rules are frozen.

---

## Input specification | 输入规范

Runtime input is JSON conforming to the versioned claim-contract schema. The following is a Step 1 specification object, not a runtime-ready request.

~~~json
{
  "schema_version": "0.5.0",
  "case_id": "EOP101132-NDVI-001",
  "runtime_ready": false,
  "project": {
    "project_id": "EOP101132",
    "project_name": "Sunday Morning Hills Revegetation",
    "registry_url": "https://cer.gov.au/schemes/australian-carbon-credit-unit-scheme/accu-project-and-contract-register/project/EOP101132",
    "declared_model_start_date": "2017-10-06",
    "jurisdiction": "Australia",
    "state": "Victoria"
  },
  "claim_contract": {
    "claim_type": "OBSERVATIONAL_COMPARISON",
    "observable": "AOI_SEASONAL_NDVI",
    "claim_text": "Within the frozen EOP101132 carbon-estimation-area boundary, the AOI median of per-pixel temporal-median Sentinel-2 L2A NDVI for the seasonally matched 2025-06-01 to 2025-08-31 window is higher than the corresponding 2017-06-01 to 2017-08-31 pre-model-start window by more than the frozen 0.03 NDVI PoC operational indifference band, among pixels satisfying the joint observation-coverage policy.",
    "analysis_boundary_role": "CEA",
    "pre_window_identity": {"start_date": "2017-06-01", "end_date": "2017-08-31"},
    "post_window_identity": {"start_date": "2025-06-01", "end_date": "2025-08-31"},
    "seasonal_rule_id": "MATCHED_AUSTRAL_WINTER_JJA_V1",
    "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
    "aggregation": "AOI median of per-pixel temporal-median Sentinel-2 L2A NDVI",
    "eligible_population": "Pixels satisfying DEMO_AOI_JOINT_MINCOUNT_COVERAGE_V1 in both windows",
    "primary_indifference_band_policy_id": "POC_OPERATIONAL_INDIFFERENCE_BAND_V1",
    "primary_tau": 0.03,
    "authority_ceiling": "OBSERVATIONAL_CONSISTENCY_ONLY",
    "forbidden_inferences": [
      "CAUSAL_ATTRIBUTION",
      "CARBON_QUANTITY",
      "ADDITIONALITY",
      "CREDIT_VALIDITY_OR_QUALITY",
      "REGULATORY_OR_METHODOLOGY_COMPLIANCE",
      "PERMANENCE",
      "PROJECT_PERFORMANCE_BEYOND_BOUNDED_OBSERVATION",
      "GREENWASHING_OR_LEGAL_LIABILITY",
      "FINANCIAL_RECOMMENDATION",
      "TOKENISATION_READINESS"
    ]
  },
  "evidence_policy": {
    "registry_version": "0.5.0",
    "allowed_source_ids": [
      "CER_ACCU_PROJECT_REGISTER",
      "CER_PROJECT_RECORD",
      "CER_PUBLISHED_CEA",
      "MSPC_SENTINEL2_L2A"
    ],
    "source_bindings": [
      {
        "source_id": "CER_ACCU_PROJECT_REGISTER",
        "canonical_uri": "https://cer.gov.au/markets/reports-and-data/accu-project-and-contract-register",
        "discovery_uri": null,
        "retrieval_uri": null,
        "binding_status": "FROZEN"
      },
      {
        "source_id": "CER_PROJECT_RECORD",
        "canonical_uri": "https://cer.gov.au/schemes/australian-carbon-credit-unit-scheme/accu-project-and-contract-register/project/EOP101132",
        "discovery_uri": null,
        "retrieval_uri": null,
        "binding_status": "FROZEN"
      },
      {
        "source_id": "CER_PUBLISHED_CEA",
        "canonical_uri": null,
        "discovery_uri": "https://cer.gov.au/schemes/australian-carbon-credit-unit-scheme/accu-project-and-contract-register/project/EOP101132",
        "retrieval_uri": null,
        "binding_status": "PENDING_STEP_2"
      },
      {
        "source_id": "MSPC_SENTINEL2_L2A",
        "canonical_uri": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a",
        "discovery_uri": null,
        "retrieval_uri": null,
        "binding_status": "FROZEN"
      }
    ]
  },
  "transformation_policy": {
    "registry_version": "0.5.0",
    "required_transformation_ids": [
      "VALIDATE_CLAIM_CONTRACT",
      "CHECK_AUTHORITY_SCOPE",
      "RESOLVE_REGISTRY_FACTS",
      "RESOLVE_CEA_BOUNDARY",
      "SEARCH_SENTINEL2_L2A",
      "ALIGN_AOI_RASTERS",
      "APPLY_SCL_VALIDITY_MASK",
      "CALCULATE_AOI_VALID_COVERAGE",
      "CALCULATE_AOI_NDVI",
      "AGGREGATE_SEASONAL_WINDOWS",
      "QUALIFY_OBSERVATIONAL_CLAIM",
      "EMIT_ASSESSMENT_AND_PROVENANCE"
    ]
  },
  "spatial_scope": {
    "status": "PENDING_STEP_2",
    "boundary_source_id": "CER_PUBLISHED_CEA",
    "boundary_artifact_uri": null,
    "boundary_sha256": null
  },
  "temporal_scope": {
    "status": "PENDING_STEP_2",
    "pre_window": null,
    "post_window": null,
    "seasonal_rule": null
  },
  "qualification_policy": {
    "policy_version": "0.5.0",
    "proposed_execution_mode": "QUALIFICATION",
    "approval_status": "PENDING_HUMAN_APPROVAL",
    "indifference_band": {
      "policy_id": "POC_OPERATIONAL_INDIFFERENCE_BAND_V1",
      "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
      "tau": 0.03,
      "unit": "NDVI",
      "lower_boundary_inclusive": true,
      "upper_boundary_inclusive": true,
      "epistemic_status": "DEMO_OPERATIONAL_RULE",
      "ecological_standard": false,
      "regulatory_standard": false,
      "instrument_detection_limit": false,
      "assurance_standard": false
    },
    "sensitivity_tau_values": [0.01, 0.02, 0.05],
    "scl_rule": "PENDING_STEP_2",
    "observation_coverage_rule": "PENDING_STEP_2"
  },
  "pending_step_2": [
    "BOUNDARY_FILE_AND_CHECKSUM",
    "PRE_WINDOW",
    "POST_WINDOW",
    "SEASONAL_MATCHING_RULE",
    "SCL_VALIDITY_RULE",
    "OBSERVATION_COVERAGE_POLICY"
  ]
}
~~~

### Input invariants

- Unknown controlled fields, sources and transformations are rejected.
- The source IDs must exist in the evidence registry.
- Each allowed source ID has exactly one case-specific source binding.
- PENDING_STEP_2 bindings must have an allowlisted discovery URI and a null unresolved canonical artifact URI.
- Transformation IDs must match the registered sequence exactly.
- A missing authority ceiling is a specification failure.
- runtime_ready must remain false while any Step 2 field is pending.
- Step 1 must not guess scientific or data-derived parameters.

---

## Output specification | 输出规范

The following is a schema fixture demonstrating abstention. It is not an empirical output.

~~~json
{
  "schema_version": "0.5.0",
  "case_id": "SCHEMA-FIXTURE-ABSTAINED-001",
  "run_id": "SCHEMA-FIXTURE-ABSTAINED",
  "execution_status": "ABSTAINED",
  "evidence_disposition": "INCONCLUSIVE",
  "reason_codes": [
    "TEMPORAL_SCOPE_NOT_FROZEN"
  ],
  "quality_checks": {
    "claim_contract": "PASS",
    "evidence_allowlist": "PASS",
    "transformation_allowlist": "PASS",
    "spatial_scope": "NOT_RUN",
    "temporal_scope": "FAIL",
    "observation_coverage": "NOT_RUN",
    "evidence_consistency": "NOT_RUN",
    "authority_scope": "PASS",
    "provenance": "PASS",
    "system_execution": "PASS"
  },
  "observations": null,
  "statement_template_id": null,
  "supported_statement": null,
  "must_not_claim": [
    "CAUSAL_ATTRIBUTION",
    "CARBON_QUANTITY",
    "ADDITIONALITY",
    "CREDIT_VALIDITY_OR_QUALITY",
    "REGULATORY_OR_METHODOLOGY_COMPLIANCE",
    "PERMANENCE",
    "PROJECT_PERFORMANCE_BEYOND_BOUNDED_OBSERVATION",
    "GREENWASHING_OR_LEGAL_LIABILITY",
    "FINANCIAL_RECOMMENDATION",
    "TOKENISATION_READINESS"
  ],
  "human_review_required": true,
  "provenance_manifest_ref": "urn:fixture:manifest:abstained",
  "qualification_policy_version": "0.5.0",
  "statement_parameters": null
}
~~~

### Controlled output objects

quality_checks has exactly these keys:

~~~text
claim_contract
evidence_allowlist
transformation_allowlist
spatial_scope
temporal_scope
observation_coverage
evidence_consistency
authority_scope
provenance
system_execution
~~~

Each check is PASS, FAIL or NOT_RUN.

When observations is non-null, it includes the original coverage and window summaries plus the three-way qualification fields:

~~~text
observation_status: COMPLETE | PARTIAL
aoi_total_pixels: non-negative integer or null
aoi_valid_pixels: non-negative integer or null
aoi_valid_fraction: number in [0, 1] or null
pre_window_ndvi_median: number in [-1, 1] or null
post_window_ndvi_median: number in [-1, 1] or null
delta_ndvi: number in [-2, 2] or null
primary_tau: 0.03 or null
delta_distribution: count/q05/q25/median/q75/q95/IQR/MAD or null
sensitivity_results: classifications for tau 0.01, 0.02 and 0.05 or null
~~~

COMPLETED and the controlled indifference-band abstention require `observation_status=COMPLETE` and all measurement fields non-null. PARTIAL observations may be retained only for audit and cannot support a disposition.

For complete observations, aoi_total_pixels must be positive, aoi_valid_pixels cannot exceed it, and aoi_valid_fraction must equal aoi_valid_pixels divided by aoi_total_pixels under the frozen serialization tolerance. The primary comparison uses canonical decimal semantics: delta greater than +0.03 is CORROBORATING, delta less than -0.03 is CONTRADICTORY, and the inclusive interval [-0.03, +0.03] is ABSTAINED/INCONCLUSIVE with `EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND`.

Completed v0.4.0 statements use the active versioned templates:

~~~text
OBSERVATIONAL_COMPARISON_CORROBORATING_V2
OBSERVATIONAL_COMPARISON_CONTRADICTORY_V2
~~~

The templates are frozen in config/statement-templates.json. Each renders only the bounded comparison, AOI, frozen windows, observation policy and mandatory limitation language. Non-completed outputs require statement_template_id and supported_statement to be null.

Every completed statement ends with:

> This bounded observation does not establish causality, carbon quantity, additionality, ACCU validity, project compliance or financial suitability.

### Status invariants

| Execution status | Evidence disposition | Statement template | Required behavior |
| --- | --- | --- | --- |
| COMPLETED | CORROBORATING or CONTRADICTORY | Matching registered template | All required checks pass; complete observations, bounded statement and provenance are present. |
| ABSTAINED | INCONCLUSIVE | null | A registered insufficiency/conflict/resource reason applies, or every upstream check passes and the complete delta lies inside the operational band; human review required. |
| REFUSED | null | null | At least one authority reason; evidence-processing stages are skipped. |
| ERROR | null | null | At least one system reason; no evidence conclusion is emitted. |

Every emitted assessment, including REFUSED and ERROR, must reference a provenance manifest. INCONCLUSIVE is never presented as a completed result.

### Mandatory abstention conditions

The skill must abstain when any of the following prevents a bounded evaluation:

- a required Step 2 specification is not frozen;
- the exact boundary artifact or checksum is unresolved;
- an evidence source is unavailable or cannot be versioned;
- AOI overlap is empty;
- raster/SCL alignment cannot be established;
- the Sentinel-2 processing baseline cannot be resolved;
- valid AOI observation coverage fails the frozen policy;
- seasonal comparability fails the frozen rule; or
- relevant evidence conflict remains unresolved.

An unallowlisted source or transformation is a specification violation, not permission to improvise.

### Mandatory refusal conditions

The skill must refuse when the requested output asks it to cross the authority ceiling, including requests for ACCU validation, causality, carbon quantity, additionality, permanence, compliance, legal liability, greenwashing determinations, financial recommendations or tokenisation readiness.

---

## Provenance and audit trail | 来源与审计轨迹

Step 1 defines schemas/provenance-manifest.schema.json. A plain reference field is insufficient: the referenced manifest must itself validate.

| Manifest section | Required content |
| --- | --- |
| Identity | Manifest ID, run ID, case ID, schema version, runtime mode, UTC creation time, approved/start/final policy hashes and immutable input hashes |
| Sources | Allowlisted source ID, canonical URI, publisher, retrieved time, version identifier, content SHA-256 and source-specific asset IDs |
| Solar geometry | Every discovered item, authoritative mean SZA or null, metadata source/cross-check, admissibility and exclusion reason; separate discovered/admitted window summaries and descriptive median difference |
| Artifacts | Stable artifact ID, media/data type, content hash and generating source/transformation |
| Transformations | Sequence number, allowlisted transformation ID, implementation version, parameter-set reference/hash, input/output artifact refs, status and timestamps |
| Policies | Evidence, transformation, statement-template, forbidden-inference, reason-code and qualification-policy versions |
| Environment | Code revision, Python version, package-lock hash and relevant library versions |
| Terminal result | Assessment artifact reference and SHA-256, terminal execution status and registered reason codes |

### Provenance invariants

- Every source record uses an allowlisted source ID.
- Every transformation record uses an allowlisted ID and preserves registered order.
- Executed transformations reference existing inputs and outputs.
- Skipped and failed stages record a registered reason code.
- Canonical references must not contain expiring signatures or access tokens.
- Assessment run_id, case_id and terminal status must agree with the manifest.
- Approved, start and final policy hashes must match; start and final input hashes must match.
- Solar geometry is resolved per item before acquisition count and coverage; an inadmissible item cannot contribute to coverage or NDVI.
- Assessment hashes use UTF-8 JSON serialised with sorted keys, compact separators and no ASCII escaping; the manifest records canonicalisation ID CANONICAL_JSON_V1.
- A COMPLETED assessment with missing lineage is invalid.
- The audit trail records reproducible action metadata and rule applications; it does not request or store hidden model reasoning.

---

## Initial reason-code families | 原因码范围

- **Specification:** claim unbounded, required field missing, runtime policy not frozen, source/transformation unregistered;
- **Source/version:** source unavailable, canonical identifier or version unresolved;
- **Spatial:** boundary not frozen, no AOI overlap, alignment failure;
- **Temporal:** windows or seasonal rule unresolved;
- **Observation quality:** processing baseline unresolved or valid coverage insufficient;
- **Evidence conflict:** relevant evidence conflict unresolved;
- **Authority:** requested conclusion exceeds observational authority;
- **Provenance:** manifest, lineage or hash incomplete;
- **Governance:** human/specialist review required;
- **System:** deterministic processing failure.

Free-form verdict labels are not allowed.

---

## Quantitative targets | 量化目标

These are engineering acceptance targets, not claims about ecological truth or ACCU quality.

### Step 1 specification targets

| ID | Target |
| --- | --- |
| S1-QT-01 | 100% of required schemas, registries and Step 1 fixtures parse and validate. |
| S1-QT-02 | 100% of required negative tests reject the intended invalid condition. |
| S1-QT-03 | 0 unknown or duplicate evidence, transformation, statement-template, reason or forbidden-inference entries. |
| S1-QT-04 | 100% of representative assessment fixtures link to a schema-valid provenance fixture. |
| S1-QT-05 | 100% of transformation traces use the registered order; no silent insertion or reordering. |
| S1-QT-06 | 100% of runtime-ready checks fail while any required Step 2 parameter is pending. |
| S1-QT-07 | 0 empirical environmental measurements or conclusions are introduced in Step 1. |
| S1-QT-08 | 100% of completed fixtures use a registry-backed, disposition-matched statement template; all other fixtures have no statement. |

### Later PoC acceptance targets

| ID | Target |
| --- | --- |
| POC-QT-01 | Identical frozen inputs, code and policy versions produce identical canonical assessment content, excluding declared run metadata. |
| POC-QT-02 | 100% of material observations trace to source artifacts and transformation records. |
| POC-QT-03 | AOI valid-observation coverage is reported per acquisition and per frozen window; scene-level cloud cover never substitutes for it. |
| POC-QT-04 | Deliver one completed bounded case, one naturally occurring evidence-insufficiency case and one authority refusal. |
| POC-QT-05 | 100% of authority-overreach acceptance cases return REFUSED with null disposition. |
| POC-QT-06 | Run a 12–15-case acceptance/regression suite; do not market it as a general benchmark. |
| POC-QT-07 | A fresh user can reproduce the worked case with no more than three documented commands. |

No ecological-accuracy target is claimed because this PoC has no ecological ground truth.

---

## Current implementation stage | 当前阶段

**Step 1 contract specification and acceptance remain historically complete for version 0.2.0.** See the [evidence-backed Step 1 acceptance record](docs/STEP1_ACCEPTANCE.md).

It creates and tests:

- claim-contract schema;
- assessment-output schema;
- provenance-manifest schema;
- evidence-source registry;
- allowed-transformation registry;
- bounded-statement-template registry;
- forbidden-inference registry;
- reason-code registry;
- EOP101132 case specification with explicit Step 2 pending fields;
- deterministic schema and cross-registry validation.

Step 1 does not download CER or Sentinel-2 data, choose scientific parameters, calculate pixels or NDVI, call an LLM, or build an agent.

**Step 2 platform packaging is complete for the repository-contained contract-only skill.** See the [platform packaging acceptance record](docs/STEP2_PLATFORM_ACCEPTANCE.md). The package validates specifications and linked contract artifacts, reports pending fields, and follows controlled refusal paths; it does not execute EO processing or validate environmental assets.

**Step 2B contract candidate v0.4.0 is pending human approval.** It advances the policy from V2 to V3 while preserving the exact V2 bytes. In addition to the existing indifference band and radiometry controls, it adds the ex-ante tau rationale, the inclusive per-item 70-degree mean-SZA rule, complete solar-geometry provenance, one-year baseline immutability, future-extension identity rules, and approved-policy/input hash binding. The word “persistent” and multi-year trend or climatological-typicality claims are excluded from the authoritative completed statement.

The 0.03 band is not an instrument detection limit, ecological threshold, CER rule, regulatory threshold, audit criterion or assurance standard. Scale, offset, quantification value, nodata, processing baseline and solar geometry must be resolved independently for every item from authoritative metadata. Qualification concerns only the bounded seasonally matched NDVI comparison over joint-eligible pixels.

No EO query or empirical result has occurred. Scientific/runtime EO processing remains unavailable while approval is pending and `runtime_ready=false`. Hallucination/accuracy, performance, and broader security evaluation are Step 3 work and are not complete.

---

## Repository versus installable skill

This README belongs to the public research/engineering repository. The repository-contained skill is packaged under `skill/qualify-environmental-evidence/` with only the instructions, scripts, references, and allowlisted contract resources needed for this verified capability. Repository sources remain authoritative and generated package copies are guarded by a hash manifest and drift check. The package has not been globally installed or published.
