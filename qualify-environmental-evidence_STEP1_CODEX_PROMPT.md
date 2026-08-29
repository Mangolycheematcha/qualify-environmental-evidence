# Codex execution prompt — Step 1 contract freeze

Copy the complete prompt below into Codex while the intended project directory is open.

---

## Prompt

Implement **Step 1 only** of the project qualify-environmental-evidence.

Start by acknowledging the task in one sentence. Inspect the repository, any AGENTS.md, existing files and git status. Preserve all unrelated and user-authored changes. Give a short implementation plan before editing.

## Goal

Create a minimal, deterministic and tested contract layer for a public environmental-evidence qualification PoC.

Step 1 must freeze:

1. bounded claim input;
2. evidence-source allowlist;
3. ordered transformation allowlist;
4. assessment output;
5. abstention/refusal semantics;
6. forbidden-inference and reason-code registries;
7. provenance/audit-trail requirements; and
8. the EOP101132 specification-mode case.

Do not implement geospatial processing, remote-sensing calculations, an LLM workflow or an agent in this step.

## Project context

Project name: qualify-environmental-evidence

English title:

> Qualify Environmental Evidence — A Reproducible Skill PoC for Registry and Earth-Observation Evidence

Chinese title:

> 环境证据限定与资格判断——面向注册信息与地球观测证据的可复现 Skill PoC

Positioning:

> A reproducible proof of concept for qualifying—not validating—public registry and Earth-observation evidence before use in regulated financial workflows.

Reference case:

- Project ID: EOP101132
- Project name: Sunday Morning Hills Revegetation
- Jurisdiction: Australia
- State: Victoria
- Declared model start date: 2017-10-06

Official references:

- CER register: https://cer.gov.au/markets/reports-and-data/accu-project-and-contract-register
- CER project page: https://cer.gov.au/schemes/australian-carbon-credit-unit-scheme/accu-project-and-contract-register/project/EOP101132
- Planetary Computer Sentinel-2 L2A: https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a

First bounded claim:

> Within the published CEA for EOP101132, the frozen post-period's seasonally matched AOI-level Sentinel-2 NDVI summary is higher than the frozen pre-period summary, subject to the declared observation-coverage policy.

This is an observational comparison. It cannot establish causality, carbon quantity, additionality, project or ACCU integrity, compliance, permanence, legal liability or financial suitability.

## Required repository outputs

Follow coherent existing conventions if present. Otherwise create only this structure:

~~~text
schemas/
  claim-contract.schema.json
  assessment-output.schema.json
  provenance-manifest.schema.json
config/
  evidence-sources.json
  allowed-transformations.json
  statement-templates.json
  forbidden-inferences.json
  reason-codes.json
cases/
  eop101132/
    case-spec.json
scripts/
  validate_step1_specs.py
tests/
  test_step1_specs.py
pyproject.toml
~~~

Create or minimally update pyproject.toml only when needed for jsonschema and pytest configuration. Do not create other documentation, notebooks, APIs, UIs, deployment files or agent frameworks. Do not rewrite an existing README unless a tiny command/path correction is strictly necessary.

Use JSON Schema Draft 2020-12 for all schemas. Require additionalProperties: false at every controlled object level unless a comment in the schema explains a narrowly necessary exception.

Use version 0.2.0 consistently across Step 1 schemas and registries.

## 1. Evidence-source registry

Create config/evidence-sources.json as a versioned registry with exactly these source IDs:

~~~text
CER_ACCU_PROJECT_REGISTER
CER_PROJECT_RECORD
CER_PUBLISHED_CEA
MSPC_SENTINEL2_L2A
~~~

For each source require:

- source_id;
- publisher;
- evidence_type;
- canonical_uri or canonical discovery URI;
- authority_scope;
- permitted_uses;
- prohibited_uses;
- stable_identifier_strategy;
- version_resolution_method;
- step1_status.

Use controlled step1_status values:

~~~text
IDENTITY_FROZEN
ARTIFACT_PENDING_STEP_2
~~~

Freeze these authority rules:

