# Data Sources And Attribution

The contract allowlists official Clean Energy Regulator project and mapping records and Microsoft Planetary Computer Sentinel-2 L2A metadata. Canonical source identities and source-specific attribution are recorded in policies and provenance artifacts.

No repository text should be interpreted as Microsoft affiliation, Clean Energy Regulator endorsement, DFCRC partnership, university affiliation, regulatory approval, assurance, or scientific validation.

Raw HTTP payloads, imagery, metadata assets, and raster chips are excluded from the Git baseline until their licensing, redistribution, privacy, credential, and disclosure status is reviewed. Curated examples contain only redacted derivatives that passed local secret, signed-URL, and machine-path scans.

`data/cer/` contains small curated factual snapshots from seven official ACCU project pages, the CER ACCU/SMC definition page, and one row from the official 2024-25 Safeguard baselines and emissions CSV, accessed on 2026-09-05. The project sample spans six method types, mapping availability, issuance variation, a revoked project, and an enforceable undertaking. `data/cer/corpus-manifest.json` records each local snapshot hash plus the independently captured raw source byte hash and byte count. Raw source responses are not redistributed.

These snapshots support the offline demo but are not complete source pages, complete register exports, continuously refreshed data, or an implemented stable CER API. The Safeguard row is a facility-period record and must not be transferred into ACCU project semantics. Its `SMCs issued = 9,693` value is a faithful extract from the cited CER CSV row, not independent repository proof of an issuance event.

See `THIRD_PARTY_NOTICES.md` and `docs/DATA_AND_ARTIFACT_LICENSING.md` for the tracked-material inventory, licence boundary, and unresolved release decisions.
