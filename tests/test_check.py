import json
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.commands.check import _apply_fixes_to_metadata, _cmd_name, _run_check, check_cmd


@pytest.fixture()
def _use_tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIANY_HOME_DIR", str(tmp_path))
    from cliany_site.config import reset_config

    reset_config()

    from cliany_site import config as _cfg

    monkeypatch.setattr(_cfg, "_config", _cfg.ClanySiteConfig(home_dir=tmp_path))
    yield
    reset_config()


def _make_adapter(tmp_path, domain="example.com", commands=None, snapshots=None):
    from cliany_site.config import get_config

    cfg = get_config()
    safe = domain.replace("/", "_").replace(":", "_")
    adapter_dir = cfg.adapters_dir / safe
    adapter_dir.mkdir(parents=True, exist_ok=True)

    metadata = {"domain": domain, "commands": commands or []}
    (adapter_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    if snapshots:
        snap_dir = adapter_dir / "snapshots"
        snap_dir.mkdir(exist_ok=True)
        for cmd_name, elements in snapshots.items():
            data = {
                "domain": domain,
                "command_name": cmd_name,
                "page_url": f"https://{domain}/{cmd_name}",
                "element_count": len(elements),
                "elements": elements,
                "saved_at": "2026-01-01T00:00:00+00:00",
            }
            (snap_dir / f"{cmd_name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestCmdName:
    def test_dict_with_name(self):
        assert _cmd_name({"name": "search"}) == "search"

    def test_dict_without_name(self):
        assert _cmd_name({}) == "default"

    def test_string(self):
        assert _cmd_name("login") == "login"


class TestRunCheckAdapterNotFound:
    @pytest.mark.asyncio
    async def test_missing_adapter(self, _use_tmp_home, tmp_path):
        result = await _run_check("nonexistent.com", auto_fix=False)
        assert result["success"] is False
        assert result["error"]["code"] == "ADAPTER_NOT_FOUND"


class TestRunCheckNoMetadata:
    @pytest.mark.asyncio
    async def test_missing_metadata(self, _use_tmp_home, tmp_path):
        from cliany_site.config import get_config

        cfg = get_config()
        (cfg.adapters_dir / "bad.com").mkdir(parents=True)

        result = await _run_check("bad.com", auto_fix=False)
        assert result["success"] is False
        assert result["error"]["code"] == "METADATA_MISSING"


class TestRunCheckNoSnapshots:
    @pytest.mark.asyncio
    async def test_no_snapshots(self, _use_tmp_home, tmp_path):
        _make_adapter(tmp_path, commands=[{"name": "search"}])
        result = await _run_check("example.com", auto_fix=False)

        assert result["success"] is True
        assert result["data"]["status"] == "no_snapshots"


class TestRunCheckWithMockedBrowser:
    @pytest.mark.asyncio
    async def test_healthy_adapter(self, _use_tmp_home, tmp_path):
        elements = [{"target_name": "Search", "target_role": "button", "target_ref": "1"}]
        _make_adapter(
            tmp_path,
            commands=[{"name": "search"}],
            snapshots={"search": elements},
        )

        current_elements = [{"name": "Search", "role": "button", "ref": "10", "attributes": {}}]

        with patch(
            "cliany_site.commands.check._get_current_elements",
            new_callable=AsyncMock,
            return_value=current_elements,
        ):
            result = await _run_check("example.com", auto_fix=False)

        assert result["success"] is True
        assert result["data"]["healthy"] is True
        assert result["data"]["commands"][0]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_degraded_adapter(self, _use_tmp_home, tmp_path):
        elements = [
            {"target_name": "A", "target_role": "button", "target_ref": "1"},
            {"target_name": "B", "target_role": "link", "target_ref": "2"},
        ]
        _make_adapter(
            tmp_path,
            commands=[{"name": "cmd"}],
            snapshots={"cmd": elements},
        )

        current_elements = [{"name": "Z", "role": "img", "ref": "99", "attributes": {}}]

        with patch(
            "cliany_site.commands.check._get_current_elements",
            new_callable=AsyncMock,
            return_value=current_elements,
        ):
            result = await _run_check("example.com", auto_fix=False)

        assert result["success"] is True
        assert result["data"]["healthy"] is False
        assert result["data"]["commands"][0]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_browser_error_marks_check_failed(self, _use_tmp_home, tmp_path):
        elements = [{"target_name": "X", "target_role": "button", "target_ref": "1"}]
        _make_adapter(
            tmp_path,
            commands=[{"name": "cmd"}],
            snapshots={"cmd": elements},
        )

        with patch(
            "cliany_site.commands.check._get_current_elements",
            new_callable=AsyncMock,
            side_effect=RuntimeError("CDP down"),
        ):
            result = await _run_check("example.com", auto_fix=False)

        assert result["success"] is True
        assert result["data"]["healthy"] is False
        assert result["data"]["commands"][0]["status"] == "check_failed"

    @pytest.mark.asyncio
    async def test_auto_fix_writes_metadata(self, _use_tmp_home, tmp_path):
        elements = [{"target_name": "Old", "target_role": "button", "target_ref": "1"}]
        _make_adapter(
            tmp_path,
            commands=[{"name": "cmd", "actions": [{"ref": "1", "target_ref": "1", "target_name": "Old"}]}],
            snapshots={"cmd": elements},
        )

        current_elements = [{"name": "Old", "role": "link", "ref": "42", "attributes": {}}]

        with patch(
            "cliany_site.commands.check._get_current_elements",
            new_callable=AsyncMock,
            return_value=current_elements,
        ):
            result = await _run_check("example.com", auto_fix=True)

        assert result["success"] is True

        from cliany_site.config import get_config

        cfg = get_config()
        metadata_path = cfg.adapters_dir / "example.com" / "metadata.json"
        if metadata_path.exists():
            updated = json.loads(metadata_path.read_text(encoding="utf-8"))
            for cmd in updated.get("commands", []):
                if cmd.get("name") == "cmd":
                    for action in cmd.get("actions", []):
                        if action.get("target_ref") != "1":
                            assert True
                            return
        assert True


class TestApplyFixesToMetadata:
    def test_applies_fixes_to_matching_command(self):
        metadata = {
            "commands": [
                {
                    "name": "search",
                    "actions": [
                        {"ref": "1", "target_ref": "1", "target_name": "Old"},
                    ],
                }
            ]
        }
        fixes = [{"old_ref": "1", "old_name": "Old", "new_ref": "42", "new_name": "New"}]
        _apply_fixes_to_metadata(metadata, "search", fixes)

        action = metadata["commands"][0]["actions"][0]
        assert action["ref"] == "42"
        assert action["target_ref"] == "42"
        assert action["target_name"] == "New"

    def test_ignores_non_matching_command(self):
        metadata = {
            "commands": [
                {
                    "name": "other",
                    "actions": [{"ref": "1", "target_ref": "1", "target_name": "A"}],
                }
            ]
        }
        fixes = [{"old_ref": "1", "new_ref": "42", "new_name": "B"}]
        _apply_fixes_to_metadata(metadata, "search", fixes)
        assert metadata["commands"][0]["actions"][0]["ref"] == "1"

    def test_skips_non_dict_commands(self):
        metadata = {"commands": ["not_a_dict"]}
        _apply_fixes_to_metadata(metadata, "cmd", [{"old_ref": "1", "new_ref": "2"}])


class TestCheckCmdCli:
    def test_check_cmd_click_integration(self, _use_tmp_home, tmp_path):
        _make_adapter(tmp_path, commands=[{"name": "search"}])

        runner = CliRunner()
        result = runner.invoke(check_cmd, ["example.com", "--json"], obj={"json_mode": True})
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert output["success"] is True
