# Step 3 Offline Evaluation

## Current Status

The deterministic qualification workflow has an executable offline benchmark covering behavior, unsupported-inference controls, performance, and security. This is the first implemented part of Step 3. No LLM, model API, live CER refresh, live EO, external deployment, or human-labelled evaluation set was executed.

## Benchmark

`evaluation/qualification-benchmark.json` contains eight versioned cases:

- supported CER registry-fact restatement;
- the retained inconclusive frozen observation;
- the ACCU/SMC semantic boundary;
- refusals for ACCU quality, ACCU/SMC equivalence, compliance, financial action, and causality;
- a prompt-injection phrase embedded in a prohibited financial request.

The evaluator runs every request twice and compares canonical result bytes. It reports exact outcome rate, pre-retrieval refusal rate, deterministic replay rate, unsupported-assertion proxy rate, security-case pass rate, and p95 local latency.

## Verified Baseline

On 2026-09-05, the offline evaluator passed all configured thresholds:

| Measure | Result | Threshold |
|---|---:|---:|
| Exact outcome rate | 1.0 | 1.0 minimum |
| Forbidden-request refusal rate | 1.0 | 1.0 minimum |
| Deterministic replay rate | 1.0 | 1.0 minimum |
| Unsupported-assertion proxy rate | 0.0 | 0.0 maximum |
| Security-case pass rate | 1.0 | 1.0 minimum |
| p95 local latency | below 1,000 ms | 1,000 ms maximum |

The deterministic case-outcome digest is emitted by each evaluator run. Latency is machine-dependent and intentionally excluded from that digest.

## What This Does Not Establish

The unsupported-assertion metric is a proxy for a closed, deterministic rule system. It does not measure an LLM hallucination rate, natural-language recall, model calibration, robustness across unseen projects, or analyst decision quality.

## Pending Evaluation Work

- Execute the protocol in `evaluation/HUMAN_ANNOTATION_GUIDE.md` and perform inter-annotator review on a broader claim set.
- A held-out multi-project CER dataset with time-aware source snapshots.
- Model-assisted request classification, tested separately from the deterministic authority gate.
- Real API and data-refresh tests against an explicitly documented CER publication interface.
- Deployment security testing, dependency scanning, and service-level performance testing.
- Specialist review of remote-sensing, ACCU Scheme, Safeguard, legal, and regulated-finance wording.

These items are pending, not implied by the current PASS result.
