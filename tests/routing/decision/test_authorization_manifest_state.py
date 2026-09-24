from __future__ import annotations

import datetime as dt

import pytest

import router_support.authorization_manifest as authorization_manifest
import manage_authorization
from router_support.authorization_manifest import AuthorizationManifestStore
from router_support.typed_findings import digest_value


def _context(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "route_fingerprint": "a" * 64,
        "pre_change_snapshot": "b" * 64,
        "task_id": "task-1",
        "paths": ["app/service.py"],
        "owner": "workflow-runtime",
        "canonical_root": "app/services/workflow",
        "route": "extend",
        "mutation_envelope": {
            "allowed_write_paths": ["app/services/workflow/**"],
            "forbidden_write_paths": ["legacy/**"],
        },
    }
    values.update(overrides)
    return values


def test_request_does_not_create_authority(tmp_path) -> None:
    store = AuthorizationManifestStore(tmp_path)

    request = store.create_request(_context())

    assert request["state"] == "requested"
    assert store.active_grant(request["request_id"], _context()) is None


def test_new_mutation_envelope_intersects_explicit_normalized_paths() -> None:
    envelope = authorization_manifest.build_authorization_mutation_envelope(
        [
            "app\\services\\workflow\\runner.py",
            "app/services/workflow/private/secret.py",
            "docs/guide.md",
        ],
        ["app/services/workflow/**", "docs/*.md"],
        ["app/services/workflow/private/**"],
    )

    assert envelope == {
        "allowed_write_paths": [
            "app/services/workflow/runner.py",
            "docs/guide.md",
        ],
        "forbidden_write_paths": ["app/services/workflow/private/**"],
    }


@pytest.mark.parametrize(
    ("paths", "allowed", "forbidden"),
    [
        ([], ["app/**"], []),
        (["docs/guide.md"], ["app/**"], []),
        (["app/private.py"], ["app/**"], ["app/**"]),
        (["app/*.py"], ["app/**"], []),
        (["app/file?.py"], ["app/**"], []),
        (["app/[ab].py"], ["app/**"], []),
    ],
)
def test_new_mutation_envelope_fails_closed(
    paths: list[str], allowed: list[str], forbidden: list[str]
) -> None:
    envelope = authorization_manifest.build_authorization_mutation_envelope(
        paths, allowed, forbidden
    )

    assert envelope["allowed_write_paths"] == []
    assert envelope["forbidden_write_paths"] == forbidden


def test_legacy_broad_context_round_trip_and_digest_remain_unchanged() -> None:
    normalized = authorization_manifest.normalize_authorization_context(_context())

    assert normalized["mutation_envelope"]["allowed_write_paths"] == [
        "app/services/workflow/**"
    ]
    assert digest_value(normalized) == (
        "b04487243d9c8e5c5b427fdeddd046a2bd70859fef09ab8be25bd48d5b42885c"
    )


def test_manage_authorization_fallback_builds_exact_envelope() -> None:
    context = manage_authorization._context(
        {
            "decision_id": "route-1",
            "route_fingerprint": "a" * 64,
            "changed_paths": ["tests\\unit\\test_service.py"],
            "action": "review",
            "authorization_request": {"pre_change_snapshot": "b" * 64},
            "execution_gate": {
                "proposed_allowed_write_paths": ["tests/**"],
                "proposed_forbidden_write_paths": ["tests/private/**"],
            },
        }
    )

    assert context["mutation_envelope"] == {
        "allowed_write_paths": ["tests/unit/test_service.py"],
        "forbidden_write_paths": ["tests/private/**"],
    }


def test_manage_authorization_preserves_nested_persisted_context() -> None:
    persisted = _context()

    assert manage_authorization._context(
        {"authorization_request": {"context": persisted}}
    ) == persisted


def test_user_grant_is_single_use_and_cannot_revive(tmp_path) -> None:
    store = AuthorizationManifestStore(tmp_path)
    request = store.create_request(_context())
    grant = store.grant(
        request["request_id"],
        authorization_source="user",
        confirmation="I authorize this exact mutation envelope.",
    )

    assert grant["state"] == "granted"
    consumed = store.consume(grant["grant_id"], _context())
    assert consumed["state"] == "consumed"
    assert store.active_grant(request["request_id"], _context()) is None

    with pytest.raises(ValueError, match="cannot be granted again"):
        store.grant(
            request["request_id"],
            authorization_source="user",
            confirmation="I repeat the same authorization.",
        )


def test_relevant_input_change_invalidates_grant(tmp_path) -> None:
    store = AuthorizationManifestStore(tmp_path)
    request = store.create_request(_context())
    grant = store.grant(
        request["request_id"],
        authorization_source="user",
        confirmation="I authorize this exact mutation envelope.",
    )

    assert store.active_grant(
        request["request_id"],
        _context(route_fingerprint="c" * 64),
    ) is None
    persisted = store.get_grant(grant["grant_id"])
    assert persisted["state"] == "invalidated"


def test_bounded_multi_use_requires_explicit_limit(tmp_path) -> None:
    store = AuthorizationManifestStore(tmp_path)
    request = store.create_request(_context())
    grant = store.grant(
        request["request_id"],
        authorization_source="user",
        confirmation="I authorize exactly two uses.",
        max_uses=2,
    )

    first = store.consume(grant["grant_id"], _context())
    second = store.consume(grant["grant_id"], _context())

    assert first["state"] == "granted"
    assert first["uses_remaining"] == 1
    assert second["state"] == "consumed"
    assert second["uses_remaining"] == 0


def test_expired_grant_transitions_before_use(tmp_path, monkeypatch) -> None:
    store = AuthorizationManifestStore(tmp_path)
    request = store.create_request(_context())
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    grant = store.grant(
        request["request_id"],
        authorization_source="user",
        confirmation="I authorize this envelope for one hour.",
        expires_at=expires.isoformat(),
    )

    real_datetime = authorization_manifest.dt.datetime

    class FutureDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            value = expires + dt.timedelta(hours=1)
            return value if tz else value.replace(tzinfo=None)

    monkeypatch.setattr(authorization_manifest.dt, "datetime", FutureDateTime)

    with pytest.raises(ValueError, match="not active"):
        store.consume(grant["grant_id"], _context())
    assert store.get_grant(grant["grant_id"])["state"] == "expired"


def test_grant_audit_chain_detects_tampering(tmp_path) -> None:
    store = AuthorizationManifestStore(tmp_path)
    request = store.create_request(_context())
    grant = store.grant(
        request["request_id"],
        authorization_source="user",
        confirmation="I authorize this exact mutation envelope.",
    )

    manifest_path = tmp_path / "authorizations" / f"{grant['grant_id']}.json"
    raw = manifest_path.read_text(encoding="utf-8").replace(
        '"state": "granted"', '"state": "consumed"'
    )
    manifest_path.write_text(raw, encoding="utf-8")

    with pytest.raises(ValueError, match="audit chain"):
        store.get_grant(grant["grant_id"])
