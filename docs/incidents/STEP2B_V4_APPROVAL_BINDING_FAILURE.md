# Step 2B V4 Approval-Binding Failure

## Incident Record

- Run ID: `EOP101132-STEP2B-V4-20260830T044223516364Z-73144a299e2d5763`
- Audit verdict: `VALID_TECHNICAL_RUN_BUT_APPROVAL_BINDING_INVALID`
- Executed commit: `bf0b1a33230ff2d6e259aab2cca087bc8c21dbbf`
- Policy SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`
- Runtime-spec SHA-256: `9bbfdd8c1e73a8a0393afbbec7570e4a28616b204dff2fbed2db17d8dd9a4508`
- Assessment SHA-256: `1b6297f81d1bafc847ef02dac9cb0c2ada91bf03ccedf75759bb07e4002f00dc`
- Provenance SHA-256: `5749fc7fd0b6ee55a98732b2f9ab02a47e125f874e1be9d30be8ad3f63dc3926`

The scientific execution remains technically reviewable and reproducible. Its policy, runtime specification, executable commit, source artifacts, arithmetic, assessment, provenance, checksums, and byte-identical offline replay were independently checked. The result remains `ABSTAINED / INCONCLUSIVE / EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND`.

The authorization chain failed because the detached approval file was generated inside the Codex execution context and merely declared `HUMAN_PROJECT_OWNER`. A role string in a generated file does not establish an independently attributable human act, and no exact pre-network evidence from an external human-controlled channel bound the executed tuple. Prompt text, terminal input, report prose, and filenames are not substitutes for such evidence.

This run must not be described as approved, canonical, compliant, or fully governed. Approval Protocol V2 is a corrective control: it requires a pre-existing GitHub issue or issue comment authored by the allowlisted human owner, an exact request and reserved Run ID binding, expiration, read-only evidence retrieval, and one-time atomic consumption before environmental-data access. This implementation incident has been converted into a regression control.

The original run and every historical artifact and hash are preserved without alteration. Approval Protocol V2 does not retrospectively authorize or repair the old run. A corrected pre-authorized run remains pending.
