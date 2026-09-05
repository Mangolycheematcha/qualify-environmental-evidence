---
name: qualify-environmental-evidence
description: Qualify bounded, allowlisted CER registry and frozen Earth-observation evidence with deterministic retrieval, provenance, abstention, and authority controls. Use for source-attributed registry facts, observational consistency, ACCU/SMC semantic boundaries, contract validation, and offline evaluation; do not use to validate environmental assets, quantify carbon, run remote sensing, or make regulated, legal, credit, trading, investment, or other financial judgments.
---

# Qualify Environmental Evidence

Use this skill when the user asks to:

- qualify whether allowlisted CER and Earth-observation evidence could support a bounded observational claim;
- check whether an evidence question exceeds the observational authority ceiling;
- validate a claim contract, assessment, or provenance manifest for this PoC;
- run the offline EOP101132 qualification demo against curated CER public facts and the frozen Step 2B summary;
- explain the CER-defined semantic boundary between ACCUs and SMCs without treating them as interchangeable;
- produce an auditable specification-mode status with registered reason codes.

Do not trigger it for general GIS or remote-sensing instruction, broad ESG research, carbon quantification, causal attribution, ACCU/project integrity or compliance judgments, legal/audit conclusions, or lending, trading, investment, and tokenisation decisions.

## Workflow

1. Read [authority-and-review.md](references/authority-and-review.md) before interpreting scope or escalating to a specialist.
2. Read [assurance-and-memory.md](references/assurance-and-memory.md) before using retrieval or the end-to-end workflow.
3. Read [accu-smc-boundary.md](references/accu-smc-boundary.md) for any ACCU/SMC question.
4. Read [contract-and-status.md](references/contract-and-status.md) for legacy contract/status semantics.
5. Read [evidence-identity.md](references/evidence-identity.md) and [provenance-and-cli.md](references/provenance-and-cli.md) before reporting evidence or hashes.
6. Run `python scripts/qualification_workflow.py examples/qualification/eop101132-request.json --json` for the packaged offline demo. Run `python scripts/evaluate_qualification.py --json` for the deterministic Step 3 benchmark.
7. Use `python scripts/qualify.py <case.json> --json` for legacy contract validation. Add both `--assessment` and `--manifest` only for authoritative linked validation.
8. Report structured status, reason codes, selected fact IDs, canonical source identities, document/result hashes, limitations, and review requirements. Never request or store private chain-of-thought.

The legacy case specification remains `runtime_ready=false` and contract-only. The separate workflow layer reads curated CER public facts and a hash-bound derivative of the completed frozen Step 2B assessment. It does not run EO processing, modify the historical run, consume approval, or turn a registry fact into an empirical, compliance, credit-quality, or financial conclusion.

ABSTAIN when required evidence is unresolved or the frozen assessment is inconclusive. REFUSE before retrieval when the requested conclusion exceeds evidence-qualification authority. Stop for human or specialist review at every trigger listed in the authority reference. The packaged workflow can replay evidence qualification, but scientific execution remains unavailable and no new empirical result may be generated.
