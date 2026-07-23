from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cliany_site.codegen.generator import METADATA_SCHEMA_VERSION
from cliany_site.codegen.merger import AdapterMerger
from cliany_site.commands.verify import _load_schema, _verify_single
from cliany_site.explorer.models import CommandSuggestion


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
        pytest.raises(OSError, match="disk full"),
    ):
        merger._atomic_write_json(out, {"key": "val"})
    assert mock_unlink.called


def test_no_tmp_leak_after_success(merger: AdapterMerger, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    merger._atomic_write_json(out, {"key": "val"})
    leaked = list(tmp_path.glob("*.tmp"))
    assert leaked == [], f"泄漏的 tmp 文件: {leaked}"


def test_merge_preserves_declared_empty_result_and_v3_metadata(
    merger: AdapterMerger, tmp_path: Path
) -> None:
    merge_result = merger.merge_commands(
        existing=[],
        new_commands=[
            CommandSuggestion(
                name="search-results",
                description="确认是否存在匹配结果",
                args=[],
                action_steps=[],
                expects_nonempty=False,
            )
        ],
        new_actions=[],
    )

    with patch("cliany_site.codegen.generator.get_config") as mock_cfg:
        mock_cfg.return_value.adapters_dir = tmp_path
        merger.save_merged(merge_result, workflow="确认零匹配")

    metadata_path = tmp_path / "test.com" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == METADATA_SCHEMA_VERSION
    assert metadata["signature"]
    assert metadata["commands"][0]["expects_nonempty"] is False

    with patch("cliany_site.commands.verify.get_config") as mock_cfg:
        mock_cfg.return_value.adapters_dir = tmp_path
        verification = _verify_single("test.com", _load_schema())

    assert verification["verdict"] == "ok"
