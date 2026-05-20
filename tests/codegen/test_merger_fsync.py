from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cliany_site.codegen.merger import AdapterMerger


@pytest.fixture
def merger(tmp_path: Path) -> AdapterMerger:
    with patch("cliany_site.codegen.merger.get_config") as mock_cfg:
        mock_cfg.return_value.adapters_dir = tmp_path
        m = AdapterMerger("test.com")
    return m


def test_atomic_write_text_calls_fsync(merger: AdapterMerger, tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    with patch("os.fsync") as mock_fsync:
        merger._atomic_write_text(out, "hello")
    assert mock_fsync.call_count >= 1


def test_atomic_write_json_cleans_tmp_on_replace_error(
    merger: AdapterMerger, tmp_path: Path
) -> None:
    out = tmp_path / "out.json"
    with (
        patch("os.replace", side_effect=OSError("disk full")),
        patch("os.unlink") as mock_unlink,
    ):
        with pytest.raises(OSError, match="disk full"):
            merger._atomic_write_json(out, {"key": "val"})
    assert mock_unlink.called


def test_no_tmp_leak_after_success(merger: AdapterMerger, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    merger._atomic_write_json(out, {"key": "val"})
    leaked = list(tmp_path.glob("*.tmp"))
    assert leaked == [], f"泄漏的 tmp 文件: {leaked}"
