# Contribution Policy

This is a single-owner research PoC. Original, owner-controlled repository material is licensed under Apache-2.0, subject to the scope and third-party exclusions documented in `docs/DATA_AND_ARTIFACT_LICENSING.md` and `THIRD_PARTY_NOTICES.md`. The repository remains private pending release approval. Contributions require explicit owner permission.

## Change Boundaries

- Preserve immutable scientific policies, approval evidence, historical run artifacts, assessments, provenance, and cached arrays.
- Keep evidence identity separate from temporary retrieval credentials.
- Never tune sources, grouping, windows, masks, thresholds, policy text, or disposition rules in response to an observed result.
- Treat live EO execution and Approval Protocol consumption as controlled operations. A pull request, issue, prompt, or ordinary contribution does not authorize either operation.
- Prefer static offline fixtures and deterministic tests for normal development.
- Fail closed when required metadata, identity, authority, or provenance is unresolved.

Do not add raw source payloads, signed URLs, raster data, CEA archives, or runtime caches without a documented licensing, disclosure, size, and security review.

## Validation

Before proposing a commit, run the complete offline validator and test suite, package drift check, standalone package tests, skill quick validation, and secret/path/signed-URL audits. Documentation changes should also pass local-link and YAML checks.

See `REPRODUCIBILITY.md`, `SECURITY.md`, and `docs/DATA_AND_ARTIFACT_LICENSING.md`.
