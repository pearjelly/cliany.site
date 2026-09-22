import json
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.envelope import ok


def test_find_plain_output_shows_usable_target(tmp_home):
    target = {"ref": "12", "role": "textbox", "name": "Search orders",
              "score": 0.98, "confidence": 0.95, "model": "jev-test"}
    with patch("cliany_site.commands.browser.find._run_find", AsyncMock(return_value=ok("browser find", [target]))):
        result = CliRunner().invoke(
            cli, ["browser", "find", "--by", "intent", "--value", "order search", "--allow-remote"],
        )
    assert result.exit_code == 0
    for text in ('ref="12"', 'role="textbox"', 'name="Search orders"', 'score=0.98', 'confidence=0.95'):
        assert text in result.stdout


def test_find_plain_output_escapes_page_control_characters(tmp_home):
    target = {"ref": "12", "role": "button", "name": "Apply\n\x1b[2J"}
    with patch("cliany_site.commands.browser.find._run_find", AsyncMock(return_value=ok("browser find", [target]))):
        result = CliRunner().invoke(cli, ["browser", "find", "--value", "Apply"])
    assert result.exit_code == 0
    assert 'name="Apply\\n\\u001b[2J"' in result.stdout
    assert "\x1b" not in result.stdout


def test_find_root_json_output_remains_single_envelope(tmp_home):
    envelope = ok("browser find", [{"ref": "12", "name": "Apply", "role": "button"}])
    with patch("cliany_site.commands.browser.find._run_find", AsyncMock(return_value=envelope)):
        result = CliRunner().invoke(cli, ["--json", "browser", "find", "--value", "Apply"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == envelope
