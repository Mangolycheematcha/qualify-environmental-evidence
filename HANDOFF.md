# Handoff Ledger

This ledger is updated by the implementation agent before commit. It records stable audited baselines and resolution commands, not a prediction of the commit that contains the ledger. Read-only auditors do not modify it.

## Stable Git Anchors

- `implementation_baseline_commit`: `47bbeaf5375c365eee758bbf8f6eda9f0c217dbe`
- `audit_target_commit`: `47bbeaf5375c365eee758bbf8f6eda9f0c217dbe`
- `handoff_parent_commit`: `47bbeaf5375c365eee758bbf8f6eda9f0c217dbe`
- `handoff_document_commit`: resolve with `git log -1 --format=%H -- HANDOFF.md`
- `working_tree_at_handoff_creation`: publication-closure files modified from the clean implementation baseline; these changes are intended to be committed together as `Close public-release governance findings`
- `next_authorised_phase`: `STEP_3_AUTHORISED_BUT_NOT_STARTED`

The publication authorization in GitHub Issue #3 does not itself authorize Step 3 behavioural execution. B0/B1/T1 and H1 remain `NOT_EXECUTED` and require their separately documented prerequisites.

## Publication Closure Evidence

| Item | State | Evidence |
|---|---|---|
| Owner rights attestation and Apache-2.0 scope | Confirmed for original owner-controlled material | `docs/PUBLIC_RELEASE_AUTHORIZATION.md`; GitHub Issue #3 |
| Third-party exclusions | Retained | `THIRD_PARTY_NOTICES.md`; `docs/DATA_AND_ARTIFACT_LICENSING.md` |
| Historical Gmail disclosure | Accepted by owner; no history rewrite | `docs/PUBLIC_RELEASE_AUTHORIZATION.md`; GitHub Issue #3 |
| Continued public availability | Approved by owner | `docs/PUBLIC_RELEASE_AUTHORIZATION.md`; GitHub Issue #3 |
| Framework ADR artifact-only finding | Resolved prospectively by removing version/date reliance | `docs/adr/0001-workflow-framework.md` |
| Frozen Step 2B status | `SCIENCE_VALID - GOVERNANCE_LIMITATION - NO_RERUN` | `docs/STEP2B_V4_CLOSURE.md` |

## Mixed-Responsibility Audit History

The following corrections predate the separated publication-closure protocol and retain their historical classification:

- Evaluation denominators, semantic groups, partition isolation, retrieval corrections, checkpoint/replay controls, performance calculations, security coverage, Safeguard wording, documentation reconciliation and time-dependent test stabilization: **applied under mixed responsibility, re-verified**.
- The former framework ADR version/date assertions were **applied under mixed responsibility, not independently verifiable**. That historical finding is not rewritten; this closure removes reliance on those assertions for future publication.

## Resolution Commands

After the publication-closure commit, resolve the document commit and audit target without editing this file:

```powershell
git log -1 --format=%H -- HANDOFF.md
git status --short
git show --stat --oneline HEAD
```

The first command identifies the commit containing this ledger. Phase 2 must audit that commit and leave the worktree unchanged.

## Remaining Limits

- The 80 rows remain repository-authored deterministic regression evidence, not model accuracy or expert validation.
- Retrieval remains a small repository-authored controlled set with one single-candidate query.
- B0/B1/T1 and H1 are `NOT_EXECUTED`; each has 27 planned cases and 0 completed cases.
- No stable live CER API, hosted application, software release, DOI or production control environment has been exercised.
- The owner-operated review of GitHub Pages, Actions, collaborators and secrets is not performed by this repository commit.

## Must Not Be Redone

- Do not rerun live EO, modify a frozen run, consume approval, or recalculate the scientific result.
- Do not change tau, thresholds, policy semantics, schemas, or historical classifications in this closure.
- Do not rewrite Git history to remove the accepted historical email disclosure.
- Do not execute B0/B1/T1/H1 or call a model API as part of publication closure.
