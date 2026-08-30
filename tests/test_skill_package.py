from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import validate_step1_specs as step1
from scripts import approval_protocol_v2


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "qualify-environmental-evidence"
CLI = SKILL / "scripts" / "qualify.py"
PACKAGE_SCRIPT = ROOT / "scripts" / "package_skill.py"
CASE = ROOT / "cases" / "eop101132" / "case-spec.json"


def run_cli(*args: str, cwd: Path | None = None, cli: Path = CLI) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(cli), *map(str, args)],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return path


def write_linked_fixture(tmp_path: Path, status: str = "COMPLETED") -> tuple[Path, Path, Path]:
    registries = step1.load_contracts()["registries"]
    case = step1.build_fixture_cases()[status]
    assessment, manifest = step1.build_fixture_pairs(registries)[status]
    return (
        write_json(tmp_path / "case.json", case),
        write_json(tmp_path / "assessment.json", assessment),
        write_json(tmp_path / "manifest.json", manifest),
    )


def test_skill_frontmatter_folder_and_trigger_scope_are_valid():
    assert SKILL.name == "qualify-environmental-evidence"
    content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, flags=re.DOTALL)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter["name"] == SKILL.name
    description = frontmatter["description"]
    assert "bounded" in description and "do not use" in description
    assert "financial judgments" in description
    assert "[TODO" not in content


