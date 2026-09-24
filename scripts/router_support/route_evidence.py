from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from router_support.typed_findings import TypedFinding
from router_support.finding_adapters import adapt_check_report


def _finding(
    finding_type: str,
    *,
    severity: str,
    invariant_class: str,
    origin: str,
    delta_state: str,
    relevance: str,
    evidence_status: str,
    policy_rule_id: str,
    paths: Iterable[str] = (),
    capabilities: Iterable[str] = (),
    evidence: Mapping[str, Any] | None = None,
    message: str = "",
) -> TypedFinding:
    return TypedFinding.create(
        type=finding_type,
        severity=severity,
        invariant_class=invariant_class,
        origin=origin,
        delta_state=delta_state,
        task_relevance=relevance,
        evidence_status=evidence_status,
        policy_rule_id=policy_rule_id,
        paths=paths,
        capabilities=capabilities,
        evidence=evidence,
        message=message,
    )


def build_route_findings(
    *,
    freshness: Mapping[str, Any],
    changed_paths: Iterable[str],
    primary_capability: str | None,
    primary_public_entries: Iterable[str],
    primary_internal_only: bool,
    owner_assessment: Mapping[str, Any],
    evaluation_passed: bool,
    evaluation_reasons: Iterable[str],
    high_risk: bool,
    lifecycle_intent: bool,
    capability_conflicts: Iterable[Mapping[str, Any]],
) -> list[TypedFinding]:
    paths = list(dict.fromkeys(str(path) for path in changed_paths if str(path)))
    capabilities = [primary_capability] if primary_capability else []
    findings: list[TypedFinding] = []
    assessment = freshness.get("route_assessment", {})
    classification = str(assessment.get("classification", "unknown"))
    comparison_complete = freshness.get("comparison_delta_complete") is True
    unknown_paths = list(assessment.get("unknown_changed_paths", []))
    relevant_paths = list(assessment.get("relevant_changed_paths", []))
    unrelated_paths = list(assessment.get("unrelated_changed_paths", []))

    for path in unknown_paths:
        findings.append(
            _finding(
                "unindexed_path",
                severity="P0",
                invariant_class="task_local",
                origin="freshness",
                delta_state="unknown",
                relevance="unknown",
                evidence_status="incomplete",
                policy_rule_id="GATE-PATH-001",
                paths=[path],
                evidence={"route_assessment": dict(assessment)},
                message="changed path has no proven capability mapping",
            )
        )
    if classification == "task_local_new":
        findings.append(
            _finding(
                "freshness_delta",
                severity="P1",
                invariant_class="closure_global",
                origin="freshness",
                delta_state="task_local_new",
                relevance="relevant",
                evidence_status="complete" if comparison_complete else "incomplete",
                policy_rule_id="GATE-FRESHNESS-001",
                paths=relevant_paths or paths,
                capabilities=assessment.get("relevant_capabilities", capabilities),
                evidence={"failure_reasons": freshness.get("failure_reasons", [])},
                message="freshness delta intersects the route dependency closure",
            )
        )
    elif classification == "baseline_unchanged" and freshness.get("status") == "fail":
        findings.append(
            _finding(
                "historical_freshness_debt",
                severity="P2",
                invariant_class="closure_global",
                origin="freshness",
                delta_state="baseline_unchanged",
                relevance="unrelated",
                evidence_status="complete" if comparison_complete else "incomplete",
                policy_rule_id="GATE-HISTORY-001",
                paths=unrelated_paths,
                capabilities=assessment.get("relevant_capabilities", capabilities),
                evidence={"failure_reasons": freshness.get("failure_reasons", [])},
                message="global freshness debt is proven outside the route closure",
            )
        )
    elif classification == "unknown" and not unknown_paths:
        findings.append(
            _finding(
                "freshness_unknown",
                severity="P0",
                invariant_class="closure_global",
                origin="freshness",
                delta_state="unknown",
                relevance="unknown",
                evidence_status="incomplete",
                policy_rule_id="GATE-FRESHNESS-UNKNOWN-001",
                paths=paths,
                capabilities=capabilities,
                evidence={"failure_reasons": freshness.get("failure_reasons", [])},
                message="freshness evidence cannot be localized safely",
            )
        )

    if not owner_assessment.get("trusted", False):
        reasons = [str(reason) for reason in owner_assessment.get("reasons", [])]
        duplicate = any("duplicate" in reason.lower() for reason in reasons)
        findings.append(
            _finding(
                "duplicate_owner" if duplicate else "owner_unknown",
                severity="P0",
                invariant_class="always_global",
                origin="ownership",
                delta_state="task_local_new" if duplicate else "unknown",
                relevance="relevant" if primary_capability else "unknown",
                evidence_status="complete" if duplicate else "incomplete",
                policy_rule_id="GATE-OWNER-001",
                paths=paths,
                capabilities=capabilities,
                evidence={"reasons": reasons},
                message="capability owner governance is incomplete",
            )
        )
    for conflict in capability_conflicts:
        findings.append(
            _finding(
                "duplicate_owner",
                severity="P0",
                invariant_class="always_global",
                origin="ownership",
                delta_state="task_local_new",
                relevance="relevant",
                evidence_status="complete",
                policy_rule_id="GATE-OWNER-CONFLICT-001",
                paths=paths,
                capabilities=capabilities,
                evidence=dict(conflict),
                message="capability ownership conflict exists",
            )
        )
    if primary_capability and not list(primary_public_entries) and not primary_internal_only:
        findings.append(
            _finding(
                "public_entry_unknown",
                severity="P1",
                invariant_class="always_global",
                origin="public_api",
                delta_state="unknown",
                relevance="relevant",
                evidence_status="incomplete",
                policy_rule_id="GATE-PUBLIC-ENTRY-001",
                paths=paths,
                capabilities=capabilities,
                message="routed capability has no public entry or internal-only contract",
            )
        )
    if not evaluation_passed:
        findings.append(
            _finding(
                "evaluation_policy_invalid",
                severity="P1",
                invariant_class="always_global",
                origin="evaluation",
                delta_state="unknown",
                relevance="relevant",
                evidence_status="stale",
                policy_rule_id="GATE-EVALUATION-001",
                paths=paths,
                capabilities=capabilities,
                evidence={"reasons": list(evaluation_reasons)},
                message="evaluation attestation does not authorize unattended writes",
            )
        )
    if high_risk:
        findings.append(
            _finding(
                "high_risk_surface",
                severity="P0",
                invariant_class="task_local",
                origin="route",
                delta_state="task_local_new",
                relevance="relevant",
                evidence_status="complete",
                policy_rule_id="GATE-RISK-001",
                paths=paths,
                capabilities=capabilities,
                message="route affects a high-risk surface",
            )
        )
    if lifecycle_intent:
        findings.append(
            _finding(
                "lifecycle_change",
                severity="P0",
                invariant_class="closure_global",
                origin="lifecycle",
                delta_state="task_local_new",
                relevance="relevant",
                evidence_status="complete",
                policy_rule_id="GATE-LIFECYCLE-001",
                paths=paths,
                capabilities=capabilities,
                message="capability lifecycle change requires explicit review",
            )
        )
    return sorted(findings, key=lambda item: item.finding_id)


