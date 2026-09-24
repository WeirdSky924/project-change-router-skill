from pathlib import Path

import pytest

from router_support.task_evidence.working_index import WorkingIndexStore


def test_known_owner_assignment_is_external_and_non_authorizing(tmp_path: Path):
    result = WorkingIndexStore(tmp_path / "runtime").record(
        "task", paths=["app/core.py", "tests/core/test_core.py"],
        owner_patterns={"core": ["app/**", "tests/core/**"]}, source_observation_id="obs",
    )
    assert result["assignments"] == {"app/core.py": "core", "tests/core/test_core.py": "core"}
    assert result["baseline_eligible"] is False
    assert result["write_authority"] == "none"


def test_unknown_and_conflicting_paths_remain_visible(tmp_path: Path):
    result = WorkingIndexStore(tmp_path / "runtime").record(
        "task", paths=["unknown.py", "shared.py"],
        owner_patterns={"a": ["shared.py"], "b": ["shared.py"]}, source_observation_id="obs",
    )
    assert result["unknown_paths"] == ["unknown.py"]
    assert result["conflict_paths"] == ["shared.py"]


def test_working_index_cannot_be_replaced_or_tampered(tmp_path: Path):
    store = WorkingIndexStore(tmp_path / "runtime")
    store.record("task", paths=["a.py"], owner_patterns={"a": ["a.py"]}, source_observation_id="obs")
    with pytest.raises(ValueError, match="already exists"):
        store.record("task", paths=["a.py"], owner_patterns={"a": ["a.py"]}, source_observation_id="obs")
    assert store.load("task")["write_authority"] == "none"


def test_observation_events_refresh_paths_without_replacing_history(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = WorkingIndexStore(tmp_path / "runtime")
    first = store.observe("task", repo_root=repo, paths=["app/a.py"],
                          owner_patterns={"core": ["app/**"]}, source_observation_id="first")
    second = store.observe("task", repo_root=repo, paths=["app/a.py", "app/b.py"],
                           owner_patterns={"core": ["app/**"]}, source_observation_id="second")
    repeated = store.observe("task", repo_root=repo, paths=["app/a.py", "app/b.py"],
                             owner_patterns={"core": ["app/**"]}, source_observation_id="second")
    assert first["paths"] == ["app/a.py"]
    assert second["assignments"] == {"app/a.py": "core", "app/b.py": "core"}
    assert second == repeated
    assert len(list((store.root / "events" / "task").glob("*.json"))) == 2
    assert second["write_authority"] == "none"


@pytest.mark.parametrize("path", ["../app/a.py", "/app/a.py", "C:/app/a.py"])
def test_working_paths_cannot_escape(tmp_path, path):
    with pytest.raises(ValueError, match="path"):
        WorkingIndexStore(tmp_path / "runtime").record("task", paths=[path],
            owner_patterns={"core": ["**"]}, source_observation_id="obs")


def test_event_runtime_must_remain_external(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        WorkingIndexStore(tmp_path / "runtime").observe("task", repo_root=tmp_path,
            paths=["app/a.py"], owner_patterns={"core": ["app/**"]}, source_observation_id="obs")
