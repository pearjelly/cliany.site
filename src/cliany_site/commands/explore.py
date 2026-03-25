import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click

from cliany_site.errors import CDP_UNAVAILABLE, EXECUTION_FAILED, LLM_UNAVAILABLE
from cliany_site.response import error_response, print_response, success_response


@click.command("explore")
@click.argument("url")
@click.argument("workflow_description")
@click.option(
    "--force", is_flag=True, default=False, help="覆盖已有的 adapter（无需确认）"
)
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def explore_cmd(
    ctx: click.Context,
    url: str,
    workflow_description: str,
    force: bool,
    json_mode: bool | None,
):
    """探索网站工作流并生成 CLI adapter"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = (
        json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    )

    async def _run():
        from cliany_site.browser.cdp import CDPConnection
        from cliany_site.codegen.generator import AdapterGenerator, save_adapter
        from cliany_site.explorer.engine import WorkflowExplorer, _load_dotenv

        _load_dotenv()

        cdp = CDPConnection()
        if not await cdp.check_available():
            return error_response(
                CDP_UNAVAILABLE,
                "Chrome CDP 不可用",
                "启动 Chrome 并开启 --remote-debugging-port=9222",
            )

        if not (
            os.getenv("CLIANY_ANTHROPIC_API_KEY")
            or os.getenv("CLIANY_OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        ):
            return error_response(
                LLM_UNAVAILABLE,
                "LLM API Key 未配置",
                "设置 CLIANY_ANTHROPIC_API_KEY 或 CLIANY_OPENAI_API_KEY 环境变量",
            )

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path

        adapter_dir = Path.home() / ".cliany-site" / "adapters" / domain
        if adapter_dir.exists() and not force:
            if not effective_json_mode:
                from rich.console import Console

                console = Console(stderr=True)
                console.print(f"[yellow]已存在 adapter: {domain}[/yellow]")
                if not click.confirm("是否覆盖？", default=False):
                    return success_response(
                        {
                            "status": "skipped",
                            "domain": domain,
                            "message": "用户取消覆盖",
                        }
                    )

        if not effective_json_mode:
            from rich.console import Console

            console = Console(stderr=True)
            console.print(f"[cyan]正在探索: {url}[/cyan]")
        else:
            print(f"[explore] 正在探索: {url}", file=sys.stderr)

        try:
            explorer = WorkflowExplorer()
            explore_result = await explorer.explore(url, workflow_description)
        except Exception as e:
            return error_response(
                EXECUTION_FAILED,
                f"探索失败: {e}",
                "请检查 URL 是否可访问，LLM 配置是否正确",
            )

        print(
            f"[explore] 发现 {len(explore_result.commands)} 个命令建议", file=sys.stderr
        )
        gen = AdapterGenerator()
        code = gen.generate(explore_result, domain)

        metadata = {
            "source_url": url,
            "workflow": workflow_description,
        }
        adapter_path = save_adapter(domain, code, metadata)

        commands_list = [cmd.name for cmd in explore_result.commands]
        print(f"[explore] Adapter 已生成: {adapter_path}", file=sys.stderr)

        return success_response(
            {
                "domain": domain,
                "adapter_path": adapter_path,
                "commands": commands_list,
                "pages_explored": len(explore_result.pages),
                "actions_found": len(explore_result.actions),
            }
        )

    result = asyncio.run(_run())
    print_response(result, effective_json_mode)
