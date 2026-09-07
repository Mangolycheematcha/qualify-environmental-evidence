# Glossary

These terms describe how this repository uses evidence and controls. They are not general legal, regulatory, or scientific definitions.

## Step 2B

The bounded Earth-observation vertical slice that acquired permitted Sentinel-2 evidence, applied the frozen decision policy, and produced the retained assessment. It is one scientific qualification case, not project validation.

## V3 / V4

Historical versions of the Step 2B policy and runtime contract. V4 identifies the version used by the retained run; it is not a general quality grade or a claim that the run is free of disclosed governance limitations.

## AOI

Area of interest: the contract-bound geometry within which eligible pixels are evaluated. Its bounds, target grid, and rasterized mask are controlled inputs to the comparison.

## SCL

Sentinel-2 Scene Classification Layer. The workflow uses allowed SCL classes to exclude unsuitable observations before compositing and calculating NDVI.

## Tau (`tau`)

The magnitude of the operational indifference boundary, frozen at `0.03` before observation for the demonstrated case. It is a policy threshold, not a confidence interval or scientific detection limit.

## Joint Coverage

The fraction of AOI pixels eligible in both PRE and POST composites. The workflow checks this shared footprint before comparing the two windows.

## Authority Ceiling

A deterministic limit on what the system may conclude from the admitted evidence. When evidence supports only a narrower statement, the workflow must not produce a stronger one.

## Abstention

A structured decision to decline a stronger conclusion when evidence, coverage, authority, or policy conditions are insufficient. In the demonstrated case, the observed NDVI change remained inside the pre-observation operational indifference band.

## Claim Contract

A versioned specification of the question, subject, evidence sources, transformations, thresholds, allowed statements, forbidden inferences, and review requirements for one qualification task.

## Provenance

Records connecting source identity, retrieved evidence, transformations, hashes, decisions, and generated artifacts. Provenance supports traceability but does not by itself establish scientific truth or regulatory assurance.

## Behavioural Evaluation

A planned comparison involving a selected model or independent human reviewers. It is distinct from the completed deterministic regression and retrieval evaluations and is currently `NOT_EXECUTED`.

## B0 / B1 / T1 / H1

B0 is the question-only model arm; B1 supplies a matched evidence packet; T1 adds the deterministic authority gate to that matched packet; H1 is independent human review. Each has 27 planned cases and 0 completed cases, and none may run without separate authorization.
