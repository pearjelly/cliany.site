import json

import pytest

from cliany_site.browser.session_scope import (
    ScopesRegistry,
    SessionScope,
    acquire_scope,
    release_scope,
)


def test_ephemeral_scope_is_not_persisted(tmp_path):
    scopes_json = tmp_path / "scopes.json"
    scope = acquire_scope(name=None, scopes_path=scopes_json)

    assert scope.name is None
    assert scope.tab_target_id.startswith("ephemeral-")
    assert scope._is_ephemeral is True
    assert not scopes_json.exists()


def test_named_scope_is_persisted(tmp_path):
    scopes_json = tmp_path / "scopes.json"
    scope = acquire_scope(name="demo", scopes_path=scopes_json)

    assert scope.name == "demo"
    assert scope._is_ephemeral is False
    assert scopes_json.exists()

    data = json.loads(scopes_json.read_text())
    assert "demo" in data
    assert data["demo"]["tab_target_id"] == scope.tab_target_id


def test_named_scope_reuse(tmp_path):
    scopes_json = tmp_path / "scopes.json"
    scope1 = acquire_scope(name="demo", scopes_path=scopes_json)
    scope2 = acquire_scope(name="demo", scopes_path=scopes_json)

    assert scope1.tab_target_id == scope2.tab_target_id


def test_ephemeral_scope_release_is_safe(tmp_path):
    scopes_json = tmp_path / "scopes.json"
    scope = acquire_scope(name=None, scopes_path=scopes_json)
    release_scope(scope)

    assert not scopes_json.exists()


def test_named_scope_release_default_removes_entry(tmp_path):
    scopes_json = tmp_path / "scopes.json"
    scope = acquire_scope(name="demo", scopes_path=scopes_json)
    assert scopes_json.exists()

    release_scope(scope, keep=False)

    assert not scopes_json.exists()


def test_named_scope_release_keep_preserves_entry(tmp_path):
    scopes_json = tmp_path / "scopes.json"
    scope = acquire_scope(name="demo", scopes_path=scopes_json)
    tab_id_before = scope.tab_target_id

    release_scope(scope, keep=True)

    assert scopes_json.exists()
    data = json.loads(scopes_json.read_text())
    assert data["demo"]["tab_target_id"] == tab_id_before


def test_scopes_registry_load_returns_empty_on_missing_file(tmp_path):
    registry = ScopesRegistry(tmp_path / "nonexistent.json")
    assert registry.load() == {}


def test_scopes_registry_load_returns_empty_on_corrupt_file(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("not valid json", encoding="utf-8")
    registry = ScopesRegistry(path)
    assert registry.load() == {}


def test_multiple_named_scopes_independent(tmp_path):
    scopes_json = tmp_path / "scopes.json"
    scope_a = acquire_scope(name="alpha", scopes_path=scopes_json)
    scope_b = acquire_scope(name="beta", scopes_path=scopes_json)

    assert scope_a.tab_target_id != scope_b.tab_target_id

    data = json.loads(scopes_json.read_text())
    assert "alpha" in data
    assert "beta" in data

    release_scope(scope_a, keep=False)

    data_after = json.loads(scopes_json.read_text())
    assert "alpha" not in data_after
    assert "beta" in data_after
