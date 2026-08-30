# Approval Protocol V2

Approval Protocol V2 is the governance gate for any future EOP101132 V4 live execution. It does not change the scientific policy or authorize a run by itself.

## Data Flow

1. After the implementation commit and runtime-spec freeze, the offline request CLI creates a random request ID, reserved Run ID, 256-bit nonce, frozen tuple, modes, scopes, one-execution limit, and expiry under ignored `runs/pending-approvals/`.
2. The human owner manually publishes the exact canonical statement in the GitHub web UI as an issue or issue comment.
3. The read-only adapter performs one GitHub API `GET`. Before the request, it persists an authorization-network attempt without credentials or headers.
4. The validator uses GitHub API actor identity, repository and evidence IDs, canonical URL, exact body bytes, timestamps, expiry, and safe response fields. Validation produces `VERIFIED` state but does not consume the request.
5. Runtime initialization rechecks the policy, runtime spec, executable commit, clean Git state, reserved Run ID, request/evidence hashes, and authorization attempt history. It then creates a permanent exclusive lock and records the sole consumption before creating the run directory.
6. The first CER/STAC/signing/raster attempt is recorded separately as environmental-data access before the HTTP request. A timeout, DNS, TLS, or connection failure does not remove either attempt or consumption evidence.

The lifecycle is `PENDING`, `VERIFIED`, `CONSUMED`, or `REJECTED`. A surviving consumption lock always fails closed, including after a crash. Preflight never consumes. A source failure after consumption never restores the approval.

## Canonical Hash

`CANONICAL_JSON_V1` is UTF-8 JSON with sorted object keys, compact separators, no NaN or Infinity, and one trailing newline. Duplicate keys are rejected during parsing.

To avoid a self-reference cycle, `approval_request_sha256` is SHA-256 over the canonical request binding payload with `approval_request_sha256` and `canonical_approval_statement` excluded. The statement is then derived from the binding payload and request hash. The full request file has a separate ordinary file SHA-256 when copied into a run package.

## Trust Boundary

Prompt text, terminal input, generated files, copied approval prose, filenames, and a self-declared `HUMAN_PROJECT_OWNER` role are not human-approval evidence. The implemented independent adapter accepts only a pre-existing GitHub issue or issue comment whose API actor is exactly `Mangolycheematcha` in `Mangolycheematcha/qualify-environmental-evidence`.

The adapter contains no create, update, reply, or delete operation. A future detached-signature adapter may implement the same verified-evidence interface, but no PKI or IAM mechanism is implemented here.
