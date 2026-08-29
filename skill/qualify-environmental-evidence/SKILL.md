---
name: qualify-environmental-evidence
description: Validate and qualify bounded, allowlisted environmental-evidence claim contracts, assessment outputs, and provenance for the specification-first PoC. Use for observational authority checks and auditable contract status; do not use to validate environmental assets, quantify carbon, run remote sensing, or make regulated, legal, credit, or financial judgments.
---

# Qualify Environmental Evidence

Use this skill when the user asks to:

- qualify whether allowlisted CER and Earth-observation evidence could support a bounded observational claim;
- check whether an evidence question exceeds the observational authority ceiling;
- validate a claim contract, assessment, or provenance manifest for this PoC;
- produce an auditable specification-mode status with registered reason codes.

Do not trigger it for general GIS or remote-sensing instruction, broad ESG research, carbon quantification, causal attribution, ACCU/project integrity or compliance judgments, legal/audit conclusions, or lending, trading, investment, and tokenisation decisions.

## Workflow

1. Read [authority-and-review.md](references/authority-and-review.md) before interpreting scope or escalating to a specialist.
2. Read [contract-and-status.md](references/contract-and-status.md) for input/output and reason/status semantics.
3. Read [evidence-identity.md](references/evidence-identity.md) when inspecting source bindings or provenance source records.
4. Read [provenance-and-cli.md](references/provenance-and-cli.md) before running the validator or reporting an audit trail.
5. Run `python scripts/qualify.py <case.json> --json` from the installed skill root, or call it by absolute path from any working directory. Add both `--assessment <assessment.json>` and `--manifest <manifest.json>` only for authoritative linked validation.
6. Report structured status, reason codes, policy versions, source identities, hashes, and review requirements. Never request or store private chain-of-thought.

The current v0.4.0 candidate remains contract-only and pending human approval. It validates packaged schemas and registries, three-way indifference-band semantics, per-item solar-geometry admissibility, item/band radiometry metadata contracts, approved-policy hash binding, controlled authority refusals, linked synthetic or externally supplied contract artifacts, and pending scientific fields. Its offline helpers perform no network or raster access and cannot emit an empirical environmental result.

ABSTAIN when required scientific fields or evidence are unresolved, or when complete measurements fall inside the inclusive primary operational band. REFUSE when the requested conclusion exceeds observational authority. Stop for human or specialist review at every trigger listed in the authority reference. Scientific execution remains unavailable while the policy is pending, `runtime_ready=false`, or any Step 2 field remains unresolved.
