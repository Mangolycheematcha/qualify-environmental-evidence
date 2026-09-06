# Implementation verification

Publication audit date: 2026-09-06. Branch: `main`. Audit initial HEAD: `a33c252cb1df79029dd946354046c0bcc2bc8d4d`.

## Executed verification

- Full test suite: 317 passed with pytest caching disabled after adding publication-closure invariants and updating two stale README expectations.
- Corpus generator check: 9 documents, including 7 ACCU projects and 1 Safeguard facility-period record.
- Independent source check: all 9 cited official CER responses matched their recorded source byte counts and SHA-256 values on 2026-09-06; raw responses were not saved.
- Evaluation generator check: 80 rows across 22 groups, 53 development and 27 held out, with no group, template-family, subject-partition or target-evidence overlap.
- Retrieval generator check: 25 repository-authored controlled queries; fact-text-only ranking; no expected fact ID, project ID or project name in query text.
- Retrieval Top-1: lexical 22/25, local TF-IDF 22/25, hybrid 23/25. One query has only one filtered candidate. The 1/25 hybrid gain is below a 5% materiality threshold added during this audit, not a preregistered research threshold.
- E2E: 4/4 journeys passed; completed replay was byte-equal and left checkpoint/evidence file counts unchanged at 3/10.
- Security: 7 executed controls and 3 explicitly not-applicable surfaces; all 10 records passed. No penetration-test claim is made.
- Performance: raw samples are recorded for 8 cold, 40 warm, and 200 calls per retrieval mode; p50 uses `statistics.median` and p95 uses nearest-rank ceiling.
- Skill package check: 46 managed resources, no drift.
- Frozen policy and runtime-spec builders: PASS.
- Strict JSON finite-value parse: 85 repository JSON files; no NaN or Infinity numeric value.
- Frozen run checksum manifest: 336/336 generated files, 0 missing, 0 extra, 0 mismatched.
- Candidate baseline scan: 197 files, with no secret/path failures, binaries, symlinks, executables, or files over 10 MB; only three clearly synthetic signed-URL fixtures under `tests/` were identified.
- Full-history content scan: 385 Git objects, no secret/path pattern hit, binary blob, or blob over 10 MB.
- No live EO, STAC, signed-raster, GDAL, model API or approval-consumption access occurred. GitHub's public read-only Issue endpoint was used to verify Issue #3; no credential or raw response was retained.

## Frozen identities

| Artifact | Independently calculated SHA-256 |
|---|---|
| V4 policy | `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd` |
| V4 runtime specification | `e7671981e1edbe9b17d2198d68bd873750c40c9489923c403790c34ae9059b51` |
| V4 assessment | `759a173dbdbe2bee8a5689996ae38d226fdc7601118e4c60364a3b9f8561c01f` |
| V4 provenance | `b42cb95d1fa8aeeae7aff758cc18b41986e3d376a758e1a498218fd88bd2471c` |
| V4 checksum manifest | `34d7cfd94b179f413f93d2a93c1ee5b4fc83bd7d4832089f6af743d497a570ac` |

## Change classification

| Class | Changed surface |
|---|---|
| Runtime implementation | Retrieval ranking text, monotonic checkpoint enforcement, bounded Safeguard statement, evaluators, and evidence reports |
| Policy/schema/registry | No frozen policy, runtime specification, schema, or semantic registry changed |
| Empirical/public input | No curated factual value or source hash changed; no raw third-party response added |
| Evaluation output | Partitioned 80-row benchmark; controlled retrieval, E2E, security, performance and qualification reports regenerated |
| Test expectation only | Leakage mutation tests, store-sequencing tests, recorded-sample recomputation, stable-time approval fixture, and README expectations |
| Documentation only | Retrieval/evaluation limitations, storage semantics, Safeguard evidence boundary, framework source versions, licensing notice and reproduction state |
| Packaging/CI | Existing 46-resource skill package resynchronised; no workflow expansion |

## External blockers

- B0/B1/T1 behavioural evaluation: `NOT_EXECUTED`; 27 held-out cases are planned and 0 are completed for each arm. No provider credential or model/API cost was authorized. The adapter and matched B1/T1 packet design are implemented; fixture output is not behavioural evidence.
- H1 independent evaluation: `NOT_EXECUTED`; 27 labels are planned and 0 are completed. Repository expectations are engineering labels, not human gold.
- CER API: no stable authenticated API contract was identified or exercised; inputs are exact public pages and one raw CSV publication.
- Hosting: the GitHub repository is public, but no authenticated service, hosted API, cloud application, release, DOI, or production controls were exercised.

## Publication authorization

- Rights: in [GitHub Issue #3](https://github.com/Mangolycheematcha/qualify-environmental-evidence/issues/3), the repository owner confirmed review of tracked original material and authority, to the best of their knowledge, to release owner-controlled code, schemas, registries, tests, documentation and original diagrams under Apache-2.0. The local [authorization record](PUBLIC_RELEASE_AUTHORIZATION.md) preserves the verified metadata and hashes.
- Third-party boundary: the same authorization explicitly retains the exclusions in `THIRD_PARTY_NOTICES.md` and `docs/DATA_AND_ARTIFACT_LICENSING.md`; it is not a legal guarantee or relicensing of third-party material.
- Historical identity: the four commits from `9d12ff0` through `a33c252` use the configured noreply identity. The owner explicitly accepted public disclosure of `e28581919@gmail.com` in older reachable history and prohibited history rewriting.
- Release authority: the owner approved continued public availability of implementation baseline `47bbeaf5375c365eee758bbf8f6eda9f0c217dbe` and a subsequent documentation-only publication-closure commit. Step 3 behavioural evaluation, live EO, approval consumption, release/DOI creation and fully canonical claims remain outside scope.

## Commit attribution

- `9d12ff0`: deterministic qualification baseline; parent `a965ad4`.
- `be3c39e`: multi-entity corpus, workflow and evaluation implementation; parent `9d12ff0`.
- `cd5e0a3`: package, CI, architecture and release-status documentation; parent `be3c39e`.
- `a33c252`: master-prompt verification status; parent `cd5e0a3`.
- `47bbeaf`: publication audit and evaluation-claim corrections; parent `a33c252`.

The four implementation-tranche commits from `9d12ff0` through `a33c252`, plus audit commit `47bbeaf`, use `Hio Wai Hoi <288892596+Mangolycheematcha@users.noreply.github.com>` and form the expected linear chain. Earlier history contains the owner-accepted personal email noted above. The publication-closure commit is resolved mechanically with `git log -1 --format=%H -- HANDOFF.md` after creation rather than predicted inside the ledger.
