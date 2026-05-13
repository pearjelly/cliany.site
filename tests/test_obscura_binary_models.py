from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from cliany_site.binary.models import (
    BinaryConfig,
    BinaryState,
    BinaryVersion,
    get_active_version,
    install_version,
    rollback_version,
    use_version,
    validate_pinned_version,
)


def _empty_state(tmp_path: Path) -> BinaryState:
    cache = tmp_path / "obscura"
    return BinaryState(
        cache_dir=cache,
        active_version=None,
        installed_versions=[],
    )


class TestInstallVersion:
    def test_install_creates_exe_and_ready(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        exe_name = "obscura.exe" if sys.platform == "win32" else "obscura"
        assert (state.cache_dir / "0.1.2" / exe_name).exists()
        assert (state.cache_dir / "0.1.2" / ".ready").exists()

    def test_install_adds_to_installed_versions(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        assert len(state.installed_versions) == 1
        assert state.installed_versions[0].version == "0.1.2"

    def test_install_is_idempotent(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        state = install_version(state, "0.1.2", "darwin-arm64")
        assert len(state.installed_versions) == 1

    def test_install_multiple_versions(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        state = install_version(state, "0.1.3", "darwin-arm64")
        versions = {v.version for v in state.installed_versions}
        assert versions == {"0.1.2", "0.1.3"}

    def test_install_does_not_change_active_version(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        assert state.active_version is None

    def test_installed_version_is_ready(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        assert state.installed_versions[0].is_ready is True

    def test_installed_version_has_installed_at(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        assert state.installed_versions[0].installed_at is not None


class TestUseVersion:
    def test_use_version_sets_active(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        state = use_version(state, "0.1.2")
        assert state.active_version == "0.1.2"

    def test_use_version_writes_active_file(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        state = use_version(state, "0.1.2")
        active_file = state.cache_dir / "active"
        assert active_file.exists()
        assert active_file.read_text(encoding="utf-8").strip() == "0.1.2"

    def test_use_uninstalled_version_raises(self, tmp_path):
        state = _empty_state(tmp_path)
        with pytest.raises(ValueError, match="未安装"):
            use_version(state, "9.9.9")


class TestGetActiveVersion:
    def test_returns_none_when_active_file_missing(self, tmp_path):
        cache = tmp_path / "obscura"
        assert get_active_version(cache) is None

    def test_returns_version_from_active_file(self, tmp_path):
        cache = tmp_path / "obscura"
        cache.mkdir(parents=True)
        (cache / "active").write_text("0.1.2", encoding="utf-8")
        assert get_active_version(cache) == "0.1.2"

    def test_returns_none_on_empty_active_file(self, tmp_path):
        cache = tmp_path / "obscura"
        cache.mkdir(parents=True)
        (cache / "active").write_text("", encoding="utf-8")
        assert get_active_version(cache) is None


class TestRollbackVersion:
    def test_rollback_switches_to_previous(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        time.sleep(0.01)
        state = install_version(state, "0.1.3", "darwin-arm64")
        state = use_version(state, "0.1.3")
        assert state.active_version == "0.1.3"
        state = rollback_version(state)
        assert state.active_version == "0.1.2"

    def test_rollback_updates_active_file(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        time.sleep(0.01)
        state = install_version(state, "0.1.3", "darwin-arm64")
        state = use_version(state, "0.1.3")
        state = rollback_version(state)
        assert (state.cache_dir / "active").read_text(encoding="utf-8").strip() == "0.1.2"

    def test_rollback_requires_two_versions(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        state = use_version(state, "0.1.2")
        with pytest.raises(ValueError):
            rollback_version(state)

    def test_rollback_on_oldest_version_raises(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        time.sleep(0.01)
        state = install_version(state, "0.1.3", "darwin-arm64")
        state = use_version(state, "0.1.2")
        with pytest.raises(ValueError):
            rollback_version(state)


class TestUseAndRollbackIntegration:
    def test_install_use_rollback_full_cycle(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        time.sleep(0.01)
        state = install_version(state, "0.1.3", "darwin-arm64")
        state = use_version(state, "0.1.3")
        assert state.active_version == "0.1.3"
        state = rollback_version(state)
        assert state.active_version == "0.1.2"
        assert get_active_version(state.cache_dir) == "0.1.2"


class TestBinaryConfig:
    def test_defaults(self):
        cfg = BinaryConfig()
        assert cfg.pinned_version is None
        assert cfg.auto_upgrade is False
        assert cfg.min_version == "0.1.2"

    def test_validate_allows_pinned_without_auto_upgrade(self):
        cfg = BinaryConfig(pinned_version="0.1.2", auto_upgrade=False)
        validate_pinned_version(cfg)

    def test_validate_allows_auto_upgrade_without_pinned(self):
        cfg = BinaryConfig(auto_upgrade=True, pinned_version=None)
        validate_pinned_version(cfg)

    def test_validate_rejects_auto_upgrade_with_pinned(self):
        cfg = BinaryConfig(pinned_version="0.1.2", auto_upgrade=True)
        with pytest.raises(ValueError, match="pinned_version"):
            validate_pinned_version(cfg)

    def test_validate_rejects_empty_string_pinned(self):
        cfg = BinaryConfig(pinned_version="")
        with pytest.raises(ValueError, match="空字符串"):
            validate_pinned_version(cfg)


class TestBinaryVersionDataclass:
    def test_fields(self, tmp_path):
        from datetime import datetime
        bv = BinaryVersion(
            version="0.1.2",
            platform="darwin-arm64",
            path=tmp_path / "obscura",
            is_ready=True,
            installed_at=datetime(2026, 1, 1),
        )
        assert bv.version == "0.1.2"
        assert bv.platform == "darwin-arm64"
        assert bv.is_ready is True
        assert bv.installed_at.year == 2026

    def test_installed_at_defaults_to_none(self, tmp_path):
        bv = BinaryVersion(
            version="0.1.2",
            platform="linux-amd64",
            path=tmp_path / "obscura",
            is_ready=False,
        )
        assert bv.installed_at is None


class TestCacheDirLayout:
    def test_version_directory_structure(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        assert (state.cache_dir / "0.1.2").is_dir()
        assert (state.cache_dir / "0.1.2" / ".ready").is_file()

    def test_multiple_versions_each_in_own_dir(self, tmp_path):
        state = _empty_state(tmp_path)
        state = install_version(state, "0.1.2", "darwin-arm64")
        state = install_version(state, "0.1.3", "darwin-arm64")
        assert (state.cache_dir / "0.1.2").is_dir()
        assert (state.cache_dir / "0.1.3").is_dir()
