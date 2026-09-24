from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable, Mapping

from router_support.typed_findings import canonical_json, digest_value


WORKING_INDEX_SCHEMA_VERSION = 1


def _safe_task(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value):
        raise ValueError("invalid working-index task id")
    return value


def _match(pattern: str, path: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or (pattern.endswith("/**") and path.startswith(pattern[:-3].rstrip("/") + "/"))


class WorkingIndexStore:
    """External, task-scoped path observations; never writes repository bundles."""

    def __init__(self, runtime_root: Path):
        self.root = Path(runtime_root).resolve() / "working-index"

    def _path(self, task_id: str) -> Path:
        return self.root / f"{_safe_task(task_id)}.json"

    def _value(
        self,
        task_id: str,
        *,
        paths: Iterable[str],
        owner_patterns: Mapping[str, Iterable[str]],
        source_observation_id: str,
    ) -> dict[str, Any]:
        _safe_task(task_id)
        if not source_observation_id:
            raise ValueError("working index requires a source observation")
        normalized = sorted({str(path).replace("\\", "/").removeprefix("./") for path in paths if path})
        for path in normalized:
            if Path(path).is_absolute() or PureWindowsPath(path).drive or ".." in Path(path).parts:
                raise ValueError("working index path escapes repository")
        patterns_by_owner = {owner: sorted(set(patterns)) for owner, patterns in owner_patterns.items()}
        assignments: dict[str, str] = {}
        unknown: list[str] = []
        conflicts: list[str] = []
        for path in normalized:
            matches = sorted(owner for owner, patterns in patterns_by_owner.items() if any(_match(str(pattern), path) for pattern in patterns))
            if len(matches) == 1:
                assignments[path] = matches[0]
            elif len(matches) > 1:
                conflicts.append(path)
            else:
                unknown.append(path)
        result = {"schema_version": WORKING_INDEX_SCHEMA_VERSION, "task_id": task_id,
                  "state": "observation_only", "source_observation_id": source_observation_id,
                  "paths": normalized, "assignments": assignments,
                  "unknown_paths": unknown, "conflict_paths": conflicts,
                  "baseline_eligible": False, "write_authority": "none",
                  "owner_patterns_id": digest_value(patterns_by_owner)}
        result["record_id"] = digest_value(result)
        return result

    @staticmethod
    def _persist(path: Path, result: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(canonical_json(result) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def record(self, task_id: str, *, paths: Iterable[str],
               owner_patterns: Mapping[str, Iterable[str]], source_observation_id: str) -> dict[str, Any]:
        result = self._value(task_id, paths=paths, owner_patterns=owner_patterns,
                             source_observation_id=source_observation_id)
        path = self._path(task_id)
        try:
            self._persist(path, result)
        except FileExistsError as exc:
            raise ValueError("working index already exists; update requires explicit task event") from exc
        return result

    def observe(self, task_id: str, *, repo_root: Path, paths: Iterable[str],
                owner_patterns: Mapping[str, Iterable[str]], source_observation_id: str) -> dict[str, Any]:
        repo = Path(repo_root).resolve()
        if self.root == repo or repo in self.root.parents:
            raise ValueError("working index runtime must be outside repository")
        value = self._value(task_id, paths=paths, owner_patterns=owner_patterns,
                            source_observation_id=source_observation_id)
        value.pop("record_id")
        value["repo_root"] = str(repo)
        value["record_id"] = digest_value(value)
        path = self.root / "events" / task_id / f"{value['record_id']}.json"
        try:
            self._persist(path, value)
        except FileExistsError:
            if path.is_symlink() or self._load(path) != value:
                raise ValueError("invalid working index observation event")
        return value

    def load(self, task_id: str) -> dict[str, Any]:
        value = self._load(self._path(task_id))
        if value.get("task_id") != task_id:
            raise ValueError("invalid working index task binding")
        return value

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.is_file() or path.is_symlink():
            raise ValueError("working index does not exist or is unsafe")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schema_version") != WORKING_INDEX_SCHEMA_VERSION:
            raise ValueError("invalid working index schema")
        record_id = value.pop("record_id", None)
        if record_id != digest_value(value):
            raise ValueError("invalid working index evidence")
        value["record_id"] = record_id
        return value
