# Agentic AI Track B alignment

## Scope

This document maps the repository to the Track B Agent Builder capstone rubric in
[`WenyuChiou/awesome-agentic-ai-zh`](https://github.com/WenyuChiou/awesome-agentic-ai-zh/blob/8f23ef8c1e77ba673a0179ca5497b9180c83f033/CAPSTONE.zh-Hans.md),
reviewed at upstream commit `8f23ef8c1e77ba673a0179ca5497b9180c83f033`.
It is a compatibility assessment, not an upstream endorsement or a claim that every
learning-stage prerequisite has been completed.

The repository follows the capstone's RAG-system option. It does not add a multi-agent
framework merely to satisfy an architectural label. The implemented system is a bounded,
offline evidence-retrieval and qualification agent whose authority ceiling requires it to
qualify, abstain, refuse, pause, resume, or replay without making financial or environmental-
integrity decisions.

## Runtime map

| Agentic component | Repository implementation | Inspectable evidence |
|---|---|---|
| Input contract | Schema-validated bounded question and claim family | `schemas/qualification-request.schema.json` |
| Agent loop | Bounded observe-decide-act-verify controller with an explicit step budget | `scripts/agent_runtime.py` |
| Tool use | Deterministic retrieval, schema validation, content-addressed storage and qualification | `scripts/qualification_workflow.py`; `scripts/retrieval_memory.py` |
| Memory / RAG | Immutable evidence snapshots plus lexical, local TF-IDF and hybrid ranking | `scripts/retrieval_memory.py`; `evaluation/retrieval-benchmark.json` |
| Policy and authority | Allowlisted sources, claim families, forbidden conclusions and human-review requirement | `config/semantic-boundaries.json` |
| Checkpoint / recovery | Append-only checkpoints bound to request and evidence hashes | `scripts/qualification_session.py` |
| Observability | Schema-validated execution receipt recording actions, checkpoint hashes, evidence hashes, stop reason and result hash | `schemas/agent-execution-receipt.schema.json` |
| Evaluation | Versioned development and group-held-out cases, retrieval comparison, security cases, E2E journeys and runtime recovery checks | `docs/STEP3_EVALUATION.md`; `evaluation/results/` |
| Interface | Offline CLI returning human-readable or canonical JSON output | `scripts/agent_runtime.py --help` |

## Capstone gap matrix

| Track B requirement | Status | Evidence | Remaining limitation |
|---|---|---|---|
| Concrete problem | **Met** | The system decides whether bounded evidence is sufficient and authorised before a stronger claim is made. | One frozen observational case does not establish general external validity. |
| RAG or multi-agent architecture | **Met — RAG path** | Ten local evidence documents, deterministic retrieval and source-linked results. | No continuously refreshed CER integration and no external vector service. |
| Tool use | **Met** | Retrieval, schema validation, provenance checks, checkpoint storage and qualification are invoked as bounded tools. | Tools are local and offline by design. |
| External interface | **Met — CLI** | Qualification and agent-runtime commands emit JSON and stable exit codes. | No hosted API or graphical interface. |
| Versioned eval suite | **Exceeded for engineering evidence** | 80 rows across 22 semantic groups: 53 development and 27 group-held-out; frozen held-out inventory. | Repository-authored expectations are not independent expert labels. |
| Baseline and regression | **Met** | Retrieval modes are compared; exact outcomes and byte-deterministic replay are checked in CI. | B0/B1/T1 model arms remain `NOT_EXECUTED`. |
| Failure-mode analysis | **Met** | Missing, stale, conflicting, entity-mismatch, forbidden-claim, tamper and resume-mismatch paths fail closed. | Live transport and external-service failures are outside this offline runtime. |
| Recovery and idempotency | **Met** | Step-budget pause, hash-bound resume and completed-session replay create no new evidence or checkpoint files. | Recovery of ignored raw live-run assets requires the separate private-source archive described below. |
| Architecture explanation | **Met** | This runtime map and the qualification workflow documentation identify components and boundaries. | The system intentionally avoids a general-purpose agent framework. |
| Reflection / next limitation | **Met here** | The design choice and next evidence gap are recorded below. | Independent H1 labels and authorised model arms remain future work. |

## Recovery and source-preservation boundary

Git is the durable baseline for code, schemas, curated factual extracts, manifests and
evaluation results. Raw HTTP responses, metadata blobs, rasters, cached arrays and complete
live-run packages remain outside the public repository until licensing and disclosure review.
For each retained private source package, preserve at least:

- canonical source URI and access time;
- retrieval method and original filename;
- byte count and SHA-256 digest;
- licence and redistribution status;
- derived artifact identifiers and the related Git commit;
- an immutable copy in a second storage location.

An execution receipt proves which curated evidence snapshots and checkpoints a local agent
used. It does not claim that excluded source bytes are publicly redistributable or that an
unavailable private archive has been recovered.

## Reproduce the bounded agent path

Run a three-step offline session:

```text
python scripts/agent_runtime.py examples/qualification/eop101132-request.json --state-root runs/agent-demo --workflow-id AGENT-DEMO --max-steps 3 --json
```

Run the same command again to verify idempotent replay. The second receipt must report
`REPLAYED`, preserve the result hash and create no new checkpoint or evidence file.

Run the committed runtime evaluation:

```text
python scripts/evaluate_agent_runtime.py --check --json
```

## Design reflection

The repository already contained the substantive control system before it had an explicit
"agent runtime" label. Adding a framework would have increased dependencies and enlarged the
attack and reproducibility surface without improving the bounded decision. The compatibility
layer therefore exposes the existing state transitions as a budgeted loop and records a
machine-checkable receipt. The next high-value evidence is not more orchestration: it is an
independently governed human-label set or an explicitly authorised model comparison using the
already frozen held-out packet.
