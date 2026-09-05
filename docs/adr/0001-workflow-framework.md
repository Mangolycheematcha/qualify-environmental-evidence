# ADR 0001: Workflow framework

- Status: Accepted
- Decision date: 2026-09-05
- Scope: qualification workflow only; frozen Step 2B execution is excluded

## Context

The implemented workflow has three explicit stages: request validation, immutable evidence snapshotting, and deterministic qualification. It has no autonomous tool loop, multi-agent routing, or live EO action. The principal requirements are fail-closed semantics, byte-stable replay, reviewable checkpoints, minimal dependencies, and an optional model-provider boundary.

Current evidence was reviewed on 2026-09-05:

| Option | Current official evidence | Fit | Cost and risk |
|---|---|---|---|
| Repository state machine | Python standard library plus existing JSON Schema dependency; explicit content-addressed evidence and append-only checkpoints | Direct fit for three deterministic stages | Project owns persistence and observability code |
| LangGraph | [Official concepts](https://docs.langchain.com/oss/python/concepts/products) describe a low-level runtime for long-running stateful agents, durable execution, persistence, and human-in-the-loop; [official releases](https://github.com/langchain-ai/langgraph/releases) show active 1.x maintenance | Capable, but its graph/runtime surface exceeds present needs | New dependency, migration and checkpoint-format surface without demonstrated evaluation gain |
| Microsoft Agent Framework | [Official overview](https://learn.microsoft.com/en-us/agent-framework/overview/) provides agents, sessions, middleware and graph workflows and explicitly advises using a function when a function can handle the task; [hosting guidance](https://learn.microsoft.com/en-us/agent-framework/hosting/) says current Python self-hosting packages are prerelease | Attractive if the PoC becomes a hosted multi-provider agent or multi-function workflow | Prerelease Python hosting path, additional abstractions, and no current behavioural evidence of benefit |

Neither optional framework package nor LangGraph is installed in the repository environment. Framework marketing claims are not treated as project evidence.

## Decision

Retain the lightweight deterministic state machine for this tranche. Keep the model provider behind a small protocol and keep evidence, checkpoints, and user preferences in separate stores. This is a positive architecture decision, not an assertion that either external framework is unsuitable in general.

The selected path is demonstrated by:

- content-addressed immutable evidence snapshots;
- append-only, workflow-id-scoped checkpoints;
- pause after evidence snapshot, resume, and byte-equal completed-result replay;
- deterministic gates before any optional model call;
- no framework telemetry or hidden persistence.

## Re-evaluation triggers

Re-run this ADR with a measured spike when any two of these become requirements: concurrent branches, multiple agents, tool-call loops, durable distributed workers, hosted streaming sessions, framework-native telemetry, or human edits to in-flight graph state. A spike must use the same held-out cases and report dependency, latency, replay, and security deltas. Do not migrate solely to claim framework adoption.

## Consequences

The current implementation is easier to audit and package, but the repository remains responsible for migration, locking, retention, authentication and production-grade storage. It is a local PoC, not a distributed production runtime.
