import io
import tarfile
from pathlib import Path

import pytest

from cliany_site.tui.screens.adapter_list import _safe_tar_members


def _add_file(tar: tarfile.TarFile, name: str, content: bytes = b"") -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(content)
    tar.addfile(info, io.BytesIO(content))


def _add_symlink(tar: tarfile.TarFile, name: str, linkname: str) -> None:
    info = tarfile.TarInfo(name=name)
    info.type = tarfile.SYMTYPE
    info.linkname = linkname
    tar.addfile(info)


def _add_hardlink(tar: tarfile.TarFile, name: str, linkname: str) -> None:
    info = tarfile.TarInfo(name=name)
    info.type = tarfile.LNKTYPE
    info.linkname = linkname
    tar.addfile(info)


def test_extract_rejects_path_traversal(tmp_path: Path) -> None:
    tar_path = tmp_path / "evil.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_file(tar, "../../etc/passwd", b"root:x:0:0:root:/root:/bin/bash")

    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path, "r:gz") as tar:
        with pytest.raises(ValueError):
            list(_safe_tar_members(tar, dest))


def test_extract_rejects_absolute_path(tmp_path: Path) -> None:
    tar_path = tmp_path / "abs.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_file(tar, "/etc/passwd", b"")

    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path, "r:gz") as tar:
        with pytest.raises(ValueError):
            list(_safe_tar_members(tar, dest))


def test_extract_rejects_symlink_escape(tmp_path: Path) -> None:
    tar_path = tmp_path / "symlink_evil.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_symlink(tar, "domain/evil_link", "/etc/passwd")

    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path, "r:gz") as tar:
        with pytest.raises(ValueError):
            list(_safe_tar_members(tar, dest))


def test_extract_rejects_symlink_relative_escape(tmp_path: Path) -> None:
    tar_path = tmp_path / "symlink_rel.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_symlink(tar, "domain/evil_link", "../../../../etc/shadow")

    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path, "r:gz") as tar:
        with pytest.raises(ValueError):
            list(_safe_tar_members(tar, dest))


def test_extract_rejects_hardlink_escape(tmp_path: Path) -> None:
    tar_path = tmp_path / "hardlink_evil.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_hardlink(tar, "domain/evil_hard", "/etc/passwd")

    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path, "r:gz") as tar:
        with pytest.raises(ValueError):
            list(_safe_tar_members(tar, dest))


def test_extract_normal_file_ok(tmp_path: Path) -> None:
    tar_path = tmp_path / "normal.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_file(tar, "github.com/commands.py", b"# adapter\n")
        _add_file(tar, "github.com/metadata.json", b"{}")

    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path, "r:gz") as tar:
        members = list(_safe_tar_members(tar, dest))

    assert len(members) == 2
    names = {m.name for m in members}
    assert "github.com/commands.py" in names
    assert "github.com/metadata.json" in names


def test_extract_normal_file_extracts_correctly(tmp_path: Path) -> None:
    tar_path = tmp_path / "normal.tar.gz"
    content = b"print('hello')\n"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_file(tar, "domain/commands.py", content)

    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=dest, members=_safe_tar_members(tar, dest))

    extracted = dest / "domain" / "commands.py"
    assert extracted.exists()
    assert extracted.read_bytes() == content
