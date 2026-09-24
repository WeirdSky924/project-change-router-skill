from __future__ import annotations

import subprocess
import json
import sys
from pathlib import Path

import pytest

from router_support.task_evidence.observation import TaskObservationStore, observe_worktree


def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "old.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c",
         "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True,
    )
    return repo


def test_existing_dirty_file_modified_again_is_a_new_observation(tmp_path):
    repo = repository(tmp_path)
    (repo / "old.py").write_text("VALUE = 2\n")
    store = TaskObservationStore(tmp_path / "runtime")
    start = store.start("fix-one", repo, binding={"policy": "2"})
    (repo / "old.py").write_text("VALUE = 3\n")
    (repo / "new file.py").write_text("VALUE = 4\n")

    result = store.compare("fix-one", repo, binding={"policy": "2"})

    assert start["baseline_eligible"] is False
    assert result["changed_since_start"] == ["new file.py", "old.py"]
    assert result["preexisting_changed_paths"] == ["old.py"]
    assert result["unchanged_preexisting_paths"] == []
    assert result["attribution"] == "time_observation_only"
    assert result["authorization"] == "none"


def test_resume_preserves_original_observation_and_cannot_reset(tmp_path):
    repo = repository(tmp_path)
    store = TaskObservationStore(tmp_path / "runtime")
    start = store.start("fix-one", repo, binding={})
    (repo / "old.py").unlink()
    resumed = TaskObservationStore(tmp_path / "runtime")
    with pytest.raises(ValueError, match="already exists"):
        resumed.start("fix-one", repo, binding={})
    result = resumed.compare("fix-one", repo, binding={})
    assert result["start_observation_id"] == start["observation_id"]
    assert result["deleted_paths"] == ["old.py"]


def test_rename_is_observed_as_both_old_and_new_path(tmp_path):
    repo = repository(tmp_path)
    store = TaskObservationStore(tmp_path / "runtime")
    store.start("rename", repo, binding={})
    (repo / "old.py").rename(repo / "renamed.py")
    result = store.compare("rename", repo, binding={})
    assert result["changed_since_start"] == ["old.py", "renamed.py"]
    assert result["added_paths"] == ["renamed.py"]
    assert result["deleted_paths"] == ["old.py"]


@pytest.mark.parametrize("task_id", ["../escape", "/absolute", "", "a/b"])
def test_task_ids_cannot_escape_the_observation_store(tmp_path, task_id):
    repo = repository(tmp_path)
    with pytest.raises(ValueError, match="task id"):
        TaskObservationStore(tmp_path / "runtime").start(task_id, repo, binding={})


def test_missing_context_and_changed_policy_fail_closed(tmp_path):
    repo = repository(tmp_path)
    store = TaskObservationStore(tmp_path / "runtime")
    with pytest.raises(ValueError, match="does not exist"):
        store.compare("missing", repo, binding={})
    store.start("fix", repo, binding={"policy": "1"})
    with pytest.raises(ValueError, match="binding changed"):
        store.compare("fix", repo, binding={"policy": "2"})


def test_observation_store_must_be_outside_the_repository(tmp_path):
    repo = repository(tmp_path)
    with pytest.raises(ValueError, match="outside"):
        TaskObservationStore(repo / "runtime").start("fix", repo, binding={})


def test_symlinks_are_unknown_evidence_without_reading_the_target(tmp_path):
    repo = repository(tmp_path)
    (repo / "external.py").symlink_to(tmp_path / "absent-secret")
    result = observe_worktree(repo)
    assert result["records"]["external.py"]["state"] == "symlink"
    assert "symlink:external.py" in result["diagnostics"]


def test_git_failure_cannot_look_like_an_empty_clean_worktree(tmp_path):
    with pytest.raises(ValueError, match="git observation"):
        observe_worktree(tmp_path)


def test_cli_retains_task_observation_across_runs_without_changing_gate(tmp_path):
    import router_core

    repo = repository(tmp_path)
    router_core.bootstrap_bundle(repo, write=True)
    script = Path(__file__).resolve().parents[3] / "scripts/run_change_flow.py"
    command = [sys.executable, str(script), "--repo", str(repo), "--request",
               "Extend the existing Python source", "--changed-path", "old.py",
               "--runtime-dir", str(tmp_path / "runtime"), "--timeout-seconds", "20",
               "--task-id", "one", "--format", "full-json"]
    started = subprocess.run([*command, "--start-task"], capture_output=True, text=True)
    assert started.returncode in {0, 2}, started.stderr
    first = json.loads(started.stdout)
    (repo / "old.py").write_text("VALUE = 2\n")
    (repo / "new.py").write_text("VALUE = 3\n")
    resumed = subprocess.run(command, capture_output=True, text=True)
    assert resumed.returncode in {0, 2}, resumed.stderr
    second = json.loads(resumed.stdout)
    assert second["task_observation"]["start_observation_id"] == first["task_observation"]["start_observation_id"]
    assert second["task_observation"]["changed_since_start"] == ["new.py", "old.py"]
    assert "new.py" in second["working_index"]["paths"]
    assert second["working_index"]["source_observation_id"] == second["task_observation"]["current_observation_id"]
    assert second["execution_gate"]["state"] == "blocked"  # An observation grants no write authority.
