from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping


def knowledge_path(path: str) -> bool:
    return (path in {".project-change-router.yaml", ".project-change-router.yml",
                     "project-change-router.profile.yaml", "project-change-router.profile.yml"}
            or path.startswith("project-change-router/references/")
            or path.startswith("project-change-router/schemas/")
            or path == "project-change-router/router-config.yaml")


def compare_snapshot_records(current: Any, indexed: Mapping[str, Any]) -> dict[str, Any]:
    before = indexed.get("file_records")
    if not isinstance(before, list) or any(
        not isinstance(x, Mapping) or not isinstance(x.get("path"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(x.get("content_digest", "")))
        or not isinstance(x.get("executable"), bool)
        or not x["path"] or PurePosixPath(x["path"]).is_absolute()
        or PureWindowsPath(x["path"]).drive or ".." in PurePosixPath(x["path"]).parts
        for x in before
    ):
        return {"complete": False, "reason": "legacy_or_invalid_file_records"}
    old = {x["path"]: dict(x) for x in before}
    if len(old) != len(before):
        return {"complete": False, "reason": "duplicate_file_records"}
    if "indexed_paths" in indexed and (
        not isinstance(indexed["indexed_paths"], list)
        or any(not isinstance(p, str) for p in indexed["indexed_paths"])
        or set(indexed["indexed_paths"]) != set(old)
    ):
        return {"complete": False, "reason": "file_record_coverage_mismatch"}
    new = {x["path"]: dict(x) for x in current.file_records}
    added, removed = sorted(new.keys() - old.keys()), sorted(old.keys() - new.keys())
    modified = sorted(p for p in new.keys() & old.keys() if new[p] != old[p])
    changed = sorted(set(added + removed + modified))
    return {"complete": not current.diagnostics, "added_paths": added, "removed_paths": removed,
            "content_changed_paths": modified, "changed_paths": changed,
            "knowledge_changed_paths": [p for p in changed if knowledge_path(p)]}


def _details(report: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    for check in report.get("checks", []) or []:
        if isinstance(check, Mapping) and check.get("name") == name:
            value = check.get("details", {})
            return value if isinstance(value, Mapping) else {}
    return {}


def classify_freshness_layers(
    report: Mapping[str, Any],
    *,
    changed_paths: Iterable[str] = (),
) -> dict[str, Any]:
    """Separate path-set, content and routing-knowledge freshness.

    A layer describes evidence only. It never changes the execution gate or grants
    an owner to a path. Unknown mapping remains unknown.
    """
    changed = sorted({str(path).replace("\\", "/").strip("/") for path in changed_paths if path})
    path_details = _details(report, "indexed_paths")
    coverage_details = _details(report, "changed_path_coverage")
    path_changes = sorted(set(path_details.get("missing_from_index", [])) | set(path_details.get("stale_in_index", [])))
    unmapped = sorted(str(path) for path in coverage_details.get("unmapped", []) if path)
    content_failed = "structure_digest" in report.get("failure_reasons", [])
    path_failed = "indexed_paths" in report.get("failure_reasons", [])
    knowledge_failed = "changed_path_coverage" in report.get("failure_reasons", [])
    observed = {check.get("name") for check in report.get("checks", []) or [] if isinstance(check, Mapping)}
    def status(name: str, failed: bool, failure: str) -> str:
        if failed:
            return failure
        return "current" if name in observed else "unknown"
    return {
        "path_set": {"status": status("indexed_paths", path_failed, "stale"), "changed_paths": path_changes},
        "content": {"status": status("structure_digest", content_failed, "changed"), "changed_paths": changed},
        "routing_knowledge": {"status": status("changed_path_coverage", knowledge_failed, "unknown"), "unmapped_paths": unmapped},
        "requires_reanalysis": sorted(set(path_changes) | (set(changed) if content_failed else set())),
        "write_authority": "unchanged",
    }