def test_openai_yaml_is_syntactically_valid_and_consistent_with_skill():
    metadata = yaml.safe_load((SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    interface = metadata["interface"]
    assert interface["display_name"] == "Qualify Environmental Evidence"
    assert 25 <= len(interface["short_description"]) <= 64
    assert "$qualify-environmental-evidence" in interface["default_prompt"]
    assert metadata["policy"]["allow_implicit_invocation"] is True
    assert "Do not trigger" in (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_skill_has_no_placeholders_empty_files_or_empty_directories():
    files = [path for path in SKILL.rglob("*") if path.is_file()]
    directories = [path for path in SKILL.rglob("*") if path.is_dir()]
    assert files
    assert all(path.stat().st_size > 0 for path in files)
    assert all(any(path.iterdir()) for path in directories)
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files)
    assert not re.search(r"\b(TODO|TBD|FIXME)\b", text)
    assert not (SKILL / "README.md").exists()
    assert not any(path.name == "__pycache__" or path.suffix == ".pyc" for path in SKILL.rglob("*"))


def test_packaged_resources_match_authoritative_allowlist_and_manifest():
    result = subprocess.run([sys.executable, str(PACKAGE_SCRIPT), "--check"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((SKILL / "resource-manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["resources"]) == 19
    assert [item["path"] for item in manifest["resources"]] == list(dict.fromkeys(item["path"] for item in manifest["resources"]))


def test_cli_runs_outside_repository_working_directory(tmp_path):
    result = run_cli(str(CASE), "--json", cwd=tmp_path)
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["outcome"] == "VALID_SPECIFICATION_PENDING"
    assert payload["execution_status"] == "ABSTAINED"
    assert payload["runtime_ready"] is False
    assert payload["scientific_execution_available"] is False
    assert payload["empirical_environmental_result"] is False


def test_standalone_skill_copy_runs_without_repository(tmp_path):
    standalone = tmp_path / "qualify-environmental-evidence"
    shutil.copytree(SKILL, standalone)
    cli = standalone / "scripts" / "qualify.py"
    case = standalone / "cases" / "eop101132" / "case-spec.json"
    result = run_cli(str(case), "--json", cwd=tmp_path, cli=cli)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["outcome"] == "VALID_SPECIFICATION_PENDING"
    check = run_cli("--check-resources", "--json", cwd=tmp_path, cli=cli)
    assert check.returncode == 0
    assert json.loads(check.stdout)["outcome"] == "RESOURCES_VALID"


def test_standalone_skill_validates_approval_request_without_network(tmp_path):
    request = approval_protocol_v2.build_request(
        policy_sha256=approval_protocol_v2.APPROVED_POLICY_SHA256,
        runtime_spec_sha256="b" * 64,
        executable_git_commit="a" * 40,
        created_at_utc="2026-08-30T00:00:00.000000Z",
    )
    request_path = write_json(tmp_path / "approval-request.json", request)
    result = run_cli("--approval-request", str(request_path), "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "VALID_APPROVAL_REQUEST_V2"
    assert payload["approval_request_sha256"] == request["approval_request_sha256"]


def test_machine_output_and_stable_authority_refusal_exit_code(tmp_path):
    case = copy.deepcopy(step1.load_contracts()["case"])
    case["claim_contract"]["authority_ceiling"] = "FINANCIAL_SUITABILITY"
    path = write_json(tmp_path / "overreach.json", case)
    result = run_cli(str(path), "--json", cwd=tmp_path)
    payload = json.loads(result.stdout)
    assert result.returncode == 3
    assert payload["outcome"] == "CONTROLLED_REFUSAL"
    assert payload["execution_status"] == "REFUSED"
    assert payload["evidence_disposition"] is None
    assert payload["reason_codes"] == ["AUTHORITY_SCOPE_EXCEEDED"]
    assert payload["human_review_required"] is True


def test_cli_performs_no_network_calls(monkeypatch, capsys):
    def blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    scripts = str(SKILL / "scripts")
    monkeypatch.syspath_prepend(scripts)
    sys.modules.pop("validate_step1_specs", None)
    spec = importlib.util.spec_from_file_location("skill_qualify_no_network", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    assert module.main([str(CASE), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "VALID_SPECIFICATION_PENDING"


def test_packaged_files_contain_no_machine_paths_secrets_or_network_clients():
    text_files = [path for path in SKILL.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in text_files)
    assert "C:\\Users\\" not in combined
    assert "BEGIN PRIVATE KEY" not in combined
    assert not re.search(r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*['\"][^'\"]+", combined)
    python_source = "\n".join(path.read_text(encoding="utf-8") for path in text_files if path.suffix == ".py")
    assert not re.search(r"(?m)^\s*(?:from|import)\s+(requests|httpx|urllib\.request|aiohttp)\b", python_source)


@pytest.mark.parametrize("field", ["source", "transformation"])
def test_unknown_controlled_identifiers_fail_closed_through_cli(field, tmp_path):
    case = copy.deepcopy(step1.load_contracts()["case"])
    if field == "source":
        case["evidence_policy"]["allowed_source_ids"].append("UNKNOWN_SOURCE")
    else:
        case["transformation_policy"]["required_transformation_ids"][4] = "UNKNOWN_TRANSFORMATION"
    result = run_cli(str(write_json(tmp_path / f"unknown-{field}.json", case)), "--json", cwd=tmp_path)
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["outcome"] == "INVALID_CONTRACT"
    assert payload["empirical_environmental_result"] is False


def test_tampered_or_unexpected_packaged_resource_fails_integrity_check(tmp_path):
    standalone = tmp_path / "qualify-environmental-evidence"
    shutil.copytree(SKILL, standalone)
    (standalone / "config" / "evidence-sources.json").write_text("{}\n", encoding="utf-8")
    result = run_cli("--check-resources", "--json", cwd=tmp_path, cli=standalone / "scripts" / "qualify.py")
    assert result.returncode == 4
    assert json.loads(result.stdout)["outcome"] == "RESOURCE_INTEGRITY_FAILURE"
    shutil.copytree(SKILL, standalone, dirs_exist_ok=True)
    (standalone / "config" / "unexpected.json").write_text("{}\n", encoding="utf-8")
    result = run_cli("--check-resources", "--json", cwd=tmp_path, cli=standalone / "scripts" / "qualify.py")
    assert result.returncode == 4
    assert "unexpected resource" in json.loads(result.stdout)["detail"]
    shutil.copytree(SKILL, standalone, dirs_exist_ok=True)
    (standalone / "scripts" / "validate_step1_specs.py").unlink()
    result = run_cli("--check-resources", "--json", cwd=tmp_path, cli=standalone / "scripts" / "qualify.py")
    assert result.returncode == 4
    assert "missing resource" in json.loads(result.stdout)["detail"]


def test_valid_linked_fixture_passes_as_contract_validation_only(tmp_path):
    case, assessment, manifest = write_linked_fixture(tmp_path)
    result = run_cli(str(case), "--assessment", str(assessment), "--manifest", str(manifest), "--json", cwd=tmp_path)
    payload = json.loads(result.stdout)
    assert result.returncode == 0, result.stderr
    assert payload["outcome"] == "VALID_LINKED_CONTRACT"
    assert payload["artifact_runtime_mode"] == "SCHEMA_FIXTURE"
    assert payload["execution_status"] == "COMPLETED"
    assert payload["empirical_environmental_result"] is False
    assert "no environmental execution" in payload["detail"]


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("nan", "non-standard JSON numeric constant"),
        ("evil_uri", "exact allowlisted host"),
        ("impossible_pixel", "aoi_valid_pixels must not exceed"),
        ("false_statement", "statement project_id does not match authoritative case"),
        ("incomplete_manifest", "complete source and transformation provenance"),
        ("contradictory_reason", "incompatible reason codes"),
    ],
)
def test_step1_regressions_remain_rejected_through_packaged_cli(scenario, expected, tmp_path):
    if scenario in {"nan", "evil_uri"}:
        case = copy.deepcopy(step1.load_contracts()["case"])
        case_path = tmp_path / "case.json"
        if scenario == "nan":
            case_path.write_text('{"value": NaN}', encoding="utf-8")
        else:
            case["evidence_policy"]["source_bindings"][2]["discovery_uri"] = "https://evil.example/fake"
            write_json(case_path, case)
        result = run_cli(str(case_path), "--json", cwd=tmp_path)
    else:
        status = "ERROR" if scenario in {"impossible_pixel", "contradictory_reason"} else "COMPLETED"
        case, assessment_path, manifest_path = write_linked_fixture(tmp_path, status)
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if scenario == "impossible_pixel":
                assessment["observations"] = {
                    "observation_status": "COMPLETE", "aoi_total_pixels": 10, "aoi_valid_pixels": 999999,
                    "aoi_valid_fraction": 0.5, "pre_window_ndvi_median": 0.1, "post_window_ndvi_median": 0.2,
                    "delta_ndvi": 0.1, "primary_tau": 0.03,
                    "delta_distribution": {"count": 1, "q05": 0.1, "q25": 0.1, "median": 0.1, "q75": 0.1, "q95": 0.1, "iqr": 0.0, "mad": 0.0},
                    "sensitivity_results": step1.step2b_offline.classify_primary_and_sensitivities(0.1)["sensitivities"],
                }
        elif scenario == "false_statement":
            assessment["statement_parameters"]["project_id"] = "ATTACKER-PROJECT"
        elif scenario == "incomplete_manifest":
            manifest["source_records"] = []
            manifest["transformation_records"][4].update(
                {"status": "SKIPPED", "input_artifact_refs": [], "output_artifact_refs": [], "reason_codes": ["SOURCE_UNAVAILABLE"]}
            )
        else:
            assessment["reason_codes"] = ["AUTHORITY_SCOPE_EXCEEDED", "DETERMINISTIC_PROCESSING_ERROR"]
            assessment["quality_checks"]["authority_scope"] = "FAIL"
        write_json(assessment_path, assessment)
        write_json(manifest_path, manifest)
        result = run_cli(str(case), "--assessment", str(assessment_path), "--manifest", str(manifest_path), "--json", cwd=tmp_path)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "INVALID_CONTRACT"
    assert expected in payload["detail"]
