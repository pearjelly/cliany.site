"""适配器市场 — marketplace.py + commands/market.py 测试"""

from __future__ import annotations

import gzip
import hashlib
import json
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError
from urllib.request import Request

import pytest
from click.testing import CliRunner, Result

from cliany_site.marketplace import (
    MANIFEST_VERSION,
    MAX_REMOTE_PACKAGE_SIZE,
    PACK_EXTENSION,
    AdapterManifest,
    _HTTPSOnlyRedirectHandler,
    _sha256_file,
    get_adapter_info,
    inspect_adapter_package,
    install_adapter,
    list_backups,
    pack_adapter,
    resolve_adapter_source,
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
    manifest_domain: str | None = None,
    bad_hash: bool = False,
    missing_declared_file: bool = False,
    extra_file: bool = False,
    path_traversal: bool = False,
    no_manifest: bool = False,
    manifest_data: object | None = None,
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

    manifest = manifest_data
    if manifest is None:
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "domain": domain if manifest_domain is None else manifest_domain,
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

        if not missing_declared_file:
            info_meta = tarfile.TarInfo(name="metadata.json")
            info_meta.size = len(metadata_content)
            tar.addfile(info_meta, BytesIO(metadata_content))

        if extra_file:
            extra_info = tarfile.TarInfo(name="unlisted.txt")
            extra_content = b"not declared in manifest"
            extra_info.size = len(extra_content)
            tar.addfile(extra_info, BytesIO(extra_content))

        if path_traversal:
            evil_info = tarfile.TarInfo(name="../../../etc/passwd")
            evil_content = b"root:x:0:0:"
            evil_info.size = len(evil_content)
            tar.addfile(evil_info, BytesIO(evil_content))

    return pack_path


class _FakeResponse:
    def __init__(self, body: bytes, *, content_length: int | None = None) -> None:
        self._body = body
        self.headers = {} if content_length is None else {"Content-Length": str(content_length)}
        self.read_calls = 0

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if size < 0:
            size = len(self._body)
        body, self._body = self._body[:size], self._body[size:]
        return body


class _GeneratedResponse(_FakeResponse):
    def __init__(self, size: int) -> None:
        super().__init__(b"")
        self.remaining = size

    def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if self.remaining <= 0:
            return b""
        chunk_size = min(size, self.remaining)
        self.remaining -= chunk_size
        return b"x" * chunk_size


def _patch_download_temp_dir(tmp_path: Path):
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    real_mkstemp = tempfile.mkstemp

    def mkstemp(*args: object, **kwargs: object) -> tuple[int, str]:
        kwargs["dir"] = str(download_dir)
        return real_mkstemp(*args, **kwargs)

    return patch("cliany_site.marketplace.tempfile.mkstemp", side_effect=mkstemp), download_dir


# ── remote adapter source ────────────────────────────────


class TestRemoteAdapterSource:
    @pytest.mark.parametrize(
        "source",
        [
            "http://downloads.example.test/adapter.tar.gz",
            "file:///tmp/adapter.tar.gz",
            "data:application/gzip;base64,ZmFrZQ==",
        ],
    )
    def test_rejects_non_https_before_request(self, source: str) -> None:
        with (
            patch("cliany_site.marketplace.urllib.request.build_opener") as build_opener,
            pytest.raises(ValueError, match="HTTPS"),
            resolve_adapter_source(source, expected_sha256="0" * 64),
        ):
            pass

        build_opener.assert_not_called()

    @pytest.mark.parametrize("expected_sha256", [None, "abc", "g" * 64])
    def test_requires_a_64_hex_digest_before_request(self, expected_sha256: str | None) -> None:
        with (
            patch("cliany_site.marketplace.urllib.request.build_opener") as build_opener,
            pytest.raises(ValueError, match="SHA-256"),
            resolve_adapter_source(
                "https://downloads.example.test/adapter.tar.gz?token=secret#fragment",
                expected_sha256=expected_sha256,
            ),
        ):
            pass

        build_opener.assert_not_called()

    def test_https_redirect_handler_rejects_downgrade_before_body_read(self) -> None:
        handler = _HTTPSOnlyRedirectHandler()
        response = MagicMock()

        with pytest.raises(ValueError, match="降级"):
            handler.redirect_request(
                Request("https://downloads.example.test/adapter.tar.gz"),
                response,
                302,
                "Found",
                {},
                "http://cdn.example.test/adapter.tar.gz?token=secret#fragment",
            )

        response.read.assert_not_called()

    def test_local_path_yields_original_path_without_digest(self, tmp_path: Path) -> None:
        pack_path = tmp_path / "local.cliany-adapter.tar.gz"
        pack_path.write_bytes(b"local")

        with resolve_adapter_source(str(pack_path)) as resolved_path:
            assert resolved_path == pack_path

    def test_windows_drive_path_is_local_source(self) -> None:
        source = r"C:\\packages\\adapter.cliany-adapter.tar.gz"

        with resolve_adapter_source(source) as resolved_path:
            assert str(resolved_path) == source

    def test_downstream_error_redacts_temp_path_and_url_secrets(self, tmp_path: Path) -> None:
        archive = b"remote archive"
        digest = hashlib.sha256(archive).hexdigest()
        response = _FakeResponse(archive, content_length=len(archive))
        opener = MagicMock()
        opener.open.return_value = response
        source = "https://downloads.example.test/adapter.tar.gz?token=secret#fragment"
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with (
            patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener),
            temp_patch,
            pytest.raises(ValueError) as exc_info,
            resolve_adapter_source(source, expected_sha256=digest) as resolved_path,
        ):
            raise ValueError(f"安装包无法读取: {resolved_path}")

        assert str(exc_info.value) == "安装包无法读取: https://downloads.example.test/adapter.tar.gz"
        assert str(download_dir) not in str(exc_info.value)
        assert "secret" not in str(exc_info.value)
        assert "fragment" not in str(exc_info.value)
        assert list(download_dir.iterdir()) == []


