# Astra Handoff Ledger

Owner: Astra (SOL audit authority). This file is rewritten by Astra at each phase boundary.

## Current Git State

- Baseline HEAD: `a33c252cb1df79029dd946354046c0bcc2bc8d4d`
- Branch: `main`
- Worktree: dirty with the authorised publication-audit corrective pass; no commit has yet been created.
- Remote actions: none. No push, release, tag, issue, visibility change, deployment, paid API, live EO, CER runtime, STAC, signed-raster, or GDAL operation was performed.

## Phase States And Evidence

| Phase | State | Evidence path |
|---|---|---|
| Git baseline and four-commit lineage | Astra-audited complete | `docs/IMPLEMENTATION_VERIFICATION.md` (`Commit attribution`) |
| CER corpus count, six method categories, source traceability | Astra-audited complete | `data/cer/corpus-manifest.json`; `docs/IMPLEMENTATION_VERIFICATION.md` |
| Evaluation split and denominator correction | Implemented; final regeneration/verification pending | `evaluation/qualification-benchmark.json`; `evaluation/results/qualification-evaluation.json` |
| Retrieval leakage correction and metric recalculation | Implemented; latest result regeneration pending | `evaluation/retrieval-benchmark.json`; `scripts/evaluate_retrieval.py` |
| E2E, state-store, security, and performance corrections | Implemented and focused/full tests passed before the latest retrieval-only edit | `evaluation/results/e2e-demonstrations.json`; `evaluation/results/security-evaluation.json`; `evaluation/results/performance.json` |
| Frozen V3/V4 integrity | Astra-audited complete: V4 336/336; V3/V4 hashes match | `docs/IMPLEMENTATION_VERIFICATION.md` (`Frozen identities`) |
| Publication scans | Astra-audited complete for content; candidate-byte count needs one final refresh | `docs/IMPLEMENTATION_VERIFICATION.md` |
| Final corrective commit | Pending Luna implementation and Astra acceptance | Git state |

## Exact Next Command

```powershell
& '.\.venv\Scripts\python.exe' scripts/evaluate_retrieval.py --write --json
```

After that, Luna must synchronise the existing 46-resource skill package, run the documented offline verification, refresh only mechanically derived audit numbers, inspect the diff, and create the single local commit `Audit evaluation and publication claims`. Luna must not choose or alter any threshold or status label.

## Open Escalations Awaiting Astra Decision

- Public redistribution rights remain an accountable-human decision: `docs/DATA_AND_ARTIFACT_LICENSING.md` (`Remaining Release Decisions`) and `PUBLIC_RELEASE_CHECKLIST.md`.
- Older reachable commits expose `e28581919@gmail.com`; history rewrite is prohibited. Evidence: `docs/IMPLEMENTATION_VERIFICATION.md` (`External blockers`).
- GitHub settings and explicit publication approval remain human-controlled: `PUBLIC_RELEASE_CHECKLIST.md`.

## Unfixed Red-Team Findings And Disclosed Limits

- The 25-query retrieval set is repository-authored after the corpus, uses structured subject filters, and includes one single-candidate query. It is not independent human or comparative-model evidence.
- The 80 rows are parameterised deterministic regression evidence across 22 semantic groups, not 80 independent expert-labelled scenarios.
- B0/B1/T1 remain 0/27 per arm; H1 remains 0/27; no public hosting or deployment has occurred.
- The frozen Step 2B classification remains `SCIENCE_VALID - GOVERNANCE_LIMITATION - NO_RERUN`; no fully canonical claim is allowed.

## Must Not Be Redone

- Do not rerun live EO or mutate any frozen run. The retained scientific result and its 336-entry checksum package were already independently verified and are immutable.
- Do not refetch CER or framework sources during this pass. Astra already compared all nine cited CER response byte counts and hashes and checked the current official framework documentation.
- Do not revisit framework selection, tau, scientific thresholds, policy semantics, schema versions, or historical run classification; none is in the approved implementation scope.
