# Implementation verification

Publication audit date: 2026-09-06. Branch: `main`. Audit initial HEAD: `a33c252cb1df79029dd946354046c0bcc2bc8d4d`.

## Executed verification

- Full test suite: 313 passed in 58.53 seconds after correcting one time-dependent approval fixture and two stale README expectations.
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
- Candidate baseline scan: 195 files, 2,124,421 bytes, no secret/path failures, binaries, symlinks, executables, or files over 10 MB; only three clearly synthetic signed-URL fixtures under `tests/` were identified.
- Full-history content scan: 385 Git objects, no secret/path pattern hit, binary blob, or blob over 10 MB.
- No live EO, STAC, signed-raster or GDAL access occurred. Public CER pages/CSV and official framework documentation were read only to verify citations and hashes.

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

- B0/B1/T1: 0/27 live cases per arm. No provider credential is configured and no model/API cost was authorized. The adapter and matched B1/T1 packet design are implemented; fixture output is not counted as behavioural evidence.
- H1: 0/27 independent labels. Repository expectations are engineering labels, not human gold.
- CER API: no stable authenticated API contract was identified or exercised; inputs are exact public pages and one raw CSV publication.
- Hosting/publication: no authenticated service, cloud target, push, release, visibility change or production controls were authorized.
- Publication rights: ownership and redistribution rights for every tracked artifact still require accountable human confirmation.
- Git identity: the four commits from `9d12ff0` through `a33c252` use the configured noreply identity, but older reachable commits include `e28581919@gmail.com`. Rewriting history was prohibited; the owner must accept that disclosure or choose a separate publication process.
- Release authority: GitHub settings and third-party terms still require review, and no explicit approval to publish or change visibility has been given.

## Commit attribution

- `9d12ff0`: deterministic qualification baseline; parent `a965ad4`.
- `be3c39e`: multi-entity corpus, workflow and evaluation implementation; parent `9d12ff0`.
- `cd5e0a3`: package, CI, architecture and release-status documentation; parent `be3c39e`.
- `a33c252`: master-prompt verification status; parent `cd5e0a3`.

Those four commits use `Hio Wai Hoi <288892596+Mangolycheematcha@users.noreply.github.com>` and form the expected linear chain. Earlier history contains the personal email noted above. No push was performed.