class TestRemoteAdapterCLI:
    def _invoke(self, args: list[str], cfg: MagicMock) -> Result:
        from cliany_site.commands.market import market_group

        runner = CliRunner()
        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            return runner.invoke(market_group, args)

    def test_correct_digest_reaches_existing_dry_run_plan_and_cleans_temp_file(
        self, tmp_path: Path
    ) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "remote-dry-run.com", version="2.0.0")
        archive = pack_path.read_bytes()
        digest = hashlib.sha256(archive).hexdigest()
        response = _FakeResponse(archive, content_length=len(archive))
        opener = MagicMock()
        opener.open.return_value = response
        source = "https://downloads.example.test/adapter.tar.gz?token=secret#fragment"
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener), temp_patch:
            result = self._invoke(
                ["install", source, "--sha256", digest.upper(), "--dry-run", "--json"],
                cfg,
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"] == {
            "dry_run": True,
            "package_sha256": digest,
            "domain": "remote-dry-run.com",
            "version": "2.0.0",
            "files": ["commands.py", "metadata.json"],
            "would_replace": False,
            "would_create_backup": False,
        }
        assert response.read_calls > 0
        assert not (cfg.adapters_dir / "remote-dry-run.com").exists()
        assert not (cfg.home_dir / "backups").exists()
        assert list(download_dir.iterdir()) == []
        opener.open.assert_called_once()

    def test_remote_install_uses_existing_local_install_path(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "remote-install.com")
        archive = pack_path.read_bytes()
        digest = hashlib.sha256(archive).hexdigest()
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(archive, content_length=len(archive))
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener), temp_patch:
            result = self._invoke(
                ["install", "https://downloads.example.test/adapter.tar.gz", "--sha256", digest, "--json"],
                cfg,
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["domain"] == "remote-install.com"
        assert (cfg.adapters_dir / "remote-install.com" / "commands.py").exists()
        assert list(download_dir.iterdir()) == []

    def test_remote_digest_mismatch_is_install_failed_without_secrets_or_temp_path(
        self, tmp_path: Path
    ) -> None:
        cfg = _make_config(tmp_path)
        archive = b"remote archive"
        actual_digest = hashlib.sha256(archive).hexdigest()
        expected_digest = "a" * 64
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(archive, content_length=len(archive))
        source = "https://downloads.example.test/adapter.tar.gz?token=secret#fragment"
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener), temp_patch:
            result = self._invoke(
                ["install", source, "--sha256", expected_digest, "--dry-run", "--json"],
                cfg,
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert expected_digest in data["error"]["message"]
        assert actual_digest in data["error"]["message"]
        assert "secret" not in result.output
        assert "fragment" not in result.output
        assert str(download_dir) not in result.output
        assert not (cfg.home_dir / "backups").exists()
        assert list(download_dir.iterdir()) == []

    def test_remote_network_failure_is_install_failed_without_url_query(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        opener = MagicMock()
        opener.open.side_effect = URLError("failed https://bad.example.test/?token=secret")
        source = "https://downloads.example.test/adapter.tar.gz?token=secret#fragment"

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener):
            result = self._invoke(
                ["install", source, "--sha256", "0" * 64, "--dry-run", "--json"],
                cfg,
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert "远程安装包下载失败" in data["error"]["message"]
        assert "secret" not in result.output
        assert "fragment" not in result.output

    def test_declared_oversize_response_is_rejected_before_reading(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        response = _FakeResponse(b"should not be read", content_length=MAX_REMOTE_PACKAGE_SIZE + 1)
        opener = MagicMock()
        opener.open.return_value = response
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener), temp_patch:
            result = self._invoke(
                [
                    "install",
                    "https://downloads.example.test/adapter.tar.gz",
                    "--sha256",
                    "0" * 64,
                    "--dry-run",
                    "--json",
                ],
                cfg,
            )

        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INSTALL_FAILED"
        assert "64 MiB" in json.loads(result.output)["error"]["message"]
        assert response.read_calls == 0
        assert list(download_dir.iterdir()) == []

    def test_streamed_oversize_response_is_rejected_and_cleaned(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        response = _GeneratedResponse(MAX_REMOTE_PACKAGE_SIZE + 1)
        opener = MagicMock()
        opener.open.return_value = response
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener), temp_patch:
            result = self._invoke(
                [
                    "install",
                    "https://downloads.example.test/adapter.tar.gz",
                    "--sha256",
                    "0" * 64,
                    "--dry-run",
                    "--json",
                ],
                cfg,
            )

        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INSTALL_FAILED"
        assert response.read_calls > 0
        assert list(download_dir.iterdir()) == []

    @pytest.mark.parametrize(
        "pack_path_factory",
        [
            lambda tmp_path: tmp_path / "corrupt.tar.gz",
            lambda tmp_path: _make_tarball(
                tmp_path / "packs", "remote-malformed.com", manifest_data=["not", "an", "object"]
            ),
        ],
    )
    def test_remote_archive_validation_errors_are_install_failed_without_temp_path(
        self, tmp_path: Path, pack_path_factory
    ) -> None:
        cfg = _make_config(tmp_path)
        pack_path = pack_path_factory(tmp_path)
        if not pack_path.exists():
            pack_path.write_bytes(b"not a gzip archive")
        archive = pack_path.read_bytes()
        digest = hashlib.sha256(archive).hexdigest()
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(archive, content_length=len(archive))
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener), temp_patch:
            result = self._invoke(
                [
                    "install",
                    "https://downloads.example.test/adapter.tar.gz?token=secret",
                    "--sha256",
                    digest,
                    "--dry-run",
                    "--json",
                ],
                cfg,
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert str(download_dir) not in result.output
        assert "secret" not in result.output
        assert list(download_dir.iterdir()) == []

    def test_root_remote_dry_run_does_not_create_runtime_home(self, tmp_path: Path, tmp_home: Path) -> None:
        from cliany_site.cli import cli

        pack_path = _make_tarball(tmp_path / "packs", "root-remote-dry-run.com")
        archive = pack_path.read_bytes()
        digest = hashlib.sha256(archive).hexdigest()
        opener = MagicMock()
        opener.open.return_value = _FakeResponse(archive, content_length=len(archive))
        runtime_home = tmp_home / ".cliany-site"
        temp_patch, download_dir = _patch_download_temp_dir(tmp_path)

        with patch("cliany_site.marketplace.urllib.request.build_opener", return_value=opener), temp_patch:
            result = CliRunner().invoke(
                cli,
                [
                    "--json",
                    "market",
                    "install",
                    "https://downloads.example.test/adapter.tar.gz",
                    "--sha256",
                    digest,
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert json.loads(result.output)["data"]["package_sha256"] == digest
        assert not runtime_home.exists()
        assert list(download_dir.iterdir()) == []


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

    def test_to_dict_contains_created_at_once(self) -> None:
        manifest = AdapterManifest(created_at="2026-07-16T00:00:00+00:00")

        serialized = manifest.to_dict()

        assert list(serialized).count("created_at") == 1
        assert serialized["created_at"] == "2026-07-16T00:00:00+00:00"

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
    @pytest.mark.parametrize(
        "manifest_domain",
        ["/absolute", ".", "..", "nested/domain", r"nested\domain", "C:escape"],
    )
    def test_install_rejects_path_like_manifest_domain(self, tmp_path: Path, manifest_domain: str) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(
            tmp_path / "packs",
            "domain-validation.com",
            manifest_domain=manifest_domain,
        )

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(ValueError, match="domain.*不安全路径"),
        ):
            install_adapter(pack_path)

        assert list(cfg.adapters_dir.iterdir()) == []
        assert not (cfg.home_dir / "backups").exists()

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

    def test_install_missing_declared_file_raises(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "missing-file.com", missing_declared_file=True)

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(ValueError, match="缺少声明文件: metadata.json"),
        ):
            install_adapter(pack_path)

    def test_install_unlisted_file_raises(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "extra.com", extra_file=True)

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            pytest.raises(ValueError, match="未声明文件: unlisted.txt"),
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

    def test_install_force_bad_package_does_not_create_backup(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "safe-bak.com")
        pack_path = _make_tarball(tmp_path / "packs", "safe-bak.com", bad_hash=True)

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            with pytest.raises(ValueError, match="文件校验失败"):
                install_adapter(pack_path, force=True)
            backups = list_backups("safe-bak.com")

        assert backups == []

    def test_install_nonexistent_pack_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="安装包不存在"):
            install_adapter(tmp_path / "ghost.tar.gz")

    def test_install_corrupt_pack_raises_normalized_value_error(self, tmp_path: Path) -> None:
        pack_path = tmp_path / "corrupt.tar.gz"
        pack_path.write_bytes(b"not a gzip archive")

        with pytest.raises(ValueError) as exc_info:
            install_adapter(pack_path)

        assert str(exc_info.value) == f"安装包无法读取: {pack_path}"

    def test_install_body_eof_error_is_not_mislabeled_as_archive_error(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "body-eof.com")

        with (
            patch("cliany_site.marketplace.get_config", return_value=cfg),
            patch("cliany_site.marketplace.shutil.copy2", side_effect=EOFError("install body failed")),
            pytest.raises(EOFError, match="install body failed"),
        ):
            install_adapter(pack_path)

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


class TestInspectAdapterPackage:
    def test_inspect_valid_new_package_has_no_runtime_side_effects(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "inspect-new.com", version="2.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            report = inspect_adapter_package(pack_path)

        assert report == {
            "dry_run": True,
            "package_sha256": _sha256_file(pack_path),
            "domain": "inspect-new.com",
            "version": "2.0.0",
            "files": ["commands.py", "metadata.json"],
            "would_replace": False,
            "would_create_backup": False,
        }
        assert not (cfg.adapters_dir / "inspect-new.com").exists()
        assert not (cfg.home_dir / "backups").exists()

    def test_inspect_force_reports_replace_without_writing_backup(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "inspect-force.com", version="1.0.0")
        commands_before = (adapter_dir / "commands.py").read_bytes()
        pack_path = _make_tarball(tmp_path / "packs", "inspect-force.com", version="2.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            report = inspect_adapter_package(pack_path, force=True)
            backups_after = list_backups("inspect-force.com")

        assert report["would_replace"] is True
        assert report["would_create_backup"] is True
        assert (adapter_dir / "commands.py").read_bytes() == commands_before
        assert backups_after == []

    def test_inspect_duplicate_without_force_raises_without_writing(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "inspect-duplicate.com")
        commands_before = (adapter_dir / "commands.py").read_bytes()
        pack_path = _make_tarball(tmp_path / "packs", "inspect-duplicate.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg), pytest.raises(
            FileExistsError, match="已安装"
        ):
            inspect_adapter_package(pack_path)

        assert (adapter_dir / "commands.py").read_bytes() == commands_before
        assert not (cfg.home_dir / "backups").exists()

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"bad_hash": True}, "文件校验失败"),
            ({"path_traversal": True}, "不安全路径"),
        ],
    )
    def test_inspect_rejects_invalid_package_without_writing(
        self,
        tmp_path: Path,
        kwargs: dict[str, bool],
        message: str,
    ) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "inspect-invalid.com", **kwargs)

        with patch("cliany_site.marketplace.get_config", return_value=cfg), pytest.raises(
            ValueError, match=message
        ):
            inspect_adapter_package(pack_path)

        assert not (cfg.adapters_dir / "inspect-invalid.com").exists()
        assert not (cfg.home_dir / "backups").exists()


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

    def test_install_bad_hash_returns_actionable_fix(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "cli-bad.com", bad_hash=True)

        result = self._invoke(["install", str(pack_path), "--json"], cfg)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert "manifest.file_hashes" in data["error"]["fix"]

    def test_install_duplicate_returns_force_hint(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "cli-dup.com")
        pack_path = _make_tarball(tmp_path / "packs", "cli-dup.com")

        result = self._invoke(["install", str(pack_path), "--json"], cfg)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert "--force" in data["error"]["fix"]

    def test_install_missing_package_uses_install_failed_envelope(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        missing_pack = tmp_path / "missing.cliany-adapter.tar.gz"

        result = self._invoke(["install", str(missing_pack), "--dry-run", "--json"], cfg)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert data["error"]["message"] == f"安装包不存在: {missing_pack}"

    @pytest.mark.parametrize(
        ("manifest_data", "message"),
        [
            (["not", "an", "object"], "manifest.json 根节点必须是对象"),
            (
                {"domain": "bad-files.com", "files": None, "file_hashes": {}},
                "manifest.json 的 files 必须是字符串列表",
            ),
            (
                {"domain": "bad-hashes.com", "files": [], "file_hashes": None},
                "manifest.json 的 file_hashes 必须是字符串映射",
            ),
        ],
    )
    def test_install_malformed_manifest_uses_install_failed_envelope(
        self,
        tmp_path: Path,
        manifest_data: object,
        message: str,
    ) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "malformed.com", manifest_data=manifest_data)

        result = self._invoke(["install", str(pack_path), "--dry-run", "--json"], cfg)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert data["error"]["message"] == message

    def test_install_dry_run_returns_package_plan(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "cli-dry-run.com", version="2.0.0")

        result = self._invoke(["install", str(pack_path), "--dry-run", "--json"], cfg)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["dry_run"] is True
        assert data["data"]["domain"] == "cli-dry-run.com"
        assert data["data"]["version"] == "2.0.0"
        assert data["data"]["would_replace"] is False
        assert data["data"]["would_create_backup"] is False
        assert not (cfg.adapters_dir / "cli-dry-run.com").exists()

    def test_install_dry_run_duplicate_uses_install_failed_envelope(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "cli-dry-duplicate.com")
        commands_before = (adapter_dir / "commands.py").read_bytes()
        pack_path = _make_tarball(tmp_path / "packs", "cli-dry-duplicate.com")

        result = self._invoke(["install", str(pack_path), "--dry-run", "--json"], cfg)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert "--force" in data["error"]["fix"]
        assert (adapter_dir / "commands.py").read_bytes() == commands_before
        assert not (cfg.home_dir / "backups").exists()

    @pytest.mark.parametrize("dry_run_first", [False, True])
    def test_root_install_dry_run_does_not_create_runtime_home(
        self,
        tmp_path: Path,
        tmp_home: Path,
        dry_run_first: bool,
    ) -> None:
        from cliany_site.cli import cli

        runtime_home = tmp_home / ".cliany-site"
        pack_path = _make_tarball(tmp_path / "packs", "root-dry-run.com")
        install_args = ["--dry-run", str(pack_path)] if dry_run_first else [str(pack_path), "--dry-run"]

        result = CliRunner().invoke(
            cli,
            ["--json", "market", "install", *install_args],
        )

        assert result.exit_code == 0
        assert json.loads(result.output)["data"]["dry_run"] is True
        assert not runtime_home.exists()

    def test_root_install_dry_run_truncated_gzip_uses_install_failed_envelope(
        self,
        tmp_path: Path,
        tmp_home: Path,
    ) -> None:
        from cliany_site.cli import cli

        runtime_home = tmp_home / ".cliany-site"
        pack_path = tmp_path / "truncated.cliany-adapter.tar.gz"
        pack_path.write_bytes(b"\x1f\x8b\x08\x00")

        result = CliRunner().invoke(
            cli,
            ["--json", "market", "install", str(pack_path), "--dry-run"],
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert data["success"] is False
        assert data["error"]["message"] == f"安装包无法读取: {pack_path}"
        assert not runtime_home.exists()

    def test_root_install_dry_run_corrupt_gzip_crc_uses_normalized_error(
        self,
        tmp_path: Path,
        tmp_home: Path,
    ) -> None:
        from cliany_site.cli import cli

        runtime_home = tmp_home / ".cliany-site"
        pack_path = _make_tarball(tmp_path / "packs", "corrupt-crc.com")
        with tarfile.open(pack_path, "r:gz") as tar:
            payload_end = max(
                member.offset_data
                + ((member.size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE) * tarfile.BLOCKSIZE
                for member in tar.getmembers()
            )
        tar_payload = gzip.decompress(pack_path.read_bytes())[:payload_end]
        pack_path.write_bytes(gzip.compress(tar_payload))
        archive_bytes = bytearray(pack_path.read_bytes())
        archive_bytes[-8] ^= 0xFF
        pack_path.write_bytes(archive_bytes)

        result = CliRunner().invoke(
            cli,
            ["--json", "market", "install", str(pack_path), "--dry-run"],
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert data["error"]["message"] == f"安装包无法读取: {pack_path}"
        assert not runtime_home.exists()
