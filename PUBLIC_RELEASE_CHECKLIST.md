# Public Release Checklist

Public release is not approved. Before changing repository visibility, an accountable human must verify every item below.

- [x] Select Apache-2.0 for original, owner-controlled repository material; update the private-only notice.
- [x] Record the selected licence scope and third-party exclusions in `docs/DATA_AND_ARTIFACT_LICENSING.md`, `THIRD_PARTY_NOTICES.md`, and `NOTICE`.
- [ ] Confirm ownership and redistribution rights for every tracked artifact.
- [ ] Re-run secret, signed-URL, credential, connection-string, username, and machine-path scans over all commits.
- [ ] Review binaries and files larger than 10 MB.
- [ ] Confirm raw HTTP payloads, raster assets, runtime caches, and AOI chips are absent unless explicitly cleared.
- [ ] Verify V3 immutable hashes and clearly label curated derivatives.
- [ ] Confirm the Step 2B closure remains `SCIENCE_VALID — GOVERNANCE_LIMITATION — NO_RERUN` and is not described as fully canonical.
- [ ] Verify pending policies are not represented as approved or runtime-ready.
- [ ] Run the complete validator, tests, package drift check, standalone test, and skill quick validation.
- [ ] Review attribution and third-party source terms.
- [ ] Confirm no endorsement, affiliation, regulatory, scientific, carbon, credit-quality, or financial claim is implied.
- [ ] Confirm GitHub visibility, Pages, Actions, releases, collaborators, and secrets are intentionally configured.
- [ ] Obtain explicit human approval for public release.

Repository visibility must remain private until every applicable item is reviewed by the owner. Passing CI is necessary but does not grant a licence or authorize publication.
