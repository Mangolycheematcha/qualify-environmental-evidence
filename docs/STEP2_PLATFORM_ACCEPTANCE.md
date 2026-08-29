# Step 2 Platform Packaging Acceptance

## Decision

Step 2 platform packaging is **accepted** for the repository-contained, contract-only `qualify-environmental-evidence` skill. The package is copyable and structurally valid; it was not globally installed or published.

Scientific/runtime Earth-observation processing is not part of this decision and remains unavailable.

## Package

- `skill/qualify-environmental-evidence/SKILL.md` defines discriminating trigger and non-trigger scope.
- `agents/openai.yaml` provides quoted UI metadata and keeps implicit invocation enabled.
- `scripts/qualify.py` exposes specification, refusal, linked-validation, JSON-output, and resource-check paths with stable exit codes.
- Four focused references cover authority/review, contract/status/reasons, evidence identity, and provenance/CLI behavior.
- Repository `schemas/`, `config/`, `cases/`, and the hardened validator remain authoritative.
- `scripts/package_skill.py` synchronises an explicit ten-file allowlist and generates `resource-manifest.json`; `--check` detects stale, missing, unexpected, or hash-mismatched managed resources.

The package contains no network client, signed retrieval credential, secret, machine-specific path, cache, empirical output, or scientific parameter choice.

## Verification

Executed from the repository root on 2026-08-29:

```text
uv run --no-project python scripts/package_skill.py --check
```

Result: exit 0; `Skill resources checked: 10 files; no drift.`

```text
uv run --no-project --with 'PyYAML>=6,<7' python <skill-creator>/scripts/quick_validate.py skill/qualify-environmental-evidence
```

Result: exit 0; `Skill is valid!` The platform validator path was resolved from the installed Codex `skill-creator` instructions; no repository artifact depends on that machine path.

```text
uv run --no-project --with 'jsonschema>=4.18,<5' --with 'pytest>=8,<9' --with 'PyYAML>=6,<7' python -m pytest -o addopts='' -p no:cacheprovider -q
```

Result: exit 0; `129 passed in 9.47s`.

```text
uv run --no-project --with 'jsonschema>=4.18,<5' --with 'pytest>=8,<9' --with 'PyYAML>=6,<7' python -m pytest -o addopts='' -p no:cacheprovider -q tests/test_skill_package.py::test_standalone_skill_copy_runs_without_repository
```

Result: exit 0; `1 passed in 0.79s`. The test copied only the installable skill to a temporary directory and successfully ran both resource integrity and specification-mode validation from outside the repository.

An additional external-working-directory smoke command returned exit 0 and compact JSON with `VALID_SPECIFICATION_PENDING`, `ABSTAINED`, `INCONCLUSIVE`, `runtime_ready=false`, `scientific_execution_available=false`, and `empirical_environmental_result=false`.

## Deferred

Step 3 remains responsible for hallucination/accuracy evaluation, performance, broader security evaluation, and any later reviewed scientific implementation. Network access, agent orchestration, API/UI work, vector storage, publication, and empirical validation were not added.
