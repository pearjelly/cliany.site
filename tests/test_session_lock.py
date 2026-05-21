# pyright: reportMissingImports=false
import json
import logging
import multiprocessing
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _save_session_worker(args: tuple) -> None:
    domain, data_idx = args
    from cliany_site.session import save_session_data

    save_session_data(
        domain,
        {
            "cookies": [{"name": f"c{data_idx}", "value": str(data_idx)}],
            "localStorage": {},
        },
    )


def test_concurrent_save_session_no_corruption(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    domain = "lock-test.com"

    mock_cfg = MagicMock()
    mock_cfg.sessions_dir = sessions_dir

    with (
        patch("cliany_site.session.get_config", return_value=mock_cfg),
        patch(
            "cliany_site.security.save_encrypted_session",
            side_effect=RuntimeError("no key in test"),
        ),
    ):
        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(5) as pool:
            pool.map(_save_session_worker, [(domain, i) for i in range(5)])

    session_file = sessions_dir / f"{domain}.json"
    assert session_file.exists()
    data = json.loads(session_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "cookies" in data


def test_atomic_read_json_logs_parse_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from cliany_site.atomic_io import atomic_read_json

    bad_json_file = tmp_path / "bad.json"
    bad_json_file.write_text("{invalid json content}", encoding="utf-8")
    default: dict = {"fallback": True}

    with caplog.at_level(logging.ERROR, logger="cliany_site.atomic_io"):
        result = atomic_read_json(bad_json_file, default)

    assert result == default

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) >= 1
    assert str(bad_json_file) in error_records[0].getMessage()