- CER_ACCU_PROJECT_REGISTER may establish only published register context and attributes.
- CER_PROJECT_RECORD may establish only fields and mapping references published on a case-bound CER project record.
- CER_PUBLISHED_CEA may define the AOI only after the case-specific exact artifact and SHA-256 are frozen in Step 2.
- MSPC_SENTINEL2_L2A may support only bounded descriptive spectral observations.
- Scene-level eo:cloud_cover may pre-filter candidate scenes but may not substitute for AOI-level valid-observation coverage.
- Signed or expiring URLs are access mechanisms, not canonical identifiers.
- No source supports causality, carbon quantity, additionality, ACCU quality, compliance or financial action.

The EOP101132 case must reference only registered source IDs and bind the generic CER_PROJECT_RECORD and CER_PUBLISHED_CEA source types to EOP101132. Unknown, duplicate or silently substituted sources must fail validation.

Do not retrieve any source in Step 1.

## 2. Allowed-transformation registry

Create config/allowed-transformations.json as a versioned registry containing this exact ordered pipeline:

~~~text
1  VALIDATE_CLAIM_CONTRACT
2  CHECK_AUTHORITY_SCOPE
3  RESOLVE_REGISTRY_FACTS
4  RESOLVE_CEA_BOUNDARY
5  SEARCH_SENTINEL2_L2A
6  ALIGN_AOI_RASTERS
7  APPLY_SCL_VALIDITY_MASK
8  CALCULATE_AOI_VALID_COVERAGE
9  CALCULATE_AOI_NDVI
10 AGGREGATE_SEASONAL_WINDOWS
11 QUALIFY_OBSERVATIONAL_CLAIM
12 EMIT_ASSESSMENT_AND_PROVENANCE
~~~

For each transformation require:

- sequence;
- transformation_id;
- purpose;
- input_types;
- output_types;
- parameter_source;
- implementation_stage;
- required_audit_fields;
- prohibited_behaviors.

Use controlled parameter_source values:

~~~text
NONE
FROZEN_CASE_SPEC
DETERMINISTIC_DERIVATION
~~~

Use controlled implementation_stage values:

~~~text
STEP_1_CONTRACT_ONLY
STEP_2_OR_LATER
~~~

Freeze these invariants:

- a case must reference the exact registered sequence;
- operations may stop early but cannot be inserted, deleted or reordered;
- skipped or failed downstream operations must remain visible in provenance;
- every executed operation must record implementation version, parameter-set identity or hash, input/output artifact references and status;
- an unregistered transformation is a specification failure, not permission to improvise.

Step 1 defines these operation contracts only. Do not implement or execute transformations 3–11.

## 3. Forbidden-inference registry

Create config/forbidden-inferences.json as a versioned registry. Each entry requires code, description and why the inference is outside the PoC authority ceiling.

Include exactly these required codes:

~~~text
CAUSAL_ATTRIBUTION
CARBON_QUANTITY
ADDITIONALITY
CREDIT_VALIDITY_OR_QUALITY
REGULATORY_OR_METHODOLOGY_COMPLIANCE
PERMANENCE
PROJECT_PERFORMANCE_BEYOND_BOUNDED_OBSERVATION
GREENWASHING_OR_LEGAL_LIABILITY
FINANCIAL_RECOMMENDATION
TOKENISATION_READINESS
~~~

The EOP101132 case and representative outputs must include all codes. Missing, duplicate or unknown codes fail validation.

## 4. Reason-code registry

Create config/reason-codes.json as a versioned registry. Each entry requires:

- code;
- category;
- description;
- default_execution_status;
- default_human_review_required.

Controlled categories:

~~~text
SPECIFICATION
SOURCE_VERSION
SPATIAL
TEMPORAL
OBSERVATION_QUALITY
EVIDENCE_CONFLICT
AUTHORITY
PROVENANCE
GOVERNANCE
SYSTEM
~~~

Freeze at least these codes:

