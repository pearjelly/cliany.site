import json
from concurrent.futures import ThreadPoolExecutor

import click
import pytest

from cliany_site.workflow.engine import ClickAdapterExecutor


@pytest.mark.parametrize("in_worker", [False, True])
def test_executor_snapshots_root_options_before_dispatch(in_worker):
    @click.group()
    @click.option("--cdp-url")
    @click.option("--headless", is_flag=True)
    @click.option("--sandbox", is_flag=True)
    @click.option("--force-browser", is_flag=True)
    @click.option("--diagnose", is_flag=True)
    @click.pass_context
    def root(ctx, **options):
        ctx.obj = options

    @root.group()
    def adapter():
        pass

    @adapter.command()
    @click.option("--json", "json_mode", is_flag=True)
    @click.pass_context
    def inspect(ctx, json_mode):
        click.echo(json.dumps({"ok": True, "data": ctx.find_root().obj}))

    options = {"cdp_url": "ws://localhost:9333", "headless": True,
               "sandbox": True, "force_browser": True, "diagnose": True}
    with click.Context(root, obj=options) as parent:
        with click.Context(click.Command("workflow"), parent=parent, obj={}):
            executor = ClickAdapterExecutor(root)
    options["cdp_url"] = "ws://wrong:9222"
    if in_worker:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(executor.execute_step, "adapter", "inspect", {}).result()
    else:
        result = executor.execute_step("adapter", "inspect", {})
    assert result["ok"] is True
    assert result["data"] == {**options, "cdp_url": "ws://localhost:9333"}
