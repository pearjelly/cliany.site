"""适配器市场 — marketplace.py + commands/market.py 测试"""

from __future__ import annotations

import json
import tarfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner, Result

from cliany_site.marketplace import (
    MANIFEST_VERSION,
    PACK_EXTENSION,
    AdapterManifest,
    _sha256_file,
    get_adapter_info,
    install_adapter,
    list_backups,
    pack_adapter,
    rollback_adapter,
    uninstall_adapter,
)

# ── helpers ──────────────────────────────────────────────


def _make_config(tmp_path: Path) -> MagicMock:
    cfg = MagicMock()
    cfg.home_dir = tmp_path
    cfg.adapters_dir = tmp_path / "adapters"
    cfg.adapters_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def _create_adapter(adapters_dir: Path, domain: str, *, version: str = "0.1.0") -> Path:
    """在 adapters_dir 下创建一个最简 adapter 目录"""
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)

    commands_py = adapter_dir / "commands.py"
    commands_py.write_text('import click\n\n@click.command()\ndef hello():\n    click.echo("hi")\n', encoding="utf-8")

    metadata = {
        "workflow": "测试工作流",
        "source_url": f"https://{domain}",
        "version": version,
    }
    (adapter_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    return adapter_dir


def _make_tarball(
    tmp_path: Path,
    domain: str,
    *,
    version: str = "0.1.0",
    bad_hash: bool = False,
    path_traversal: bool = False,
    no_manifest: bool = False,
) -> Path:
    """手工构建一个 .tar.gz 安装包"""
    import hashlib

    pack_path = tmp_path / f"{domain}{PACK_EXTENSION}"
    commands_content = b"import click\n\n@click.command()\ndef test():\n    pass\n"
    metadata_content = json.dumps({"workflow": "test", "version": version}).encode("utf-8")

    commands_hash = hashlib.sha256(commands_content).hexdigest()
    metadata_hash = hashlib.sha256(metadata_content).hexdigest()

    if bad_hash:
        commands_hash = "0" * 64

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "domain": domain,
        "version": version,
        "description": "test",
        "author": "tester",
        "created_at": "2025-01-01T00:00:00+00:00",
        "files": ["commands.py", "metadata.json"],
        "file_hashes": {"commands.py": commands_hash, "metadata.json": metadata_hash},
    }

    tmp_path.mkdir(parents=True, exist_ok=True)
    with tarfile.open(pack_path, "w:gz") as tar:
        if not no_manifest:
            manifest_bytes = json.dumps(manifest).encode("utf-8")
            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(manifest_bytes)
            tar.addfile(info, BytesIO(manifest_bytes))

        info_cmd = tarfile.TarInfo(name="commands.py")
        info_cmd.size = len(commands_content)
        tar.addfile(info_cmd, BytesIO(commands_content))

        info_meta = tarfile.TarInfo(name="metadata.json")
        info_meta.size = len(metadata_content)
        tar.addfile(info_meta, BytesIO(metadata_content))

        if path_traversal:
            evil_info = tarfile.TarInfo(name="../../../etc/passwd")
            evil_content = b"root:x:0:0:"
            evil_info.size = len(evil_content)
            tar.addfile(evil_info, BytesIO(evil_content))

    return pack_path


# ── AdapterManifest ──────────────────────────────────────


class TestAdapterManifest:
    def test_defaults(self) -> None:
        m = AdapterManifest()
        assert m.manifest_version == MANIFEST_VERSION
        assert m.domain == ""
        assert m.version == "0.1.0"
        assert m.files == []
        assert m.file_hashes == {}

    def test_to_dict_round_trip(self) -> None:
        m = AdapterManifest(
            domain="example.com",
            version="1.0.0",
            author="alice",
            files=["commands.py"],
            file_hashes={"commands.py": "abc123"},
        )
        d = m.to_dict()
        assert d["domain"] == "example.com"
        assert d["version"] == "1.0.0"
        assert d["author"] == "alice"

        m2 = AdapterManifest.from_dict(d)
        assert m2.domain == m.domain
        assert m2.version == m.version
        assert m2.author == m.author
        assert m2.files == m.files
        assert m2.file_hashes == m.file_hashes

    def test_from_dict_missing_fields(self) -> None:
        m = AdapterManifest.from_dict({})
        assert m.domain == ""
        assert m.version == "0.1.0"
        assert m.manifest_version == MANIFEST_VERSION

    def test_from_dict_coerces_types(self) -> None:
        m = AdapterManifest.from_dict({"domain": 123, "version": 456})
        assert m.domain == "123"
        assert m.version == "456"

    def test_frozen(self) -> None:
        m = AdapterManifest(domain="test.com")
        with pytest.raises(AttributeError):
            m.domain = "other.com"  # type: ignore[misc]


