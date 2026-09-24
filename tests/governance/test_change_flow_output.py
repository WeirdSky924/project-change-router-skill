from __future__ import annotations

import json

import pytest

from router_support.change_flow import (
    SAFE_ENVELOPE_FIELDS,
    compact_flow_output,
    persist_flow_artifact,
)


def _report() -> dict:
    return {
        "action": "extend",
        "primary_capability": "workflow",
        "execution_gate": {
            "state": "conditional",
            "unknown_evidence": [],
        },
        "veto_reasons": [],
        "allowed_write_paths": ["app/workflow/**"],
        "forbidden_write_paths": ["legacy/**"],
        "unknown_evidence": [],
        "artifact_path": "runtime/full.json",
        "artifact_digest": "a" * 64,
        "output_complete": True,
        "required_commands": ["python check.py"],
        "recommended_next_action": "run_required_commands",
        "candidate_capabilities": [{"id": "workflow", "score": 0.9}],
        "full_diagnostics": {"large": [1, 2, 3]},
    }


def test_compact_projection_cannot_hide_safety_envelope() -> None:
    compact = compact_flow_output(_report(), fields=["action"])

    assert set(SAFE_ENVELOPE_FIELDS) <= set(compact)
    assert compact["action"] == "extend"
    assert "candidate_capabilities" not in compact
    assert "full_diagnostics" not in compact


def test_artifact_reference_mode_keeps_only_envelope_and_next_command() -> None:
    compact = compact_flow_output(_report(), artifact_reference=True)

    assert set(compact) == set(SAFE_ENVELOPE_FIELDS) | {
        "action",
        "primary_capability",
        "recommended_next_action",
        "required_commands",
    }


def test_explicit_safety_envelope_exclusion_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be excluded"):
        compact_flow_output(
            _report(),
            exclude_fields=["execution_gate"],
        )


def test_persisted_artifact_is_content_addressed_and_readable(tmp_path) -> None:
    path, digest = persist_flow_artifact(tmp_path, {"report": "full"})

    assert path.name == f"{digest}.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"report": "full"}


def _checks():
    checks = {name: {"status": "pass", "findings": [], "completion_status": "complete",
                     "evidence_complete": True} for name in
              ("dependency", "public_api", "structure", "governance", "reuse", "freshness")}
    checks["freshness"].update(status="fail", failure_reasons=["structure_digest", "indexed_paths"],
        comparison_delta_complete=True, unmapped_changed_paths=[],
        snapshot_delta={"complete": True, "knowledge_changed_paths": [], "changed_paths": ["app/new.py"]})
    return checks


def _delta_finding(**overrides):
    from router_support.typed_findings import TypedFinding
    values = dict(type="freshness_delta", origin="freshness", severity="P1",
        invariant_class="closure_global", delta_state="task_local_new", task_relevance="relevant",
        evidence_status="complete", policy_rule_id="GATE-FRESHNESS-001", paths=["app/new.py"])
    return TypedFinding.create(**{**values, **overrides})


def test_current_complete_analysis_reconciles_source_delta_not_other_stops():
    from router_support.route_evidence import normalize_flow_evidence
    delta = _delta_finding()
    owner = _delta_finding(type="owner_unknown", origin="ownership", evidence_status="incomplete")
    result = normalize_flow_evidence([delta, owner], _checks(), route_paths=["app/new.py"],
        route_capabilities=["app"], route_scope_paths=["app"], relations={"complete": True, "closure_paths": ["app/new.py"]})
    assert [f.type for f in result["route_findings"]] == ["owner_unknown"]
    assert result["freshness_reconciliation"]["reconciled_finding_ids"] == [delta.finding_id]
    assert result["freshness_reconciliation"]["state"] == "reanalyzed_source_delta"


@pytest.mark.parametrize("cause", ["legacy", "knowledge", "unmapped", "bounded", "ancestry", "missing_check"])
def test_incomplete_or_changed_knowledge_never_reconciles_freshness(cause):
    from router_support.route_evidence import normalize_flow_evidence
    checks = _checks()
    if cause == "legacy":
        checks["freshness"]["snapshot_delta"] = {"complete": False}
    elif cause == "knowledge":
        checks["freshness"]["snapshot_delta"]["knowledge_changed_paths"] = [".project-change-router.yaml"]
    elif cause == "unmapped":
        checks["freshness"]["unmapped_changed_paths"] = ["new.py"]
    elif cause == "bounded":
        checks["reuse"].update(completion_status="bounded", evidence_complete=False)
    elif cause == "ancestry":
        checks["freshness"]["comparison_delta_complete"] = False
    else:
        checks.pop("dependency")
    result = normalize_flow_evidence([_delta_finding()], checks, route_paths=["app/new.py"],
        route_capabilities=["app"], route_scope_paths=["app"], relations={"complete": True, "closure_paths": ["app/new.py"]})
    assert any(f.type == "freshness_delta" for f in result["route_findings"])
    assert result["freshness_reconciliation"]["state"] == "conservative"


@pytest.mark.parametrize("report", [{}, {"status": "fail", "findings": []},
                                  {"status": "pass", "findings": [None]},
                                  {"status": "pass", "findings": "invalid"}])
def test_malformed_or_unexplained_check_results_produce_unknown_finding(report):
    from router_support.route_evidence import normalize_flow_evidence
    checks = _checks()
    checks["dependency"] = report
    result = normalize_flow_evidence([], checks, route_paths=["app/new.py"],
        route_capabilities=["app"], route_scope_paths=["app"], relations={})
    assert result["output_complete"] is False
    assert any(f.task_relevance == "unknown" and f.origin == "dependency" for f in result["check_findings"])


def test_duplicate_findings_are_deduplicated_but_conflicting_evidence_blocks():
    from router_support.route_evidence import merge_flow_findings
    same = _delta_finding()
    assert len(merge_flow_findings([same, same])) == 1
    other = _delta_finding(evidence={"different": True})
    merged = merge_flow_findings([same, other])
    assert any(f.type == "evidence_conflict" and f.evidence_status == "invalid" for f in merged)
