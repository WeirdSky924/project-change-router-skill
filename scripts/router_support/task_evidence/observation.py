from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from router_support.typed_findings import canonical_json, digest_value


TASK_OBSERVATION_SCHEMA_VERSION = 1


def _git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True,
            text=True, encoding="utf-8", timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise ValueError("git observation failed") from exc


def _record(repo: Path, relative: str) -> dict[str, Any]:
    path = repo / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("observation path escapes repository")
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != repo and repo in parent.parents):
        return {"state": "symlink"}
    if not path.exists():
        return {"state": "deleted"}
    if path.is_dir():
        return {"state": "directory"}
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise ValueError(f"observation cannot read {relative}") from exc
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if identity(before) != identity(after):
        raise ValueError(f"unstable observation: {relative}")
    # Runtime-owned evidence; never store source or secret contents in an observation.
    return {"state": "file", "size": len(content), "content_id": digest_value(content.hex()),
            "executable": bool(after.st_mode & 0o111)}


def observe_worktree(repo_root: Path) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    head = _git(repo, "rev-parse", "HEAD").strip()
    paths = set(filter(None, _git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")))
    changed: set[str] = set()
    for args in (("diff", "--name-only", "--no-renames", "-z"),
                 ("diff", "--cached", "--name-only", "--no-renames", "-z"),
                 ("ls-files", "--others", "--exclude-standard", "-z")):
        changed.update(filter(None, _git(repo, *args).split("\0")))
    records = {path: _record(repo, path) for path in sorted(paths | changed)}
    return {"repo_root": str(repo), "head": head, "records": records,
            "changed_paths": sorted(changed),
            "diagnostics": [f"{record['state']}:{path}" for path, record in records.items()
                            if record["state"] in {"symlink", "directory"}]}


class TaskObservationStore:
    """An immutable time observation, never a debt baseline or authorization."""

    def __init__(self, runtime_root: Path):
        self.root = Path(runtime_root).resolve() / "task-observations"

    def _path(self, task_id: str, repo_root: Path) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", task_id):
            raise ValueError("invalid task id")
        repo = Path(repo_root).resolve()
        if self.root == repo or repo in self.root.parents:
            raise ValueError("observation runtime must be outside repository")
        return self.root / f"{task_id}.json"

    def start(self, task_id: str, repo_root: Path, *, binding: Mapping[str, Any]) -> dict[str, Any]:
        path = self._path(task_id, repo_root)
        if path.exists():
            raise ValueError("task observation already exists; resume it")
        observation = {"schema_version": TASK_OBSERVATION_SCHEMA_VERSION,
                       "task_id": task_id, "state": "observation_only",
                       "baseline_eligible": False, "authorization": "none",
                       "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "binding": dict(binding), **observe_worktree(repo_root)}
        observation["observation_id"] = digest_value(observation)
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ValueError("task observation already exists; resume it") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(canonical_json(observation) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return observation

    def compare(self, task_id: str, repo_root: Path, *, binding: Mapping[str, Any]) -> dict[str, Any]:
        path = self._path(task_id, repo_root)
        if not path.is_file() or path.is_symlink():
            raise ValueError("task observation does not exist or is unsafe")
        try:
            start = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("invalid task observation") from exc
        if not isinstance(start, dict) or start.get("schema_version") != TASK_OBSERVATION_SCHEMA_VERSION:
            raise ValueError("invalid task observation schema")
        identity = start.get("observation_id")
        if identity != digest_value({k: v for k, v in start.items() if k != "observation_id"}):
            raise ValueError("invalid task observation evidence")
        if start.get("task_id") != task_id or start.get("repo_root") != str(Path(repo_root).resolve()):
            raise ValueError("task observation repository or task binding changed")
        if start.get("binding") != dict(binding):
            raise ValueError("task observation policy binding changed")
        current = observe_worktree(repo_root)
        old, new = start["records"], current["records"]
        missing = {"state": "deleted"}
        changes = sorted(p for p in old.keys() | new.keys() if old.get(p, missing) != new.get(p, missing))
        preexisting = start["changed_paths"]
        return {"task_id": task_id, "start_observation_id": identity,
                "current_observation_id": digest_value(current),
                "attribution": "time_observation_only", "authorization": "none",
                "baseline_eligible": False, "preexisting_changed_paths": preexisting,
                "unchanged_preexisting_paths": sorted(set(preexisting) - set(changes)),
                "changed_since_start": changes,
                "added_paths": [p for p in changes if old.get(p, missing)["state"] == "deleted"],
                "deleted_paths": [p for p in changes if new.get(p, missing)["state"] == "deleted"],
                "head_changed": start["head"] != current["head"],
                "diagnostics": sorted(set(start["diagnostics"] + current["diagnostics"]))}