~~~text
CLAIM_NOT_BOUNDED
REQUIRED_FIELD_MISSING
RUNTIME_SPECIFICATION_NOT_FROZEN
EVIDENCE_SOURCE_NOT_ALLOWED
TRANSFORMATION_NOT_ALLOWED
TRANSFORMATION_SEQUENCE_INVALID
BOUNDARY_NOT_FROZEN
TEMPORAL_SCOPE_NOT_FROZEN
SEASONAL_RULE_NOT_FROZEN
SOURCE_UNAVAILABLE
SOURCE_VERSION_UNRESOLVED
CANONICAL_IDENTIFIER_UNRESOLVED
AOI_NO_OVERLAP
SCL_ALIGNMENT_FAILED
PROCESSING_BASELINE_UNRESOLVED
VALID_OBSERVATION_COVERAGE_LOW
EVIDENCE_CONFLICT_UNRESOLVED
AUTHORITY_SCOPE_EXCEEDED
CAUSALITY_UNSUPPORTED
CARBON_QUANTITY_UNSUPPORTED
CREDIT_VALIDITY_UNSUPPORTED
COMPLIANCE_UNSUPPORTED
FINANCIAL_DECISION_UNSUPPORTED
PROVENANCE_INCOMPLETE
PROVENANCE_HASH_MISMATCH
HUMAN_REVIEW_REQUIRED
DETERMINISTIC_PROCESSING_ERROR
~~~

Do not add speculative ecological or legal conclusions as reason codes.

Map specification/evidence insufficiency to ABSTAINED, authority overreach to REFUSED and deterministic software failure to ERROR. A reason registry default does not override the assessment cross-field invariants below.

## 5. Claim-contract schema

Create schemas/claim-contract.schema.json.

Require:

- schema_version;
- case_id;
- runtime_ready;
- project;
- claim_contract;
- evidence_policy;
- transformation_policy;
- spatial_scope;
- temporal_scope;
- qualification_policy;
- pending_step_2.

Controlled values:

~~~text
claim_type: OBSERVATIONAL_COMPARISON
observable: AOI_SEASONAL_NDVI
authority_ceiling: OBSERVATIONAL_CONSISTENCY_ONLY
spatial_scope.status: PENDING_STEP_2 | FROZEN
temporal_scope.status: PENDING_STEP_2 | FROZEN
~~~

The evidence policy must carry registry_version, allowed_source_ids and source_bindings. The transformation policy must carry registry_version and required_transformation_ids.

Each source binding requires:

- source_id;
- canonical_uri, nullable only while a case-specific artifact is pending;
- discovery_uri, nullable when canonical_uri is already frozen;
- binding_status.

Controlled binding_status values:

~~~text
FROZEN
PENDING_STEP_2
~~~

Enforce through schema and validator:

- only registered source and transformation IDs;
- no duplicates;
- exactly one source binding for each allowed source ID and no extra binding;
- a PENDING_STEP_2 binding has null canonical_uri and a non-null allowlisted discovery_uri;
- a FROZEN binding has a non-null canonical_uri;
- exact transformation order;
- all required forbidden-inference codes;
- runtime_ready is false whenever pending_step_2 is non-empty or a required scientific field is pending/null;
- runtime_ready may be true only when the boundary artifact/checksum, pre/post windows, seasonal rule, SCL rule and observation-coverage policy are frozen.

Step 1 must permit explicit specification mode but prevent accidental runtime mode.

## 6. EOP101132 case specification

Create cases/eop101132/case-spec.json and validate it against the claim schema.

Use:

~~~text
schema_version: 0.2.0
case_id: EOP101132-NDVI-001
runtime_ready: false
project_id: EOP101132
project_name: Sunday Morning Hills Revegetation
declared_model_start_date: 2017-10-06
jurisdiction: Australia
state: Victoria
~~~

Use the bounded claim and authority ceiling above.

Reference all four evidence source IDs and the exact ordered transformation list.

Bind:

- CER_ACCU_PROJECT_REGISTER to the official register URL above;
- CER_PROJECT_RECORD to the official EOP101132 project URL above;
- CER_PUBLISHED_CEA to the EOP101132 project URL as discovery_uri, with canonical_uri null and binding_status PENDING_STEP_2;
- MSPC_SENTINEL2_L2A to the official dataset URL above.

