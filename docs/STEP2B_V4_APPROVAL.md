# Step 2B V4 Human Approval Gate

Policy: `DEMO_QUALIFICATION_POLICY_EOP101132_V4`

Contract: `0.5.0`

Status: `PENDING_NEW_THREE-WAY_HUMAN_APPROVAL`

Runtime ready: `false`

Canonical V4 proposal SHA-256: `3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd`

Frozen runtime-spec SHA-256: `3ac7684ed5dad74428d03496a41f676a125c12be1f7930aad3121cc05a5054cb`

The earlier policy-only approval produced a preserved pre-network failure because the immutable baseline did not contain a V4 live driver. It does not authorize the new implementation commit.

New approval must bind all three immutable identifiers:

- policy SHA-256;
- frozen runtime-spec SHA-256;
- exact Git commit.

The QUALIFICATION statement format is:

`批准 QUALIFICATION <policy-sha256> RUNTIME_SPEC <runtime-spec-sha256> COMMIT <git-commit>`

The detached approval record version is `2.0.0`, its allowed scope is `ONE_EOP101132_V4_PRIMARY_RUN`, and `policy_mutation_permitted` must be `false`. The approved policy and runtime-spec bytes must not be mutated to insert their own hashes.