FLOW_CHECKS = ("dependency", "public_api", "structure", "freshness", "governance", "reuse")


def merge_flow_findings(findings: Iterable[TypedFinding]) -> list[TypedFinding]:
    """Deduplicate identical evidence; disagreement is an explicit blocking fact."""
    unique: dict[str, TypedFinding] = {}
    conflicts: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        previous = unique.setdefault(finding.finding_id, finding)
        if previous.to_dict() != finding.to_dict():
            conflicts.setdefault(finding.finding_id, [previous.to_dict()]).append(finding.to_dict())
    for finding_id, variants in conflicts.items():
        conflict = _finding("evidence_conflict", severity="P1", invariant_class="always_global",
            origin="flow", delta_state="unknown", relevance="unknown", evidence_status="invalid",
            policy_rule_id="FLOW-EVIDENCE-CONFLICT", paths=unique[finding_id].paths,
            evidence={"finding_id": finding_id, "variants": variants})
        unique[conflict.finding_id] = conflict
    return sorted(unique.values(), key=lambda item: item.finding_id)


def normalize_flow_evidence(
    route_findings: Iterable[TypedFinding], checks: Mapping[str, Any], *,
    route_paths: Iterable[str], route_capabilities: Iterable[str],
    route_scope_paths: Iterable[str], relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconcile reanalyzed source freshness without waiving any actual finding.

    Persisted index knowledge, complete current checks and exact snapshot deltas
    are prerequisites. Task observations and working-index assignments cannot
    satisfy them. Raw global reports remain in the enclosing flow artifact.
    """
    paths, capabilities, scope = list(route_paths), list(route_capabilities), list(route_scope_paths)
    route = list(route_findings)
    complete = True
    findings: list[TypedFinding] = []
    for name in FLOW_CHECKS:
        report = checks.get(name)
        malformed = not isinstance(report, Mapping)
        report = report if isinstance(report, Mapping) else {}
        status = report.get("status", report.get("result_status"))
        raw = report.get("findings", [])
        malformed = malformed or status not in {"pass", "warn", "fail"} or not isinstance(raw, list)
        if isinstance(raw, list):
            malformed = malformed or any(not isinstance(item, Mapping) for item in raw)
        finished = (report.get("completion_status", "complete") == "complete"
                    and report.get("evidence_complete", True) is True and not report.get("flow_error"))
        if name == "reuse":
            finished = finished and report.get("completion_status") == "complete" and report.get("evidence_complete") is True
        adapted = [] if malformed else adapt_check_report(name, report, route_paths=paths,
            route_capabilities=capabilities, route_scope_paths=scope)
        # A failed check without accountable blocking evidence is never a pass.
        unexplained_failure = status == "fail" and name != "freshness" and not any(
            finding.severity in {"P0", "P1"} for finding in adapted)
        if malformed or not finished or unexplained_failure:
            complete = False
            adapted.append(_finding(f"{name}_evidence_incomplete", severity="P1",
                invariant_class="closure_global", origin=name, delta_state="unknown", relevance="unknown",
                evidence_status="invalid" if malformed or unexplained_failure else "incomplete",
                policy_rule_id=f"FLOW-{name.upper()}-EVIDENCE", paths=paths,
                evidence={"malformed": malformed, "unexplained_failure": unexplained_failure,
                          "completion_status": report.get("completion_status"), "flow_error": report.get("flow_error")},
                message=f"{name} cannot provide complete accountable evidence"))
        findings.extend(adapted)

    freshness = checks.get("freshness", {})
    freshness = freshness if isinstance(freshness, Mapping) else {}
    delta = freshness.get("snapshot_delta", {})
    delta = delta if isinstance(delta, Mapping) else {}
    failures = freshness.get("failure_reasons")
    source_only = (isinstance(failures, list) and all(isinstance(item, str) for item in failures)
                   and set(failures) <= {"source_commit", "structure_digest", "indexed_paths"})
    reanalyzed = (complete and relations.get("complete") is True
                  and source_only and delta.get("complete") is True
                  and delta.get("knowledge_changed_paths") == []
                  and freshness.get("comparison_delta_complete") is True
                  and freshness.get("unmapped_changed_paths") == [])
    reconciled = []
    if reanalyzed:
        # Unindexed, unknown, owner and policy findings are deliberately excluded.
        reconciled = [f.finding_id for f in route if f.origin == "freshness"
                      and f.type in {"freshness_delta", "historical_freshness_debt"}]
        route = [f for f in route if f.finding_id not in reconciled]
    if freshness.get("status") == "fail" and not reanalyzed and not any(f.origin == "freshness" for f in route):
        findings.append(_finding("freshness_unknown", severity="P1", invariant_class="closure_global",
            origin="freshness", delta_state="unknown", relevance="unknown", evidence_status="incomplete",
            policy_rule_id="FLOW-FRESHNESS-EVIDENCE", paths=paths,
            evidence={"failure_reasons": failures}, message="freshness cannot be reconciled safely"))
    return {"route_findings": merge_flow_findings(route), "check_findings": merge_flow_findings(findings),
            "output_complete": complete,
            "freshness_reconciliation": {"state": "reanalyzed_source_delta" if reanalyzed else "conservative",
                "reconciled_finding_ids": sorted(reconciled), "snapshot_delta_complete": delta.get("complete") is True,
                "knowledge_unchanged": delta.get("knowledge_changed_paths") == [],
                "current_checks_complete": complete, "baseline_promoted": False}}