Include pending_step_2 with exactly:

~~~text
BOUNDARY_FILE_AND_CHECKSUM
PRE_WINDOW
POST_WINDOW
SEASONAL_MATCHING_RULE
SCL_VALIDITY_RULE
OBSERVATION_COVERAGE_POLICY
~~~

Keep the boundary checksum, pre/post windows, seasonal rule, SCL validity rule and observation-coverage policy null or explicitly PENDING_STEP_2. Do not guess them.

The case must validate in specification mode and must be provably not runtime-ready.

## 7. Assessment-output schema

Create config/statement-templates.json as a versioned registry with exactly two entries:

~~~text
OBSERVATIONAL_COMPARISON_CORROBORATING_V1
OBSERVATIONAL_COMPARISON_CONTRADICTORY_V1
~~~

Each entry must contain:

- template_id;
- required_disposition;
- template_text;
- allowed_placeholders;
- mandatory_limitation_text.

Allow only these placeholders:

~~~text
project_id
pre_window
post_window
pre_value
post_value
qualification_policy_version
~~~

The corroborating template states only that the frozen post-window NDVI summary was higher than the frozen pre-window summary. The contradictory template states only that it was not higher. Both must end with this exact limitation:

> This bounded observation does not establish causality, carbon quantity, additionality, ACCU validity, project compliance or financial suitability.

No free-form completed statement is permitted. The validator must render the registered template from controlled fixture/runtime fields and require an exact match to supported_statement.

Create schemas/assessment-output.schema.json.

Require:

- schema_version;
- case_id;
- run_id;
- execution_status;
- evidence_disposition;
- reason_codes;
- quality_checks;
- observations;
- statement_template_id;
- supported_statement;
- must_not_claim;
- human_review_required;
- provenance_manifest_ref;
- qualification_policy_version.

Controlled statuses:

~~~text
COMPLETED
ABSTAINED
REFUSED
ERROR
~~~

Controlled dispositions:

~~~text
CORROBORATING
CONTRADICTORY
INCONCLUSIVE
null
~~~

Enforce:

quality_checks must contain exactly:

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

Each value is PASS, FAIL or NOT_RUN.

When observations is non-null, permit exactly:

~~~text
observation_status: COMPLETE | PARTIAL
aoi_total_pixels: non-negative integer or null
aoi_valid_pixels: non-negative integer or null
aoi_valid_fraction: number in [0, 1] or null
pre_window_ndvi_median: number in [-1, 1] or null
post_window_ndvi_median: number in [-1, 1] or null
~~~

Register exactly these non-null statement_template_id values:

~~~text
OBSERVATIONAL_COMPARISON_CORROBORATING_V1
OBSERVATIONAL_COMPARISON_CONTRADICTORY_V1
~~~

Then enforce:

1. COMPLETED requires CORROBORATING or CONTRADICTORY, observation_status COMPLETE, all five measurements non-null, every quality check PASS, the matching statement template, a non-empty bounded supported_statement and human_review_required false.
2. ABSTAINED requires INCONCLUSIVE, null observations or observation_status PARTIAL, null statement_template_id, null supported_statement, at least one insufficiency/conflict reason and human_review_required true. Partial observations are audit-only and cannot support a disposition.
3. REFUSED requires null disposition, null observations, null statement_template_id, null supported_statement and at least one AUTHORITY reason.
4. ERROR requires null disposition, null statement_template_id, null supported_statement and at least one SYSTEM reason.
5. INCONCLUSIVE is never valid with COMPLETED.
6. Every status requires a non-empty provenance_manifest_ref.
7. Every reason code and must_not_claim value must exist in its registry.
8. All required forbidden-inference codes are present, unique and ordered canonically.
9. Unknown controlled fields are rejected.

For complete observations, additionally enforce in the validator:

