# Step 3 evaluation

## Status and denominators

Executed on 2026-09-05. All results below are local PoC evidence, not general model or regulatory assurance.

| Layer | Denominator | Result | Meaning |
|---|---:|---|---|
| Deterministic qualification | 80 cases: 53 development, 27 group-held-out | 80/80 exact; 80/80 byte-deterministic replay | Engineering behaviour of the rule workflow |
| Sources | 29 real-source, 23 synthetic counterfactual, 28 adversarial | Reported separately in the result artifact | Synthetic and adversarial rows are not prevalence estimates |
| Retrieval | 25 held-out engineering-relevance queries | lexical, local TF-IDF and hybrid each 25/25 Top-1 | No measured reason to add external vector infrastructure |
| End-to-end journeys | 4 | 4/4 pass, including missing/stale/conflict and resume/replay | Offline workflow integration only |
| Security | 8 executed, 2 not-applicable attack surfaces | 10/10 recorded controls pass | Bounded local threat evaluation, not a penetration test |
| Performance | 8 cold processes, 40 warm workflow calls, 200 calls per retrieval mode | See `evaluation/results/performance.json` | Machine-specific local latency |
| B0/B1/T1 model arms | 27 planned per arm | 0/27 executed per arm | Blocked: no configured API credential; adapter exists |
| H1 independent human labels | 27 planned | 0/27 | Blocked pending independent annotators; repository labels are not human gold |

`evaluation/qualification-benchmark.json` is generated and frozen by group. Its engineering labels cover seven real ACCU projects, one Safeguard facility-period record, ACCU/SMC definitions, the frozen observation, missing/stale/entity-mismatch/policy cases, semantic-transfer attempts and forbidden requests. `evaluation/held-out-freeze.json` binds the held-out case IDs and canonical bytes.

## Artifacts

- `qualification-evaluation.json`: exact outcomes, denominators, split rates, per-case hashes and latency.
- `retrieval-comparison.json`: lexical/vector/hybrid ranking comparison and decision.
- `e2e-demonstrations.json`: four journeys and resumable byte-equal replay.
- `security-evaluation.json`: threat/control matrix and excluded classes.
- `performance.json`: environment, cache state, sample counts and p50/p95.
- `model-comparison-status.json`: B0/B1/T1 design, matched B1/T1 packet hashes, adapter readiness and exact blockers.

## Interpretation limits

The 80-case labels are repository engineering expectations, not independent annotations. The unsupported-assertion metric is a deterministic proxy, not an LLM hallucination rate. Perfect scores on generated cases do not establish external validity. B0/B1/T1 must use one selected model and identical settings, with matched evidence bytes for B1/T1, after a human explicitly authorizes API cost and data transfer. H1 requires independent annotators following `evaluation/HUMAN_ANNOTATION_GUIDE.md`.
