# Step 2B V4 Post-Metadata Connection Reset

## Preserved Incident

Run `EOP101132-STEP2B-V4-20260830T095123241799Z-5bb61d381c71a8e9` had valid external GitHub approval, exact tuple binding, and one atomic approval consumption before environmental-data access. It ended without raster access, assessment, provenance, replay, or Step 3 output after a POST metadata request raised `ConnectionResetError [WinError 10054]`.

The consumed Approval Protocol V2 request and GitHub Issue #1 remain immutable and cannot authorize another execution. The failed run remains `ERROR / DETERMINISTIC_PROCESSING_ERROR` as a historical artifact; this patch does not retrospectively reclassify, resume, repair, or approve it.

## Root Causes

The V4 retry wrapper caught normalized legacy source failures and raw timeouts, but not a raw connection reset escaping Python's `urllib` stack. The exception therefore reached the generic terminal mapper even though a peer reset is a transient transport/source failure rather than deterministic scientific processing.

The network ledger correctly persisted the first data attempt at `2026-08-30T10:07:37.455380Z`. `fetch_sources()` later wrote a state object loaded before that request, replacing the authoritative value. A later metadata request then populated `run-state.json` with `2026-08-30T10:07:46.961071Z`.

## Corrective Control

Runtime version 1.1.1 narrowly recognizes the standard-library transport exceptions used by this HTTP path: timeouts, connection errors including resets, `http.client.RemoteDisconnected`, and `urllib.error.URLError` or its existing normalized wrapper. It retains the frozen maximum of three attempts, delays of 0, 2, and 5 seconds, timeout, source identities, request contents, and scientific policy. Exhaustion maps to `SOURCE_UNAVAILABLE`; programming, JSON, schema, and metadata-semantic failures are not retried or relabelled.

Each request now creates and persists one authoritative pre-request event. Ledger, run state, failure records, and future provenance reuse the event ID and timestamp. State transitions merge into the latest persisted state so they cannot overwrite network lineage with stale values.

Any future live execution requires a new commit, runtime-spec hash, reserved Run ID, Approval Protocol V2 request, and externally authored GitHub approval. Issue #1 and its consumed approval are not reused.