- aoi_total_pixels is greater than zero;
- 0 <= aoi_valid_pixels <= aoi_total_pixels;
- aoi_valid_fraction equals aoi_valid_pixels / aoi_total_pixels within absolute tolerance 1e-12;
- CORROBORATING requires post_window_ndvi_median > pre_window_ndvi_median;
- CONTRADICTORY requires post_window_ndvi_median <= pre_window_ndvi_median;
- statement_template_id, disposition, numeric comparison and rendered supported_statement agree.

Do not invent environmental measurements or represent fixtures as empirical outputs.

## 8. Provenance-manifest schema

Create schemas/provenance-manifest.schema.json.

Require:

- schema_version;
- manifest_id;
- run_id;
- case_id;
- runtime_mode;
- created_at_utc;
- source_records;
- artifact_records;
- transformation_records;
- policy_versions;
- software_environment;
- terminal_result.

Controlled runtime modes:

~~~text
SCHEMA_FIXTURE
EXECUTION
~~~

Each source record must include:

- source_id;
- canonical_uri;
- publisher;
- retrieved_at_utc;
- version_identifier;
- content_sha256;
- source_asset_ids.

Each artifact record must include:

- artifact_id;
- artifact_type;
- content_sha256;
- produced_by;
- media_type.

Each transformation record must include:

- sequence;
- transformation_id;
- implementation_version;
- parameter_set_ref;
- parameter_set_sha256;
- input_artifact_refs;
- output_artifact_refs;
- status;
- started_at_utc;
- finished_at_utc;
- reason_codes.

Transformation status values:

~~~text
COMPLETED
SKIPPED
FAILED
~~~

policy_versions must include versions for evidence sources, transformations, statement templates, forbidden inferences, reason codes and qualification policy.

software_environment must include code revision, Python version, package-lock SHA-256 and relevant package versions. Permit explicit fixture placeholders only when runtime_mode is SCHEMA_FIXTURE.

terminal_result must include assessment artifact reference, assessment SHA-256, execution status and reason codes.

Use one frozen canonicalisation rule for fixture and later runtime hashes:

~~~text
canonicalisation_id: CANONICAL_JSON_V1
encoding: UTF-8
JSON serialisation: sorted keys, separators=(',', ':'), ensure_ascii=false
~~~

Record canonicalisation_id in terminal_result. Hash the canonical assessment bytes, not a pretty-printed representation.

Enforce through schema and validator:

- every source and transformation ID belongs to its registry;
- transformation records follow the registered order and have contiguous sequence numbers;
- every artifact reference resolves within the manifest;
- every executed transformation has input/output lineage and parameter identity;
- SKIPPED or FAILED records include a registered reason code;
- canonical_uri cannot contain common expiring credential parameters such as sig, token, se, sp or sv;
- manifest run_id, case_id, status and reasons agree with its assessment fixture;
- the terminal assessment hash matches CANONICAL_JSON_V1;
- every assessment fixture, including REFUSED and ERROR, has a matching valid manifest;
- a COMPLETED assessment with incomplete provenance is invalid.

The provenance trail records machine actions, parameters, rules and hashes. Do not request, expose or store private chain-of-thought.

## 9. Validator

Create scripts/validate_step1_specs.py.

It must:

1. load schemas, registries and the case from repository-relative paths independent of caller working directory;
2. validate registry structure, uniqueness, exact required codes/templates and version consistency;
3. validate the case against the claim schema;
4. validate in-memory assessment-plus-provenance fixture pairs for COMPLETED, ABSTAINED, REFUSED and ERROR;
5. mark every fixture unambiguously as SCHEMA_FIXTURE and not empirical output;
6. enforce source membership, transformation membership/order and cross-registry references;
7. enforce assessment status/disposition invariants;
8. enforce assessment-to-manifest identity, status, reason and hash relationships;
9. verify that the EOP101132 case remains not runtime-ready;
10. print a concise success summary with versions and pending Step 2 fields; and
11. exit non-zero with a targeted error message.

Prefer standard Python plus jsonschema. Do not introduce Pydantic, a database or an application framework unless the repository already standardises on them.

## 10. Tests

Create tests/test_step1_specs.py with pytest.

