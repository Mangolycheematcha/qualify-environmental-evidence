# Master Prompt gap matrix

Reverified 2026-09-06. `COMPLETE` requires implementation plus executed evidence. `BLOCKED` names the exact external dependency; repository-authored fixtures never count as human or model behaviour.

| ID | Requirement | Evidence and denominator | Status |
|---|---|---|---|
| R1 | 5-10 real CER ACCU cases | 7 project records, 6 method types, source byte hashes, corpus manifest | `COMPLETE` |
| R2 | Real Safeguard/SMC record and entity boundary | Arcadia 2024-25 official CSV row; facility claim passes; ACCU transfer fails | `COMPLETE` |
| R3 | 60-100 partitioned cases and frozen held-out | 80 total across 22 groups, 53 development, 27 held-out; no group, template, subject or target-evidence overlap | `COMPLETE` |
| R4 | B0/B1/T1 and provider path | adapter and 27 matched B1/T1 packet pairs implemented; 0/27 live per arm | `BLOCKED_NO_CREDENTIAL_AND_MODEL_AUTHORIZATION` |
| R5 | Framework ADR | current official evidence for local state machine, LangGraph and Microsoft Agent Framework; re-evaluation triggers | `COMPLETE` |
| R6 | Retrieval and separate stores | controlled 25-query Top-1: lexical 22, TF-IDF 22, hybrid 23; no direct label text; separate evidence/checkpoint/preference semantics | `COMPLETE_FOR_CONTROLLED_POC` |
| R7 | Four E2E journeys and replay | 4/4; missing/stale/conflict included; pause/resume/replay bytes equal; replay adds no files or external actions | `COMPLETE` |
| R8 | Security evaluation | 7 executed threats, 3 explicitly N/A, 10 controls pass; exclusions named | `COMPLETE_FOR_LOCAL_POC` |
| R9 | Cold/warm performance | 8 cold, 40 warm, 200 per retrieval mode; environment and cache state recorded | `COMPLETE_FOR_LOCAL_POC` |
| R10 | Official-source stakeholder matrix | CER, ACCC, ASIC, APRA, Microsoft, DFCRC/RBA and ACM sources; interpretations separated | `COMPLETE` |
| R11 | README/deploy truthfulness | engineering, behavioural, H1, API and hosting states separately stated | `COMPLETE` |
| R12 | Full verification, hashes, diff, commits | 313 tests; generated checks; 336/336 frozen checksum entries; focused commits `9d12ff0`, `be3c39e`, `cd5e0a3`, `a33c252` plus this audit commit | `COMPLETE` |
| R13 | Preserve frozen Step 2B and no live EO | frozen policy/runtime/assessment/provenance unchanged; no live EO run | `COMPLETE` |
| R14 | H1 independent human evaluation | 0/27 independently labelled; guide exists | `BLOCKED_PENDING_INDEPENDENT_ANNOTATORS` |
| R15 | Live CER API and hosting | curated public pages/CSV only; no stable CER API contract; no service deployed | `BLOCKED_EXTERNAL_INTERFACE_AND_RELEASE_DECISIONS` |

Initial continuation commit was `a965ad4d76493d8db169ab6d7e64ca5ebe8bdac7`. Focused implementation commits are `9d12ff0`, `be3c39e`, and `cd5e0a3`; this matrix is recorded by the final local closure commit. No commit was pushed.
