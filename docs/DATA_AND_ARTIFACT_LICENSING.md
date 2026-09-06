# Data And Artifact Licensing Inventory

This is a factual release inventory, not legal advice. In [GitHub Issue #3](https://github.com/Mangolycheematcha/qualify-environmental-evidence/issues/3), the repository owner confirmed, to the best of their knowledge, authority to release original owner-controlled material under Apache-2.0 and approved continued public availability. That attestation does not relicense third-party or mixed-origin material.

## Inventory

| Material | Current tracked state | Proposed treatment before public release |
|---|---|---|
| Repository-specific Python | Tracked as source | Apache-2.0 where original and owner-controlled; owner review recorded in Issue #3 |
| JSON Schemas, registries, and tests | Tracked; repository-specific structure and fixtures | Apache-2.0 where original and owner-controlled; source-derived facts retain their own status |
| Original documentation and diagrams | Markdown tracked; no binary diagrams or fonts found | Apache-2.0 where original and owner-controlled |
| Curated CER fact snapshots under `data/cer/` | Tracked as small, source-attributed factual extracts; no raw page or complete register export | Do not relicense the underlying CER material; retain source URL, access date, and extraction caveat |
| CER project pages and CEA boundary files | Canonical identities appear in policy/provenance; complete responses and boundary files are ignored locally | Do not relicense; link and attribute. Publish source bytes only after a separate redistribution review |
| Sentinel-2 and Planetary Computer metadata | Identifiers, URLs, metadata-derived fields, and hashes appear in contracts/examples | Attribute and preserve source terms; do not imply Microsoft or Copernicus endorsement |
| Raster inputs and cached arrays | Complete current run package is ignored and local | Keep out of the public Git baseline unless data terms, size, privacy, and disclosure are separately approved |
| Raw network responses and signed URLs | Ignored; signed credentials are prohibited from persistence | Do not publish signed URLs or credentials. Review any raw response before redistribution |
| Derived run artifacts | One redacted V3 text example is tracked; current V4 assessment/cache package is local | Treat as mixed-origin research artifacts; document derivation and source terms rather than assuming the code licence covers source-derived facts |
| Python dependencies | Declared in `pyproject.toml`/`uv.lock`, not vendored | Retain dependency notices and comply with each package licence when distributing built bundles |
| GitHub Actions | External actions referenced by pinned commit, with no vendored action code | Retain action identity; its upstream licence applies |
| Fonts, images, website templates | None found in the tracked baseline | Re-audit if visual assets are added |

## Selected Licence And Scope

Apache-2.0 applies to original code, schemas, registries, tests, and documentation only to the extent that the repository owner has authority to license them. It does not cover third-party data or metadata, raw source responses, raster products, derived or cached artifacts, external service content, dependencies, or third-party marks except where their own terms independently permit use or redistribution.

The tracked `examples/eop101132-v3-abstained/` directory contains a reviewed derivative rather than a complete evidence package. Its presence does not establish that upstream source material can be relicensed.

## Owner Authorization And Remaining Operations

The owner accepted the historical Gmail disclosure, retained third-party exclusions, and approved continued public availability in Issue #3. GitHub service settings, future source additions, releases, deployments, and any redistribution of excluded material still require their own review. Selecting Apache-2.0 and approving repository publication do not provide a legal guarantee or expand rights in third-party material.