Positive tests:

- all registries are unique, version-consistent and complete;
- the EOP101132 Step 1 case validates;
- the registered transformation sequence is exact;
- one valid linked assessment/manifest fixture exists for every execution status;
- all fixture provenance references, artifacts and hashes are internally consistent.

Negative tests must prove targeted rejection of at least:

- unknown evidence source;
- duplicate evidence source;
- missing, duplicate or extra source binding;
- frozen source binding without canonical_uri;
- pending source binding without a discovery_uri or with a fabricated canonical artifact URI;
- unknown transformation;
- reordered, deleted or duplicated transformation;
- missing required forbidden inference;
- unknown or duplicate reason code;
- runtime_ready true with pending Step 2 fields;
- ABSTAINED with CORROBORATING;
- REFUSED with a non-null disposition;
- COMPLETED with INCONCLUSIVE or null supported statement;
- COMPLETED with incomplete observations, a failed quality check or mismatched statement template;
- COMPLETED with inconsistent pixel arithmetic, fraction outside tolerance or disposition/NDVI comparison mismatch;
- completed supported_statement that is not an exact rendering of its registered template;
- ABSTAINED with a non-null statement template;
- ERROR with an evidence disposition;
- missing provenance reference;
- unknown source/transformation inside a manifest;
- unresolved artifact reference;
- non-contiguous transformation records;
- completed transformation without parameter or input/output lineage;
- COMPLETED assessment with incomplete provenance;
- assessment/manifest run ID, case ID, status, reasons or hash mismatch;
- signed/expiring URL used as canonical_uri;
- unexpected controlled property, including a reasoning_trace or chain_of_thought field.

Assert the intended failure and message, not merely that some exception occurred.

## Strict scope boundaries

Do not:

- download CER files;
- query Planetary Computer or another network API;
- choose temporal windows;
- choose SCL valid/invalid classes;
- choose an observation-coverage threshold;
- calculate AOI pixels or NDVI;
- call an LLM;
- build an agent, RAG system, vector database, API, CLI product, dashboard or UI;
- create a benchmark;
- claim an environmental result;
- claim ACCU validity, causality, additionality, carbon quantity, permanence, compliance, project integrity, greenwashing, investment quality or tokenisation readiness;
- store or request chain-of-thought;
- commit or push changes unless separately requested.

Fixtures may use clearly labelled urn:fixture identifiers and deterministic placeholder hashes. They must not use real-looking measurements or imply that evidence has been retrieved.

Use synthetic FIXTURE-* case IDs for the four assessment/manifest pairs. Do not attach a COMPLETED fixture to EOP101132-NDVI-001: the real EOP101132 case remains specification-only and has no empirical assessment in Step 1.

If an existing file conflicts with this prompt, preserve it and report the conflict rather than overwriting user work. Ask a question only if the conflict makes safe completion impossible.

## Done when

Step 1 is complete only when:

1. every required file exists;
2. every JSON file parses;
3. all schemas use Draft 2020-12 and reject unknown controlled properties;
4. registries contain exactly the required source/transformation/template/forbidden entries and at least the required reason codes;
5. the EOP101132 case validates in specification mode and is provably not runtime-ready;
6. all four assessment/manifest fixture pairs validate;
7. every required positive test passes;
8. every required negative test rejects the intended condition;
9. python scripts/validate_step1_specs.py exits successfully;
10. python -m pytest -q exits successfully;
11. the final diff contains no Step 2 or later implementation; and
12. a final self-review finds no mismatch among README terminology, schemas, registries, fixtures and tests.

Before finishing, inspect the diff for scope creep, schema loopholes and inconsistent enums. Report:

- files created or changed;
- key contract and invariant decisions;
- validation/test commands and exact results;
- fields deliberately left for Step 2;
- any unresolved blocker.

Stop after Step 1. Do not propose or begin Step 2 in the same run.

---

The prompt is deliberately low-freedom because evidence authority, abstention and provenance are safety-critical contracts. It specifies the outcome, context, boundaries and verification criteria while leaving implementation details to existing project conventions.
