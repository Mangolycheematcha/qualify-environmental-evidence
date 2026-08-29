# Evidence Identity

The evidence allowlist and machine rules are authoritative in `config/evidence-sources.json`.

- CER register identity is bound to its exact HTTPS host and register path.
- CER project records are bound to the exact case project ID and canonical project path.
- CER published CEA identity must contain the exact case project ID; the final artifact and checksum remain a specialist-frozen field.
- Sentinel-2 L2A identity is bound to the exact Planetary Computer collection page.

Canonical identities prohibit userinfo, fragments, unexpected ports and query fields, Azure SAS credentials, and every `X-Amz-*` credential. Host matching is exact, not suffix or substring based.

`retrieval_uri` is a separate temporary access mechanism. It may contain signed parameters only for sources whose schema/policy permits it and only when a stable canonical identity remains present. Never use a retrieval URI as the sole provenance key.

Do not substitute a plausible alternative host, project, collection, or unregistered source and do not perform network retrieval in this skill version.
