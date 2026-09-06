# Deployment And Publication

## Supported Today

The supported deployment is a local, offline Python CLI or a copied Codex skill directory. It requires Python 3.10+ and `jsonschema>=4.18,<5`.

Repository CLI:

```text
python scripts/qualification_workflow.py examples/qualification/eop101132-request.json --json
python scripts/evaluate_qualification.py --json
python scripts/run_e2e_demos.py --json
```

Packaged skill:

```text
python scripts/package_skill.py
python scripts/package_skill.py --check
python skill/qualify-environmental-evidence/scripts/qualification_workflow.py skill/qualify-environmental-evidence/examples/qualification/eop101132-request.json --json
```

The package manifest binds every managed resource by SHA-256. The standalone package test copies only the skill directory to a temporary location and runs both the workflow and evaluator there.

## CI

`.github/workflows/offline-ci.yml` grants `contents: read`, pins third-party actions to commit SHAs, supplies no secrets, blocks ordinary proxy access during validation, and runs no live EO, CER, STAC, signing, raster, approval, release, or deployment command.

## Not Deployed

The source repository is publicly available. This does not constitute a versioned software release, hosted service, production deployment, operational approval, package publication, tag, or DOI.

- No hosted API, web UI, database, vector store, cloud service, container image, package publication, GitHub release, tag, or DOI exists.
- No stable live CER API contract has been adopted or tested. Current CER inputs are source-attributed curated snapshots from seven projects, one Safeguard row and unit definitions.
- No background refresh, scheduler, webhook, user authentication, tenancy, or retention policy exists.
- No model or LLM is in the decision path. An OpenAI Responses provider adapter exists but has not made a live call in this tranche.

The repository is deployment-prepared only in the sense that offline entry points, dependency bounds, CI, artifact manifests, security notes and production gates are documented. It is not deployable as an authenticated multi-user service and no hosting target has been selected.

## Production Gate

Before any service deployment, define and test source-refresh semantics, immutable snapshot retention, authentication, authorization, rate limits, dependency and image provenance, secrets handling, observability without sensitive payloads, incident response, data licensing, privacy, rollback, and human escalation. A deployed model must remain outside the deterministic authority and evidence gates until separately evaluated.

Continued public source-repository availability is authorized in GitHub Issue #3 and tracked in `PUBLIC_RELEASE_CHECKLIST.md`. Passing offline CI does not authorize deployment, package or software release, a tag, a DOI, or operational approval.
