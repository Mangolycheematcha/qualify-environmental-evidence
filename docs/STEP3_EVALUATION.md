# Step 3 evaluation

## Status and denominators

Originally executed on 2026-09-05 and independently regenerated during the 2026-09-06 publication audit. All results below are local PoC evidence, not general model or regulatory assurance.

| Layer | Denominator | Result | Meaning |
|---|---:|---|---|
| Deterministic qualification | 80 rows across 22 semantic groups: 53 development, 27 held out | 80/80 exact; 80/80 byte-deterministic replay | Engineering behaviour of the rule workflow |
| Sources | 29 real-source, 23 synthetic counterfactual, 28 adversarial | Reported separately in the result artifact | Synthetic and adversarial rows are not prevalence estimates |
| Retrieval | 25 repository-authored controlled queries | lexical 22/25, local TF-IDF 22/25, hybrid 23/25 Top-1; all 24/25 Recall@3 | Hybrid gain 1/25 is below the recorded 5% materiality threshold; no external vector infrastructure added |
| End-to-end journeys | 4 | 4/4 pass, including missing/stale/conflict and resume/replay | Offline workflow integration only |
| Security | 7 executed, 3 not-applicable attack surfaces | 10/10 recorded controls pass | Bounded local threat evaluation, not a penetration test |
| Performance | 8 cold processes, 40 warm workflow calls, 200 calls per retrieval mode | Raw samples plus recomputable p50/p95 in `evaluation/results/performance.json` | Machine-specific local latency; cache conditions recorded |
| B0/B1/T1 model arms | 27 planned per arm | `NOT_EXECUTED`; 0 completed per arm | No configured API credential or execution authorization; adapter exists |
| H1 independent human labels | 27 planned | `NOT_EXECUTED`; 0 completed | Independent annotation has not started; repository labels are not human gold |

`evaluation/qualification-benchmark.json` is generated with no development/held-out overlap in group ID, template family, subject partition key, or target evidence document. Its engineering labels cover seven real ACCU projects, one Safeguard facility-period record, ACCU/SMC definitions, the frozen observation, missing/stale/entity-mismatch/policy cases, semantic-transfer attempts and forbidden requests. `evaluation/held-out-freeze.json` binds the held-out case IDs, partition inventory and canonical bytes.

## Artifacts

- `qualification-evaluation.json`: exact outcomes, denominators, split rates, per-case hashes and latency.
- `retrieval-comparison.json`: lexical/vector/hybrid ranking comparison and decision.
- `e2e-demonstrations.json`: four journeys and resumable byte-equal replay.
- `security-evaluation.json`: threat/control matrix and excluded classes.
- `performance.json`: environment, cache state, raw samples, statistic definitions and p50/p95.
- `model-comparison-status.json`: B0/B1/T1 design, matched B1/T1 packet hashes, adapter readiness and exact blockers.

## Interpretation limits

The 80 rows are parameterised regression cases across 22 semantic groups; they are repository engineering expectations, not 80 independent substantive scenarios or expert annotations. The unsupported-assertion metric is a deterministic proxy, not an LLM hallucination rate, and 80/80 does not establish external validity. Retrieval ranks fact text only, with subject type and ID used as disclosed metadata filters; expected fact IDs, project IDs and project names are absent from query text. The retrieval queries were authored by the repository after the corpus and are not an independent human set; one query has only one candidate after its subject filter. The 5% materiality threshold was added during the 2026-09-06 audit and was not preregistered, so retaining lexical retrieval is a scoped engineering choice rather than comparative-model evidence. B0/B1/T1 remain `NOT_EXECUTED` and must use one selected model and identical settings, with matched evidence bytes for B1/T1, after a human explicitly authorizes API cost and data transfer. H1 remains `NOT_EXECUTED` and requires independent annotators following `evaluation/HUMAN_ANNOTATION_GUIDE.md`.
