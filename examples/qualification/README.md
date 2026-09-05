# Qualification Demo

The demo combines curated real CER public facts with a hash-bound summary of the frozen EOP101132 Step 2B result. It performs no network or raster access.

```text
python scripts/qualification_workflow.py examples/qualification/eop101132-request.json --json
python scripts/qualification_workflow.py examples/qualification/accu-smc-boundary-request.json --json
```

The first request returns the retained `INCONCLUSIVE` observational disposition with cited fact IDs and hashes. The second explains why ACCUs and SMCs must remain semantically distinct. Change `claim_family` to a prohibited family such as `ACCU_QUALITY` or `FINANCIAL_ACTION` to observe controlled refusal before retrieval.

These examples are evidence-qualification demonstrations. They are not current CER API responses, carbon-credit validation, compliance findings, or financial advice.
