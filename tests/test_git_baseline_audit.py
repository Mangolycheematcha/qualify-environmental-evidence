from scripts import audit_git_baseline


def test_git_candidate_baseline_has_no_secret_path_binary_or_executable_leak():
    result = audit_git_baseline.audit()
    assert result["status"] == "PASS"
    assert result["failures"] == []
    assert result["files_over_10_mb"] == []
    assert result["binary_files"] == []
    assert result["symlinks"] == []
    assert result["unexpected_executables"] == []
    assert result["synthetic_signed_url_rejection_fixtures"]
