# PCR 0.5 Task-Aware Evidence Upgrade

## Plan State

- status: complete_reviewable
- current_package: PCR 0.5 implementation, compatibility, regression and isolated installation complete; publication intentionally not authorized
- current_executable_entry: none; hold for independent review and explicit publication decision
- last_reviewed: 2026-09-24
- workspace: /home/code_workspace/pcr-0.5-AHNE35
- installed_source: /root/.codex/skills/project-change-router (preserved; no in-place development)
- scope: task observations; layered freshness and working index; precise relevance/cache; unified findings/gate; compatible 0.5 release candidate
- authorization: user asked to write a plan and start upgrading; no commit/push/PR or live product execution
- collaboration: main-thread fallback; prior collaboration objective exhausted caller-error budget; no further collaboration calls for this objective
- manual checksum validation: skipped_by_user_scope; runtime-generated provenance remains tool-owned
- preexisting_changes: seven authorization-envelope files carried unchanged into this worktree before upgrade edits
- acceptance: deterministic complete CLI behavior, preserved hard gates, prior authorization regressions, full test suite and isolated installation
- stop: new scope/authority, unsafe baseline promotion, unknown relevant evidence or destructive/shared-state operation

## Packages

- [x] P0: Preserve existing changes; establish test baseline and scoped source contracts.
- [x] P1: Persist immutable task observations; classify preexisting/changed-during-task/unattributed changes without promoting debt or asserting authorship.
- [x] P2: Separate content/path/knowledge freshness; add governed transient path ownership with explicit artifact handling and conservative legacy mode.
- [x] P3: Recompute affected directed relationships; remove irrelevant global content from local cache keys while preserving all global checks and baseline provenance.
- [x] P4: Normalize route/check findings once; distinguish ordinary source delta from actual violations/unknown evidence; deduplicate report evidence; retain shadow comparison.
- [x] P5: Version/docs/schema compatibility, complete regression, real CLI cold/warm and adversarial fixtures, isolated install/rollback verification; leave publication reviewable.

## Boundary And Reuse

Use existing router_support owners: freshness_checks, incremental_evidence, evidence_baseline, route_evidence, execution_gate, authorization_manifest, typed_findings and change_flow. The route-freshness assessment now lives in `freshness_checks`; `router_core` retains only a compatibility import and delegates to that owner. Keep legacy resolver/check semantics conservative until complete new-flow evidence can support the v2 gate. A task observation is not a trusted baseline or grant. Unknown owner/parse/dependency evidence, global conflicts, incomplete reuse and consumed grants remain fail-closed.

Do not bootstrap/rebuild the Godview bundle or edit its product tree. Working index data stays in the PCR runtime directory, separate from protected generated references. No broad ignore rules or automatic adoption of dirty debt. Existing project policies may remain stricter.

## Verification Matrix

- Meaningful logic changes: focused RED then GREEN and affected regression.
- Same-file changes, deletions, renames, path escape/symlink and missing context fail safely.
- New known-owner paths can be analyzed; unknown/conflicting ownership still blocks.
- Same capability alone does not prove current-task authorship; related and unknown code still gets checked.
- Shared dependencies and reverse callers remain visible; dynamic/unsupported evidence cannot prove unrelatedness.
- Unrelated content preserves valid local cache; relevant source/config/parser/policy changes invalidate it.
- Dirty observations cannot promote trusted debt; baseline ancestry and policy changes are handled explicitly.
- Old/new gate disagreement is explained; generated cache never conceals product or protected input.
- Cold/warm CLI results agree; malformed evidence is rejected.
- No automatic bundle write, grant revival, source-install overwrite or publication.

## Execution Record

