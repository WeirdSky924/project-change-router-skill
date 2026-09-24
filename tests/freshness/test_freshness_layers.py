from router_support.freshness_checks.layers import classify_freshness_layers


def test_layers_keep_path_content_and_knowledge_distinct():
    report = {
        "failure_reasons": ["structure_digest", "indexed_paths", "changed_path_coverage"],
        "checks": [
            {"name": "indexed_paths", "details": {"missing_from_index": ["new.py"], "stale_in_index": []}},
            {"name": "changed_path_coverage", "details": {"unmapped": ["unknown.py"]}},
        ],
    }
    result = classify_freshness_layers(report, changed_paths=["old.py", "new.py"])
    assert result["path_set"]["status"] == "stale"
    assert result["content"]["status"] == "changed"
    assert result["routing_knowledge"]["status"] == "unknown"
    assert result["write_authority"] == "unchanged"


def test_content_records_identify_code_and_routing_knowledge_changes(tmp_path):
    import subprocess
    from router_support.freshness_checks import build_structure_snapshot
    from router_support.freshness_checks.layers import compare_snapshot_records

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "code.py").write_text("VALUE = 1\n")
    (tmp_path / ".project-change-router.yaml").write_text("capabilities: []\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Test", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "initial"], check=True)
    before = build_structure_snapshot(tmp_path, ())
    (tmp_path / "code.py").write_text("VALUE = 2\n")
    after = build_structure_snapshot(tmp_path, ())
    result = compare_snapshot_records(after, {"file_records": list(before.file_records)})
    assert result["complete"] is True
    assert result["content_changed_paths"] == ["code.py"]
    assert result["knowledge_changed_paths"] == []
    (tmp_path / ".project-change-router.yaml").write_text("capabilities: [new]\n")
    changed = compare_snapshot_records(build_structure_snapshot(tmp_path, ()), {"file_records": list(before.file_records)})
    assert changed["knowledge_changed_paths"] == [".project-change-router.yaml"]


def test_legacy_snapshot_does_not_fabricate_per_file_precision(tmp_path):
    import subprocess
    from router_support.freshness_checks import build_structure_snapshot
    from router_support.freshness_checks.layers import compare_snapshot_records
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    current = build_structure_snapshot(tmp_path, ())
    assert compare_snapshot_records(current, {})["complete"] is False


def test_missing_head_does_not_prove_snapshot_complete(tmp_path):
    import subprocess
    from router_support.freshness_checks import build_structure_snapshot
    from router_support.freshness_checks.layers import compare_snapshot_records

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "code.py").write_text("VALUE = 1\n")
    current = build_structure_snapshot(tmp_path, ())
    result = compare_snapshot_records(current, {"file_records": list(current.file_records)})
    assert result["complete"] is False


def test_missing_freshness_checks_are_unknown_not_current():
    result = classify_freshness_layers({})
    assert all(result[name]["status"] == "unknown" for name in ("path_set", "content", "routing_knowledge"))


def test_snapshot_records_must_cover_the_recorded_index():
    from router_support.freshness_checks import StructureSnapshot
    from router_support.freshness_checks.layers import compare_snapshot_records
    current = StructureSnapshot("a" * 40, "b" * 64, ("app.py",), (), file_records=(
        {"path": "app.py", "content_digest": "c" * 64, "executable": False},))
    result = compare_snapshot_records(current, {"indexed_paths": ["app.py"], "file_records": []})
    assert result["complete"] is False