# ── _sha256_file ─────────────────────────────────────────


class TestSha256File:
    def test_hash_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h1 = _sha256_file(f)
        h2 = _sha256_file(f)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_different_content(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("aaa")
        f2.write_text("bbb")
        assert _sha256_file(f1) != _sha256_file(f2)


# ── pack_adapter ─────────────────────────────────────────


class TestPackAdapter:
    def test_pack_creates_tarball(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "test.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            pack_path = pack_adapter("test.com", version="1.0.0", author="bob")

        assert pack_path.exists()
        assert pack_path.suffix == ".gz"
        assert PACK_EXTENSION in pack_path.name

    def test_pack_contains_manifest(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "test.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            pack_path = pack_adapter("test.com")

        with tarfile.open(pack_path, "r:gz") as tar:
            names = tar.getnames()
            assert "manifest.json" in names
            assert "commands.py" in names
            assert "metadata.json" in names

            mf = tar.extractfile("manifest.json")
            assert mf is not None
            manifest = json.loads(mf.read())
            assert manifest["domain"] == "test.com"
            assert manifest["manifest_version"] == MANIFEST_VERSION

    def test_pack_file_hashes_correct(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "test.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            pack_path = pack_adapter("test.com")

        with tarfile.open(pack_path, "r:gz") as tar:
            mf = tar.extractfile("manifest.json")
            assert mf is not None
            manifest = json.loads(mf.read())
            assert "commands.py" in manifest["file_hashes"]
            assert len(manifest["file_hashes"]["commands.py"]) == 64

    def test_pack_missing_adapter_raises(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(FileNotFoundError, match="adapter 不存在"),
        ):
            pack_adapter("nonexistent.com")

    def test_pack_version_and_author(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "v.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            pack_path = pack_adapter("v.com", version="2.0.0", author="carol")

        with tarfile.open(pack_path, "r:gz") as tar:
            mf = tar.extractfile("manifest.json")
            assert mf is not None
            manifest = json.loads(mf.read())
            assert manifest["version"] == "2.0.0"
            assert manifest["author"] == "carol"

    def test_pack_output_dir(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "dir.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            pack_path = pack_adapter("dir.com")

        assert pack_path.parent == tmp_path / "packages"

    def test_pack_skips_hidden_and_tmp_files(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "skip.com")
        (adapter_dir / ".hidden").write_text("hidden")
        (adapter_dir / "temp.tmp").write_text("tmp")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            pack_path = pack_adapter("skip.com")

        with tarfile.open(pack_path, "r:gz") as tar:
            names = tar.getnames()
            assert ".hidden" not in names
            assert "temp.tmp" not in names


# ── install_adapter ──────────────────────────────────────


class TestInstallAdapter:
    def test_install_from_pack(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "fresh.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            manifest = install_adapter(pack_path)

        assert manifest.domain == "fresh.com"
        installed_dir = cfg.adapters_dir / "fresh.com"
        assert installed_dir.exists()
        assert (installed_dir / "commands.py").exists()
        assert (installed_dir / "manifest.json").exists()

    def test_install_writes_manifest(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "mf.com", version="3.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            install_adapter(pack_path)

        mf_path = cfg.adapters_dir / "mf.com" / "manifest.json"
        assert mf_path.exists()
        data = json.loads(mf_path.read_text(encoding="utf-8"))
        assert data["domain"] == "mf.com"
        assert data["version"] == "3.0.0"

    def test_install_hash_verification_fails(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "bad.com", bad_hash=True)

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(ValueError, match="文件校验失败"),
        ):
            install_adapter(pack_path)

    def test_install_path_traversal_blocked(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "evil.com", path_traversal=True)

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(ValueError, match="不安全路径"),
        ):
            install_adapter(pack_path)

    def test_install_missing_manifest_raises(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "no-mf.com", no_manifest=True)

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(ValueError, match="manifest.json"),
        ):
            install_adapter(pack_path)

    def test_install_duplicate_without_force_raises(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "dup.com")
        pack_path = _make_tarball(tmp_path / "packs", "dup.com")

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(FileExistsError, match="已安装"),
        ):
            install_adapter(pack_path, force=False)

    def test_install_force_overwrites(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "force.com")
        pack_path = _make_tarball(tmp_path / "packs", "force.com", version="2.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            manifest = install_adapter(pack_path, force=True)

        assert manifest.version == "2.0.0"

    def test_install_creates_backup_on_force(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "bak.com")
        pack_path = _make_tarball(tmp_path / "packs", "bak.com", version="2.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            install_adapter(pack_path, force=True)
            backups = list_backups("bak.com")

        assert len(backups) >= 1

    def test_install_nonexistent_pack_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="安装包不存在"):
            install_adapter(tmp_path / "ghost.tar.gz")

    def test_install_missing_domain_raises(self, tmp_path: Path) -> None:
        import hashlib

        pack_path = tmp_path / "nodomain.tar.gz"
        commands_content = b"import click\n"
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "domain": "",
            "version": "1.0.0",
            "files": ["commands.py"],
            "file_hashes": {"commands.py": hashlib.sha256(commands_content).hexdigest()},
        }
        with tarfile.open(pack_path, "w:gz") as tar:
            mb = json.dumps(manifest).encode("utf-8")
            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(mb)
            tar.addfile(info, BytesIO(mb))

            info2 = tarfile.TarInfo(name="commands.py")
            info2.size = len(commands_content)
            tar.addfile(info2, BytesIO(commands_content))

        cfg = _make_config(tmp_path)
        with patch("cliany_site.marketplace.get_config", return_value=cfg), pytest.raises(ValueError, match="domain"):
            install_adapter(pack_path)


# ── uninstall_adapter ────────────────────────────────────


class TestUninstallAdapter:
    def test_uninstall_removes_dir(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "rm.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            result = uninstall_adapter("rm.com")

        assert result is True
        assert not (cfg.adapters_dir / "rm.com").exists()

    def test_uninstall_missing_returns_false(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            result = uninstall_adapter("ghost.com")

        assert result is False


# ── list_backups ─────────────────────────────────────────


class TestListBackups:
    def test_no_backups(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            result = list_backups("nobackup.com")

        assert result == []

    def test_backups_listed_reverse_sorted(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        backup_base = cfg.home_dir / "backups" / "test.com"
        backup_base.mkdir(parents=True)

        (backup_base / "0.1.0-20250101T000000").mkdir()
        (backup_base / "0.2.0-20250201T000000").mkdir()

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            result = list_backups("test.com")

        assert len(result) == 2
        assert result[0]["version"] == "0.2.0"
        assert result[1]["version"] == "0.1.0"


# ── rollback_adapter ────────────────────────────────────


class TestRollbackAdapter:
    def test_rollback_restores_backup(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        # 创建 adapter 和一个备份
        _create_adapter(cfg.adapters_dir, "rb.com", version="2.0.0")
        backup_base = cfg.home_dir / "backups" / "rb.com"
        backup_dir = backup_base / "1.0.0-20250101T000000"
        backup_dir.mkdir(parents=True)
        (backup_dir / "commands.py").write_text("# v1 backup", encoding="utf-8")
        (backup_dir / "metadata.json").write_text('{"version": "1.0.0"}', encoding="utf-8")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            result = rollback_adapter("rb.com", backup_index=0)

        assert result is True
        content = (cfg.adapters_dir / "rb.com" / "commands.py").read_text()
        assert "v1 backup" in content

    def test_rollback_creates_pre_rollback_backup(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "rb2.com", version="2.0.0")

        backup_base = cfg.home_dir / "backups" / "rb2.com"
        backup_dir = backup_base / "1.0.0-20250101T000000"
        backup_dir.mkdir(parents=True)
        (backup_dir / "commands.py").write_text("# v1", encoding="utf-8")
        (backup_dir / "metadata.json").write_text('{"version": "1.0.0"}', encoding="utf-8")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            rollback_adapter("rb2.com", backup_index=0)
            # 应该有 2 个备份: 原始 + 回滚前自动备份
            backups = list_backups("rb2.com")

        assert len(backups) >= 2

    def test_rollback_no_backups_returns_false(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            result = rollback_adapter("noback.com")

        assert result is False

    def test_rollback_invalid_index_returns_false(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        backup_base = cfg.home_dir / "backups" / "idx.com"
        (backup_base / "1.0.0-20250101T000000").mkdir(parents=True)

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            result = rollback_adapter("idx.com", backup_index=99)

        assert result is False


# ── get_adapter_info ─────────────────────────────────────


class TestGetAdapterInfo:
    def test_info_returns_dict(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "info.com", version="1.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            info = get_adapter_info("info.com")

        assert info is not None
        assert info["domain"] == "info.com"
        assert info["installed"] is True
        assert "metadata" in info

    def test_info_missing_returns_none(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            info = get_adapter_info("ghost.com")

        assert info is None

    def test_info_includes_manifest_when_present(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "mf-info.com")
        manifest = {"manifest_version": "1", "domain": "mf-info.com", "version": "2.0.0"}
        (adapter_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            info = get_adapter_info("mf-info.com")

        assert info is not None
        assert "manifest" in info
        assert info["version"] == "2.0.0"

    def test_info_includes_backups(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "bk-info.com")
        backup_dir = cfg.home_dir / "backups" / "bk-info.com" / "1.0.0-20250101T000000"
        backup_dir.mkdir(parents=True)

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            info = get_adapter_info("bk-info.com")

        assert info is not None
        assert len(info["backups"]) == 1


# ── pack → install 端到端 ────────────────────────────────


class TestPackInstallEndToEnd:
    def test_pack_then_install(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "e2e.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            pack_path = pack_adapter("e2e.com", version="1.0.0", author="e2e")

            # 先删除原始 adapter
            uninstall_adapter("e2e.com")
            assert not (cfg.adapters_dir / "e2e.com").exists()

            # 从包安装
            manifest = install_adapter(pack_path)

        assert manifest.domain == "e2e.com"
        assert manifest.version == "1.0.0"
        assert (cfg.adapters_dir / "e2e.com" / "commands.py").exists()

    def test_pack_install_upgrade(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "upg.com", version="1.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            # 打包 v1
            pack_v1 = pack_adapter("upg.com", version="1.0.0")

            # 修改 adapter（模拟升级）
            (cfg.adapters_dir / "upg.com" / "commands.py").write_text("# v2\n", encoding="utf-8")
            pack_v2 = pack_adapter("upg.com", version="2.0.0")

            # 卸载
            uninstall_adapter("upg.com")

            # 安装 v1
            m1 = install_adapter(pack_v1)
            assert m1.version == "1.0.0"

            # 升级到 v2
            m2 = install_adapter(pack_v2, force=True)
            assert m2.version == "2.0.0"

            # 应该有 v1 备份
            backups = list_backups("upg.com")
            assert len(backups) >= 1


# ── CLI 命令集成 ─────────────────────────────────────────


class TestMarketCLI:
    def _invoke(self, args: list[str], cfg: MagicMock) -> Result:
        from cliany_site.commands.market import market_group

        runner = CliRunner()
        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            return runner.invoke(market_group, args)

    def test_publish_success(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "cli-pub.com")

        result = self._invoke(["publish", "cli-pub.com", "--json"], cfg)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["domain"] == "cli-pub.com"

    def test_publish_missing_adapter(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        result = self._invoke(["publish", "nope.com", "--json"], cfg)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False

    def test_uninstall_success(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "cli-rm.com")

        result = self._invoke(["uninstall", "cli-rm.com", "--json"], cfg)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

    def test_uninstall_missing(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        result = self._invoke(["uninstall", "ghost.com", "--json"], cfg)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False

    def test_info_success(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "cli-info.com")

        result = self._invoke(["info", "cli-info.com", "--json"], cfg)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["domain"] == "cli-info.com"

    def test_backups_empty(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        result = self._invoke(["backups", "noback.com", "--json"], cfg)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["backups"] == []