- Initial source contains PCR 0.4.0 and seven uncommitted authorization narrowing changes. Preserved in this detached worktree.
- Baseline: `conda run -n godview python -m pytest tests/governance tests/freshness tests/routing/freshness tests/routing/decision/test_authorization_manifest_state.py tests/routing/decision/test_route_authorization_audit.py -q` -> 163 passed in 10.64s, exit 0.
- First broad diagnostic route was seed/review with missing bundle evidence; no product writes followed. The refined P1 route is `route-20260923-120548-86a00d50`, persisted by PCR at `/tmp/pcr-0.5-initial-route.json`, exit 2, `execution_gate=blocked`, primary `scripts`, provisional scripts/tests ownership and no persisted freshness snapshot.
- P1 exact proposed writes: `scripts/router_support/task_observation.py`, `scripts/router_support/change_flow.py`, `scripts/run_change_flow.py`, `tests/governance/test_task_observation.py`. Source reads confirm this extends the existing router-support/change-flow owner. No Godview product or protected bundle is included.
- The route supports a current-task/path-specific override and requires an explicit recorded user confirmation. No grant has been created or consumed. Normal upgrade authorization has not been represented as an override.
- Next: obtain the exact P1 override or a user-selected governance-bootstrap boundary; then persist/consume the supported grant against fresh inputs and start the behavior RED tests. Do not patch the router to bypass its own stop, fabricate owners, or silently bootstrap a new bundle.
- User confirmed `授权` in response to the concrete PCR 0.5 plan-scoped override question. This authorizes the diagnosed missing self-index/provisional-owner stops for this upgrade's named packets only. Fresh route-bound grants are recorded/consumed per packet; other hard invariants, product scopes, manual-checksum prohibition and no-publication boundary remain effective. The previous authorization stop is resolved, not a permission to fabricate a passed gate.
- P1 route `route-20260923-120824-c53e3666`, exact four paths; grant consumed once through the existing authorization CLI. RED: missing task-observation module; GREEN: focused observation and flow regression passed. Observation records are external, immutable, non-authorizing; CLI start/resume preserves the same task identity.
- P2 RED/GREEN: layered freshness and external working-index focused tests pass (`16 passed` before flow integration). Path-set, content and routing-knowledge status are now reported separately; known-owner working assignments remain observation-only while unknown/conflicting paths stay visible.
- Remaining implementation envelope used the existing freshness/index, baseline/cache, findings/gate/flow owners, plus focused task-evidence modules/tests, report schemas and release documentation. The oversized `router_core` freshness classifier was extracted into its canonical `freshness_checks` owner; no installed PCR or Godview path is in this write set.
- 2026-09-24 recovery: terminal tools available; abandoned process 92449 cannot be recovered. Reran its tests: 39 passed / 1 failed. Root cause was an unborn Git fixture, not a reason to weaken snapshot completeness. The fixture now has a commit; a separate test preserves missing-HEAD failure behavior.
- Fresh route `route-20260924-020007-4cafdc32` covers 11 P2/P3 files inside the prior 44-path envelope. New single-use grant `3a67d2facb7e1583e3db9ad236ad859af25d8475042502666186ff9cffcec3e5` was consumed before edits. Old grants remain consumed. The seed self-governance findings remain visible, not marked passed.
- RED 3 -> GREEN 75: missing freshness checks stay unknown; directed import closure is integrated without sibling propagation; deleted source relationships remain incomplete. RED 6 -> GREEN 198: damaged trusted baselines rejected, absolute/escaping route paths rejected, comparison baseline separated from current evidence and bound to complete runtime identity.
- Latest regression: `conda run -n godview python -m pytest tests/governance tests/freshness tests/routing/freshness tests/routing/decision/test_authorization_manifest_state.py tests/routing/decision/test_route_authorization_audit.py -q` -> 198 passed in 15.58s. Full suite, CLI adversarial matrix and isolated installation are still pending.
- File split audit: freshness_checks/__init__.py (565), layers.py (65), incremental_evidence.py (524), evidence_inputs.py (54), path_relations.py (54), evidence_baseline.py (250), change_flow.py (642), freshness tests (45), precise-evidence tests (73), baseline tests (210), integration tests (74), all initial counts under 800, `under_threshold_same_owner`. New logic stays in its existing dedicated owner; no new sibling was added in this recovery packet. router_core extraction in P4 must reduce its oversized baseline rather than add behavior there.
- P2 working-index recovery packet: route `route-20260924-020944-85769afa`; grant `1da6bd90d0d31931cc020877169ecc7d34744474d7ed1908ccdc1aa864fdb8a0` consumed before edits. RED 6 -> GREEN 20. Flow now records each current observation as an immutable external event, includes preexisting/current/requested paths, preserves the original task start, rejects escaping paths, and never grants authority. Final file sizes: working_index 126, change_flow 639, observation tests 126, working-index tests 62; all `under_threshold_same_owner`, no added sibling in this packet.
- Final code verification: `conda run -n godview python -m pytest -q` -> **756 passed, 3 subtests passed in 65.70s**, exit 0. `git diff --check` -> exit 0. `git check-ignore -v` over the ten new plan/source/test files -> no output, exit 1. `conda run -n godview python /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/code_workspace/pcr-0.5-AHNE35` -> `Skill is valid!`, exit 0. No source edits followed this full test run.
- Post-change unified CLI: `conda run -n godview python scripts/run_change_flow.py --repo /home/code_workspace/pcr-0.5-AHNE35 --request 'Read-only verification of the PCR 0.5 freshness, comparison evidence and working-index implementation packet.' <14 exact changed paths from the P2/P3 and working-events route union> --runtime-dir /tmp/pcr-0.5-verification-runtime --timeout-seconds 20 --format text --output /tmp/pcr-0.5-post-change-flow.json` -> exit 2, gate blocked, output_complete false. Original full report: `/tmp/pcr-0.5-verification-runtime/flow-artifacts/28eced08c1818ef17bf775d8e7f86b771224997100994b142c074247115dc4fe.json`. Runtime provenance was recorded only; manual checksum validation was skipped_by_user_scope.
- CLI checks: dependency/public API pass (0 findings); freshness fail (no persisted self-index); governance warn; structure fail with two new directory-width findings; reuse warn/bounded/evidence_complete=false. Scope is project-documentation/scripts/tests, 14 candidates, 146 owners, 86 comparisons, 37 size-prefilter skips. No duplicate-absence claim. No identical retry or budget enlargement was performed.

