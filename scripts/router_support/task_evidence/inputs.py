from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Mapping

from router_support.typed_findings import digest_value


REUSE_INPUT_SUFFIXES = frozenset({".py", ".java", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".sql"})
CONFIG_SUFFIXES = frozenset({".json", ".yaml", ".yml", ".toml", ".xml", ".cfg", ".ini"})
EXCLUDED_PARTS = frozenset({".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build", "coverage"})


def repository_input_paths(repo: Path) -> list[str]:
    try:
        result = subprocess.run(["git", "-C", str(repo), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                                capture_output=True, text=True, check=True, timeout=30)
        return sorted(set(filter(None, result.stdout.split("\0"))))
    except (OSError, subprocess.SubprocessError):
        # Ungoverned repositories keep complete observed files; this is not clean Git proof.
        return sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*")
                      if p.is_file() and not EXCLUDED_PARTS.intersection(p.relative_to(repo).parts))


def reuse_input_records(repo: Path, route_paths: list[str]) -> list[dict[str, Any]]:
    records = []
    for relative in sorted(set(repository_input_paths(repo)) | set(route_paths)):
        path = repo / relative
        if path.suffix.lower() not in REUSE_INPUT_SUFFIXES | CONFIG_SUFFIXES and relative not in route_paths:
            continue
        if EXCLUDED_PARTS.intersection(Path(relative).parts):
            continue
        if relative.startswith("project-change-router/reports/"):
            continue
        if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.resolve().is_relative_to(repo.resolve()):
            raise ValueError("evidence input escapes repository")
        if path.is_symlink():
            records.append({"path": relative, "state": "symlink", "target": str(path.readlink())})
        elif path.is_file():
            records.append({"path": relative, "state": "file", "content_digest": hashlib.sha256(path.read_bytes()).hexdigest()})
        else:
            records.append({"path": relative, "state": "deleted"})
    return records


def reuse_cache_input(repo: Path, common: Mapping[str, Any], route_paths: list[str]) -> str:
    # Cross-capability duplicate candidates remain inputs, including clean files.
    # Whole-repository prose and its content digest are not reuse inputs.
    identity = {key: common[key] for key in (
        "profile_digest", "bundle_digest", "indexed_paths_digest", "runtime_identity_digest")}
    return digest_value({**identity, "route_paths": route_paths,
                         "source_records": reuse_input_records(repo, route_paths)})
