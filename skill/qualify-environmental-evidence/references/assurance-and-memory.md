# Assurance And Evidence Memory

The deterministic assurance layer is a rule-based control surface, not an audit or assurance opinion. It validates request shape, exact source identity, source authority, evidence completeness, frozen-result hashes, non-inference rules, and canonical output serialization.

Evidence memory is content-addressed and local. Each document has a stable evidence ID, canonical source URI, access date, authority scope, structured facts, and a raw document SHA-256. Retrieval uses controlled claim families, required tags, project identity, lexical overlap, and stable tie-breaking. It stores no conversation history, hidden reasoning, user profile, credential, signed URL, or model response.

Evidence snapshots are immutable and content-addressed. Checkpoints are workflow-scoped and strictly append by sequence; an identical write at an existing sequence is idempotent, while changed bytes, skipped sequences, and backfills fail closed. Preferences are a separate allowlisted current-session document written by atomic replacement; they are intentionally mutable and are not represented as an append-only audit history.

Prompt text cannot change the claim family, source allowlist, required tags, frozen hashes, or authority ceiling. Refused claim families stop before fact retrieval. Any unregistered source, redirected canonical URI, mismatched authority, duplicate fact ID, non-finite value, incomplete tag set, or altered frozen hash fails closed.

The Step 3 benchmark is an offline deterministic evaluation. Its 80 rows cover 22 semantic groups and are repository-authored regression expectations, not 80 independent expert-labelled scenarios. Its unsupported-assertion measure is a bounded proxy for this rule system; it is not evidence about the hallucination rate of an LLM that has not been integrated or tested.
