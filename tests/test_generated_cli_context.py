import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import click
import pytest

from cliany_site.codegen import runtime_helpers
from cliany_site.commands.browser.extract import _do_structured_extract


@pytest.mark.parametrize("root_obj,prefix", [
    ({}, []),
    ({"cdp_url": "ws://localhost:9333"}, ["--cdp-url", "ws://localhost:9333"]),
    ({"headless": True}, ["--headless"]),
    ({"cdp_url": "ws://localhost:9333", "headless": True}, ["--cdp-url", "ws://localhost:9333", "--headless"]),
])
def test_nested_atom_inherits_root_browser_options(tmp_home, monkeypatch, root_obj, prefix):
    calls = []

    def invoke(runner, cli, args, **kwargs):
        calls.append(args)
        return SimpleNamespace(output=json.dumps({"ok": True, "data": {}}))

    monkeypatch.setattr(runtime_helpers.CliRunner, "invoke", invoke)
    with click.Context(click.Group("root"), obj=root_obj) as root:
        with click.Context(click.Command("generated"), parent=root, obj={"cdp_url": "ignored"}):
            runtime_helpers.run_atom(["browser", "click", "--text", "Apply"], session="example.com")
    assert calls == [prefix + ["browser", "click", "--text", "Apply", "--session", "example.com", "--json"]]


def test_recorded_type_replaces_existing_field_value(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return {"ok": True}

    monkeypatch.setattr(runtime_helpers, "run_atom", run)
    runtime_helpers._execute_single_step({"type": "type", "target_name": "Name", "value": "Ada"}, "example.com")
    assert calls == [["browser", "type", "--text", "Name", "--value", "Ada", "--clear"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw,expected", [
    ('[{"name":"Ada"}]', [{"name": "Ada"}]),
    ('{"text":"Ada"}', {"text": "Ada"}),
    ([{"name": "Ada"}], [{"name": "Ada"}]),
    ("[]", []),
    ("[malformed", "[malformed"),
])
async def test_structured_extract_decodes_browser_json(raw, expected):
    page = SimpleNamespace(evaluate=AsyncMock(return_value=raw))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))
    result = await _do_structured_extract(session, "output", "list", {"name": ""})
    assert result == expected
