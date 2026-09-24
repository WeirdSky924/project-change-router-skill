from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from router_support.typed_findings import TypedFinding, digest_value


BASELINE_SCHEMA_VERSION = 1
BASELINE_BINDING_FIELDS = (
    "commit",
    "profile_digest",
    "bundle_digest",
    "structure_digest",
    "indexed_paths_digest",
    "scope_digest",
    "tool_version",
    "policy_version",
    "evidence_digest",
)


def _now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def baseline_binding(**values: str) -> dict[str, str]:
    values.setdefault("scope_digest", "global")
    missing = [field for field in BASELINE_BINDING_FIELDS if not values.get(field)]
    if missing:
        raise ValueError("baseline binding is incomplete: " + ", ".join(missing))
    return {field: str(values[field]) for field in BASELINE_BINDING_FIELDS}


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class EvidenceBaselineStore:
    def __init__(self, runtime_root: Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.candidates_root = self.runtime_root / "candidate-snapshots"
        self.baselines_root = self.runtime_root / "baselines"

    @staticmethod
    def _baseline_name(repo_id: str, binding: Mapping[str, str]) -> str:
        scope = str(binding.get("scope_digest", "global"))
        return repo_id if scope == "global" else f"{repo_id}--{scope[:16]}"

    def record_candidate(
        self,
        *,
        repo_id: str,
        binding: Mapping[str, str],
        findings: Iterable[TypedFinding],
        clean_worktree: bool,
        evidence_complete: bool,
        source: str = "local",
    ) -> dict[str, Any]:
        normalized_binding = baseline_binding(**dict(binding))
        serialized = [
            finding.to_dict()
            for finding in sorted(findings, key=lambda item: item.finding_id)
        ]
        identity = {
            "repo_id": repo_id,
            "binding": normalized_binding,
            "findings": serialized,
            "clean_worktree": bool(clean_worktree),
            "evidence_complete": bool(evidence_complete),
            "source": source,
        }
        fingerprint = digest_value(identity)
        snapshot = {
            "schema_version": BASELINE_SCHEMA_VERSION,
            "state": "candidate_snapshot",
            "snapshot_fingerprint": fingerprint,
            "created_at": _now(),
            **identity,
        }
        _atomic_json(self.candidates_root / f"{fingerprint}.json", snapshot)
        return snapshot

    def promote(self, snapshot_fingerprint: str, *, authority: str) -> dict[str, Any]:
        candidate_path = self.candidates_root / f"{snapshot_fingerprint}.json"
        if not candidate_path.is_file():
            raise ValueError("candidate snapshot does not exist")
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        if not candidate.get("clean_worktree"):
            raise ValueError("trusted baseline requires a clean worktree snapshot")
        if not candidate.get("evidence_complete"):
            raise ValueError("trusted baseline requires complete evidence")
        if not authority or authority == "automatic":
            raise ValueError("trusted baseline requires explicit promotion authority")
        baseline = {
            **candidate,
            "state": "trusted_baseline",
            "promoted_at": _now(),
            "promotion_authority": authority,
        }
        repo_id = str(candidate["repo_id"])
        baseline_name = self._baseline_name(repo_id, candidate["binding"])
        baseline_path = self.baselines_root / f"{baseline_name}.json"
        if baseline_path.is_file():
            prior = json.loads(baseline_path.read_text(encoding="utf-8"))
            if prior.get("state") == "trusted_baseline":
                superseded = {
                    **prior,
                    "state": "superseded",
                    "superseded_at": _now(),
                    "superseded_by": baseline["snapshot_fingerprint"],
                }
                history = self.baselines_root / "history"
                _atomic_json(
                    history / f"{prior['snapshot_fingerprint']}.json",
                    superseded,
                )
        _atomic_json(baseline_path, baseline)
        return baseline

    def load_trusted(
        self, repo_id: str, binding: Mapping[str, str]
    ) -> dict[str, Any] | None:
        current_binding = baseline_binding(**dict(binding))
        baseline = self._load_validated(repo_id, current_binding)
        if baseline is None:
            return None
        persisted_binding = baseline.get("binding", {})
        identity_fields = [
            field for field in BASELINE_BINDING_FIELDS if field != "evidence_digest"
        ]
        if any(
            persisted_binding.get(field) != current_binding.get(field)
            for field in identity_fields
        ):
            return None
        return baseline

    def _load_validated(self, repo_id: str, binding: Mapping[str, str]) -> dict[str, Any] | None:
        path = self.baselines_root / f"{self._baseline_name(repo_id, binding)}.json"
        if not path.is_file() or path.is_symlink():
            return None
        try:
            baseline = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(baseline, dict) or (
                baseline.get("schema_version") != BASELINE_SCHEMA_VERSION
                or baseline.get("repo_id") != repo_id
                or baseline.get("state") != "trusted_baseline"
                or baseline.get("clean_worktree") is not True
                or baseline.get("evidence_complete") is not True
                or not baseline.get("promotion_authority")
            ):
                return None
            baseline_binding(**baseline["binding"])
            identity = {key: baseline[key] for key in (
                "repo_id", "binding", "findings", "clean_worktree", "evidence_complete", "source")}
            if baseline.get("snapshot_fingerprint") != digest_value(identity):
                return None
            if not isinstance(baseline["findings"], list):
                return None
            for finding in baseline["findings"]:
                TypedFinding.from_dict(finding)
            return baseline
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return None

    def load_comparison(
        self, repo_id: str, binding: Mapping[str, str], *, repo_root: Path,
    ) -> dict[str, Any] | None:
        """Load trusted history for delta comparison, never as current pass evidence.

        Content may change; policy, ownership/index knowledge and scope may not.
        The full current checks still run before classification or gate reduction.
        """
        current = baseline_binding(**dict(binding))
        baseline = self._load_validated(repo_id, current)
        if baseline is None:
            return None
        try:
            prior = baseline_binding(**baseline["binding"])
            stable = set(BASELINE_BINDING_FIELDS) - {"commit", "structure_digest", "evidence_digest"}
            if any(prior[key] != current[key] for key in stable):
                return None
            for commit in (prior["commit"], current["commit"]):
                if not commit or any(c not in "0123456789abcdef" for c in commit) or len(commit) not in {40, 64}:
                    return None
            result = subprocess.run(["git", "-C", str(repo_root), "merge-base", "--is-ancestor",
                                     prior["commit"], current["commit"]], capture_output=True, timeout=15)
            if result.returncode != 0:
                return None
            return baseline
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
            return None


def _numeric_delta(current: Mapping[str, Any], prior: Mapping[str, Any]) -> str:
    comparable = sorted(set(current) & set(prior))
    increased = False
    decreased = False
    for key in comparable:
        left = current[key]
        right = prior[key]
        if isinstance(left, bool) or isinstance(right, bool):
            continue
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            increased = increased or left > right
            decreased = decreased or left < right
    if increased:
        return "task_local_expanded"
    if decreased and not increased:
        return "baseline_reduced"
    return "task_local_expanded"


def classify_against_baseline(
    findings: Iterable[TypedFinding],
    baseline: Mapping[str, Any] | None,
    *,
    evidence_complete: bool = True,
) -> list[TypedFinding]:
    prior_by_id = {
        str(item.get("finding_id")): item
        for item in (baseline or {}).get("findings", [])
        if isinstance(item, Mapping) and item.get("finding_id")
    }
    classified: list[TypedFinding] = []
    current_ids: set[str] = set()
    for finding in findings:
        current_ids.add(finding.finding_id)
        prior = prior_by_id.get(finding.finding_id)
        if prior is None:
            state = "task_local_new" if baseline else finding.delta_state
        elif prior.get("evidence_digest") == finding.evidence_digest:
            state = "baseline_unchanged"
        else:
            state = _numeric_delta(
                dict(finding.evidence), dict(prior.get("evidence", {}))
            )
        classified.append(finding.with_classification(delta_state=state))
    if baseline and evidence_complete:
        for finding_id in sorted(set(prior_by_id) - current_ids):
            prior = TypedFinding.from_dict(prior_by_id[finding_id])
            classified.append(
                prior.with_classification(
                    delta_state="resolved",
                    task_relevance="unrelated",
                    evidence_status="complete",
                )
            )
    return sorted(classified, key=lambda item: item.finding_id)
