# ADR 0001: Workflow framework

- Status: Accepted
- Decision date: 2026-09-05
- Scope: qualification workflow only; frozen Step 2B execution is excluded

## Context

The implemented workflow has three explicit stages: request validation, immutable evidence snapshotting, and deterministic qualification. It has no autonomous tool loop, multi-agent routing, or live EO action. The principal requirements are fail-closed semantics, byte-stable replay, reviewable checkpoints, minimal dependencies, and an optional model-provider boundary.

The decision below relies on repository-observable requirements and implementation evidence:

| Option | Repository-relevant surface | Fit | Cost and risk |
|---|---|---|---|
| Repository state machine | Python standard library plus existing JSON Schema dependency; explicit content-addressed evidence and strictly monotonic checkpoints | Direct fit for three deterministic stages | Project owns persistence and observability code |
| External graph/orchestration framework | Additional graph, persistence and framework lifecycle surface | Deferred because the implemented workflow has three explicit deterministic stages and no demonstrated requirement for an external orchestrator | New dependency, migration and checkpoint-format surface without measured evaluation gain |

Neither Microsoft Agent Framework nor LangGraph is installed in the repository environment. Their [official overview](https://learn.microsoft.com/en-us/agent-framework/overview/) and [official concepts](https://docs.langchain.com/oss/python/concepts/products) are informational references only; no version-specific, release-date, maintenance or hosting-status claim is relied upon by this ADR.

## Decision

Retain the lightweight deterministic state machine for this tranche. Keep the model provider behind a small protocol and keep evidence, checkpoints, and user preferences in separate stores. This is a positive architecture decision, not an assertion that either external framework is unsuitable in general.

The selected path is demonstrated by:

- content-addressed immutable evidence snapshots;
- monotonically appended, workflow-id-scoped checkpoints with idempotent equal-byte replay;
- pause after evidence snapshot, resume, and byte-equal completed-result replay;
- deterministic gates before any optional model call;
- no framework telemetry or hidden persistence.

## Re-evaluation triggers

Re-run this ADR with a measured spike when any two of these become requirements: concurrent branches, multiple agents, tool-call loops, durable distributed workers, hosted streaming sessions, framework-native telemetry, or human edits to in-flight graph state. Any future framework adoption requires a new ADR and must use the same held-out cases to report dependency, latency, replay, and security deltas. Do not migrate solely to claim framework adoption.

## Consequences

The current implementation is easier to audit and package, but the repository remains responsible for migration, locking, retention, authentication and production-grade storage. It is a local PoC, not a distributed production runtime.
