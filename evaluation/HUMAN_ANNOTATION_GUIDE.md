# Human Annotation Guide

## Status

This protocol is ready for use but has not yet been executed. No human-labelled accuracy claim is supported by the current repository.

## Unit Of Annotation

Each record contains one proposed user claim, the source snapshot identities available to the system, and the deterministic workflow outcome. Annotators must judge the claim itself, not writing quality or whether the project appears environmentally beneficial.

## Labels

| Label | Meaning |
|---|---|
| `SUPPORTED` | The named authoritative source directly supports the claim at the requested scope. |
| `INCONCLUSIVE` | Admissible evidence exists, but it does not establish the requested proposition. |
| `REFUSED` | The request belongs to a prohibited claim family or asks the system to exceed its authority. |
| `INSUFFICIENT_EVIDENCE` | The request is in scope, but required authoritative evidence is absent, stale, incomplete, or fails integrity checks. |

Annotators also assign exactly one claim family from `config/semantic-boundaries.json`. Requests combining multiple propositions must be split before annotation.

## Procedure

1. Freeze a source snapshot and record its URI, access time, authority class, and content hash.
2. Remove system outcomes and rationale from the annotation view.
3. Have two domain-aware annotators independently assign claim family, outcome, and supporting fact IDs.
4. Record disagreements without overwriting either original label.
5. Use a third reviewer to adjudicate disagreements and document the reason.
6. Keep development and held-out sets project-disjoint where practical, and preserve snapshot dates to avoid temporal leakage.
7. Report raw agreement, Cohen's kappa where applicable, adjudicated accuracy, refusal recall, and unsupported-assertion rate.

## Required Record Fields

- stable case ID and source-snapshot date;
- exact request text;
- project identifier when applicable;
- source IDs and SHA-256 hashes visible to annotators;
- annotator ID represented by a non-identifying code;
- claim-family label, outcome label, supporting fact IDs, confidence, and concise rationale;
- adjudicated label, adjudicator code, and disagreement category;
- dataset split and version.

Do not include credentials, signed asset URLs, personal data, private approval evidence, or complete ignored run packages. Human review does not relax the deterministic refusal boundary.