## Current Stop And Requested Scope

The earlier 44-path grant is consumed and the self-governance exception remained limited to missing self-index/provisional owners. Broad request `d8c376f24762ee0759549e4427f4ae9a96d33a0a31d76308275435eec6a93d4a` and exact request `5958d741e803f2e0c9acc6d7500590b860f25786b99eb27010394e2032ba7012` remain requested-only history. The later approved contract route `route-20260924-022621-ed13ed94` used grant `bb39ff0f6c4739e8d65f944ccfc8362f952e234c87ee5b1d8673d2227f04c2a4`, consumed once before structural/report edits. Runtime identity/provenance remained tool-owned and was not independently validated.

The post-change structure check initially found actual growth (`scripts/router_support` 34 -> 38 and `tests/governance` 9 -> 11). The approved `structure=deepen` repair moved those modules into the task-evidence owner and returned both counts to baseline; no compatibility facade or baseline waiver was used.

The approved exact destinations were:

- `scripts/router_support/task_evidence/__init__.py`
- `scripts/router_support/task_evidence/observation.py` from `task_observation.py`
- `scripts/router_support/task_evidence/working_index.py` from `working_index.py`
- `scripts/router_support/task_evidence/inputs.py` from `evidence_inputs.py`
- `scripts/router_support/task_evidence/relations.py` from `path_relations.py`
- `tests/governance/task_evidence/test_observation.py` from `test_task_observation.py`
- `tests/governance/task_evidence/test_precise_evidence.py` from `test_precise_evidence.py`

Report-contract work is implemented in the approved PCR 0.5 schemas and existing reducer/flow owners. It does not weaken unknown/owner/dependency/generated-output invariants, install over the live copy, modify Godview, rebuild its bundle, or publish.

### Scope confirmation received

User replied `授权` to the exact request above. The seven new structural destinations and report-schema/gate compatibility scope are now approved for this upgrade; prior grants remain consumed or ungranted history. Use a fresh current-input grant. Preserve all other stops and the no-publication/live-install boundary. Put P4 normalization into existing `route_evidence.py` and freshness assessment into `freshness_checks/layers.py` instead of creating flat `flow_v2.py`/`route_freshness.py`; use existing focused integration/output tests instead of adding another flat governance test. This keeps one owner and removes, rather than baselines away, the two width findings.

### Final P4/P5 evidence

- Structural relocation: `scripts/router_support/task_evidence/{observation,working_index,inputs,relations}.py` and `tests/governance/task_evidence/{test_observation,test_precise_evidence}.py`; the two growth findings returned to baseline. Schema directories remain protected freshness inputs but are excluded from code tree-width accounting.
- P4 RED/GREEN: 24 focused tests covering source-only delta reconciliation, incomplete knowledge/bounded/malformed evidence conservatism, duplicate/conflict normalization, and per-file coverage mismatch.
- Version/docs/schema: skill and package `0.5.0`; bundle schema v1 and API v1/v2 compatibility retained; added task-observation/working-index schemas, per-file index records, migration notes, and 0.5 README/SKILL guidance.
- Final regression: `conda run -n godview python -m pytest -q` -> **771 passed, 3 subtests passed in 87.69s**, exit 0.
- Installation: staging `/tmp/pcr-0.5-codex.YoRzTy`; installer and `--verify-only` both exit 0, report `version=0.5.0`, `reuse_api=2`, `architecture_api=2`, `repository_bundles_modified=0`.
- Static/package: quick validator `Skill is valid!`; `compileall -q scripts` exit 0; `npm pack --dry-run --json` reported 159 files with no runtime artifacts; `git diff --check` exit 0; new tracked candidates are not ignored.
- Final structure: `check_structure.py --repo . --format json` exit 0 with only pre-existing P2 width warnings (`scripts/router_support` 34, `tests/governance` prefix debt 9); no new P1/P0 structure finding.
- Final cold CLI: `run_change_flow.py` on this skill checkout exited 2 with `gate=blocked`, `output_complete=false`, six cache misses and a content-addressed artifact. This is expected because the checkout has no repository-local bundle/self-index; it confirms fail-closed behavior and does not authorize bootstrap. Warm equivalence and adversarial path/legacy fixtures are covered by the full suite.
- Manual checksum validation remains `skipped_by_user_scope`; runtime-generated identity/provenance was recorded, not independently recomputed.
- Final post-extraction regression: `conda run -n godview python -m pytest -q` -> **771 passed, 3 subtests passed in 74.24s**, exit 0; focused route/freshness/integration tests were 33 passed in 5.60s.
