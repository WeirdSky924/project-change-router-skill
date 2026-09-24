from __future__ import annotations

import subprocess
from pathlib import Path
import pytest

from router_support.change_flow import _check_evidence
from router_support.freshness_checks import build_structure_snapshot
from router_support.incremental_evidence import build_evidence_input


def setup_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "app/a.py").write_text("from app.shared import VALUE\n")
    (repo / "app/b.py").write_text("from app.shared import VALUE\n")
    (repo / "app/shared.py").write_text("VALUE = 1\n")
    (repo / "docs/note.md").write_text("one\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "initial"], check=True)
    return repo


def bundle():
    return {"config": {}, "module_map": {"modules": [{"path": "app", "depends_on": []}]},
            "capability_catalog": {"capabilities": [{"id": "core", "owner_modules": ["app"]}]},
            "path_to_capability_map": {"path_index": [{"path_pattern": "app/**", "capabilities": ["core"]}]}}


def evidence(repo):
    return build_evidence_input(repo, bundle(), ["app/a.py"],
        runtime_identity={"identity_digest": "runtime"},
        structure_digest=build_structure_snapshot(repo, ()).digest)


def test_real_content_digest_change_does_not_expire_reuse_for_unrelated_docs(tmp_path):
    repo = setup_repo(tmp_path)
    before = evidence(repo)
    (repo / "docs/note.md").write_text("changed documentation\n")
    after = evidence(repo)
    assert before["structure_digest"] != after["structure_digest"]
    assert _check_evidence(before, "reuse", "extend", False) == _check_evidence(after, "reuse", "extend", False)
    assert _check_evidence(before, "freshness", "extend", False) != _check_evidence(after, "freshness", "extend", False)


def test_reuse_still_invalidates_on_cross_capability_source(tmp_path):
    repo = setup_repo(tmp_path)
    before = evidence(repo)
    (repo / "outside.py").write_text("def duplicate(): return 3\n")
    after = evidence(repo)
    assert _check_evidence(before, "reuse", "extend", False) != _check_evidence(after, "reuse", "extend", False)


def test_directed_path_relations_do_not_connect_sibling_consumers(tmp_path):
    from router_support.task_evidence.relations import build_path_relations
    repo = setup_repo(tmp_path)
    result = build_path_relations(repo, ["app/a.py"], ["app/a.py", "app/b.py", "app/shared.py"])
    assert result["complete"] is True
    assert result["dependency_paths"] == ["app/a.py", "app/shared.py"]
    assert result["impacted_paths"] == ["app/a.py"]
    shared = build_path_relations(repo, ["app/shared.py"], ["app/a.py", "app/b.py", "app/shared.py"])
    assert shared["impacted_paths"] == ["app/a.py", "app/b.py", "app/shared.py"]


def test_dynamic_import_never_proves_precise_isolation(tmp_path):
    from router_support.task_evidence.relations import build_path_relations
    repo = setup_repo(tmp_path)
    (repo / "app/a.py").write_text("import importlib\nimportlib.import_module(input())\n")
    result = build_path_relations(repo, ["app/a.py"], ["app/a.py", "app/b.py", "app/shared.py"])
    assert result["complete"] is False
    assert result["diagnostics"]


def test_evidence_input_uses_directed_relations_without_sibling_contamination(tmp_path):
    repo = setup_repo(tmp_path)
    (repo / "app/b.py").write_text("from app.shared import VALUE\nOTHER = 1\n")
    result = evidence(repo)
    assert result["path_relations"]["complete"] is True
    assert {r["path"] for r in result["closure_source_fingerprints"]} == {"app/a.py", "app/shared.py"}
    assert "app/b.py" in result["worktree_paths"]
    assert any(r["path"] == "app/b.py" for r in result["global_source_fingerprints"])


def test_missing_source_relation_does_not_prove_isolation(tmp_path):
    from router_support.task_evidence.relations import build_path_relations
    repo = setup_repo(tmp_path)
    (repo / "app/a.py").unlink()
    result = build_path_relations(repo, ["app/a.py"], ["app/a.py", "app/b.py", "app/shared.py"])
    assert result["complete"] is False
    assert {"path": "app/a.py", "code": "source_missing"} in result["diagnostics"]


def test_previous_relation_keeps_removed_dependency_visible(tmp_path):
    from router_support.task_evidence.relations import build_path_relations
    repo = setup_repo(tmp_path)
    (repo / "app/a.py").write_text("VALUE = 2\n")
    result = build_path_relations(repo, ["app/a.py"], ["app/a.py", "app/b.py", "app/shared.py"],
                                  previous_edges=[{"source": "app/a.py", "target": "app/shared.py", "kind": "runtime_import"}])
    assert result["closure_paths"] == ["app/a.py", "app/shared.py"]


@pytest.mark.parametrize("path", ["../outside.py", "/tmp/outside.py"])
def test_evidence_rejects_route_path_escape_before_reading(tmp_path, path):
    repo = setup_repo(tmp_path)
    with pytest.raises(ValueError, match="escapes repository"):
        build_evidence_input(repo, bundle(), [path], runtime_identity={"identity_digest": "runtime"}, structure_digest="snapshot")


def test_check_cache_binds_comparison_base_and_runtime_budget(tmp_path):
    repo = setup_repo(tmp_path)
    inputs = evidence(repo)
    first = _check_evidence(inputs, "dependency", "extend", False, comparison_commit="base-a", timeout_seconds=20)
    second = _check_evidence(inputs, "dependency", "extend", False, comparison_commit="base-b", timeout_seconds=20)
    assert first != second
    cold = _check_evidence(inputs, "reuse", "extend", False, timeout_seconds=20)
    larger = _check_evidence(inputs, "reuse", "extend", False, timeout_seconds=30)
    assert cold != larger
