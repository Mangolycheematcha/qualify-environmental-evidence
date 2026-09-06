# Public Release Checklist

Continued public availability is approved by the repository owner in [GitHub Issue #3](https://github.com/Mangolycheematcha/qualify-environmental-evidence/issues/3). This checklist separates that authorization from technical and operational checks; passing CI alone does not grant rights or expand the approved scope.

- [x] Select Apache-2.0 for original, owner-controlled repository material; update the private-only notice.
- [x] Record the selected licence scope and third-party exclusions in `docs/DATA_AND_ARTIFACT_LICENSING.md`, `THIRD_PARTY_NOTICES.md`, and `NOTICE`.
- [x] Confirm ownership and redistribution rights for tracked original material; retain exclusions for third-party and mixed-origin artifacts. Owner attestation: Issue #3.
- [x] Re-run secret, signed-URL, credential, connection-string, username, and machine-path scans over all commits.
- [x] Review binaries and files larger than 10 MB.
- [x] Confirm raw HTTP payloads, raster assets, runtime caches, and AOI chips are absent unless explicitly cleared.
- [x] Verify V3 immutable hashes and clearly label curated derivatives.
- [x] Confirm the Step 2B closure remains `SCIENCE_VALID — GOVERNANCE_LIMITATION — NO_RERUN` and is not described as fully canonical.
- [x] Verify pending policies are not represented as approved or runtime-ready.
- [x] Run the complete validator, tests, package drift check, standalone test, and skill quick validation.
- [x] Review attribution and third-party source terms; no third-party material is relicensed by the owner attestation.
- [x] Confirm no endorsement, affiliation, regulatory, scientific, carbon, credit-quality, or financial claim is implied.
- [ ] Confirm GitHub visibility, Pages, Actions, releases, collaborators, and secrets are intentionally configured.
- [x] Obtain explicit human approval for continued public availability. Evidence: Issue #3.

The remaining GitHub settings review is an owner-operated service check, not authorization to modify settings in this repository pass. No release, tag, DOI, deployment, or Step 3 execution is authorized.
