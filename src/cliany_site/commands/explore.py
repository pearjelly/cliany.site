import asyncio
import json
import os
import sys
from urllib.parse import urlparse

import click

from cliany_site.config import get_config
from cliany_site.errors import CDP_UNAVAILABLE, EXECUTION_FAILED, LLM_UNAVAILABLE
from cliany_site.response import error_response, print_response, success_response


@click.command("explore")
@click.argument("url")
@click.argument("workflow_description")
@click.option("--force", is_flag=True, default=False, help="覆盖已有的 adapter（无需确认）")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.option("--interactive", "-i", is_flag=True, default=False, help="交互式探索模式")
@click.option("--extend", type=str, help="扩展现有适配器")
@click.option("--record/--no-record", default=True, help="是否记录探索过程")
@click.pass_context
def explore_cmd(
    ctx: click.Context,
    url: str,
    workflow_description: str,
    force: bool,
    json_mode: bool | None,
    interactive: bool,
    extend: str | None,
    record: bool,
):
    """探索网站工作流并生成 CLI adapter"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    if interactive and effective_json_mode:
        raise click.UsageError("--interactive 与 --json 不兼容，请删除 --json 标志")

    if interactive and not sys.stdin.isatty():
        raise click.UsageError("--interactive 需要 TTY 终端")

    async def _run():
        from cliany_site.browser.cdp import cdp_from_context
        from cliany_site.codegen.generator import (
            AdapterGenerator,
            _safe_domain,
            save_adapter,
        )
        from cliany_site.codegen.merger import AdapterMerger
        from cliany_site.explorer.engine import (
            WorkflowExplorer,
            _load_dotenv,
            _normalize_openai_base_url,
        )

        _load_dotenv()

        cdp = cdp_from_context(ctx)
        if not await cdp.check_available():
            return error_response(
                CDP_UNAVAILABLE,
                "Chrome CDP 不可用",
                "启动 Chrome 并开启 --remote-debugging-port=9222",
            )

        provider = os.getenv("CLIANY_LLM_PROVIDER", "anthropic").lower()
        if provider not in {"anthropic", "openai"}:
            return error_response(
                LLM_UNAVAILABLE,
                "LLM provider 配置无效",
                "请将 CLIANY_LLM_PROVIDER 设置为 anthropic 或 openai",
            )

        has_anthropic_key = bool(os.getenv("CLIANY_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        has_openai_key = bool(os.getenv("CLIANY_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))

        if provider == "anthropic" and not has_anthropic_key:
            return error_response(
                LLM_UNAVAILABLE,
                "Anthropic API Key 未配置",
                "设置 CLIANY_ANTHROPIC_API_KEY（或旧版 ANTHROPIC_API_KEY）",
            )

        if provider == "openai" and not has_openai_key:
            return error_response(
                LLM_UNAVAILABLE,
                "OpenAI API Key 未配置",
                "设置 CLIANY_OPENAI_API_KEY（OpenRouter key 也可）",
            )

        if provider == "openai":
            try:
                _normalize_openai_base_url(os.getenv("CLIANY_OPENAI_BASE_URL"))
            except (ValueError, TypeError) as e:
                return error_response(
                    LLM_UNAVAILABLE,
                    f"OpenAI base URL 配置无效: {e}",
                    "请使用 https://host[:port]/v1 格式，例如 https://sub2api.chinahrt.com/v1",
                )

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path

        if not effective_json_mode:
            from rich.console import Console

            console = Console(stderr=True)
            console.print(f"[cyan]正在探索: {url}[/cyan]")
        else:
            print(f"[explore] 正在探索: {url}", file=sys.stderr)

        from cliany_site.progress import NdjsonProgressReporter, RichProgressReporter

        reporter = NdjsonProgressReporter() if effective_json_mode else RichProgressReporter()

        try:
            cdp_url = root_obj.get("cdp_url")
            headless = root_obj.get("headless", False)
            explorer = WorkflowExplorer(
                cdp_url=cdp_url, headless=headless, interactive=interactive, extend_domain=extend
            )
            explore_result = await explorer.explore(url, workflow_description, progress=reporter, record=record)
        except (OSError, RuntimeError, ValueError) as e:
            return error_response(
                EXECUTION_FAILED,
                f"探索失败: {e}",
                "请检查 URL 是否可访问，LLM 配置是否正确",
            )

        post_analysis = {
            "atoms_extracted": 0,
            "atoms_reused": 0,
            "validation_warnings": 0,
            "action_quality_score": 1.0,
        }

        try:
            reuse_count = sum(1 for action in explore_result.actions if action.action_type == "reuse_atom")
            post_analysis["atoms_reused"] = reuse_count

            from cliany_site.explorer.analyzer import AtomExtractor

            llm_client = getattr(explorer, "_llm", None)
            if llm_client is None:
                raise RuntimeError("LLM client unavailable")
            extractor = AtomExtractor(llm_client, domain)
            new_atoms = await extractor.extract_atoms(explore_result)
            post_analysis["atoms_extracted"] = len(new_atoms)
        except (
            RuntimeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            OSError,
        ):
            pass

        print(f"[explore] 发现 {len(explore_result.commands)} 个命令建议", file=sys.stderr)
        print(
            f"[explore] 后分析: 提取 {post_analysis['atoms_extracted']} 个原子, "
            f"复用 {post_analysis['atoms_reused']} 个原子",
            file=sys.stderr,
        )

        adapter_dir = get_config().adapters_dir / _safe_domain(domain)

        from cliany_site.activity_log import write_log

        if force or not adapter_dir.exists():
            gen = AdapterGenerator()
            code = gen.generate(explore_result, domain)
            metadata = {
                "source_url": url,
                "workflow": workflow_description,
            }
            adapter_path = save_adapter(domain, code, metadata, explore_result=explore_result)
            commands_list = [cmd.name for cmd in explore_result.commands]
            print(f"[explore] Adapter 已生成: {adapter_path}", file=sys.stderr)
            write_log(
                "explore",
                domain,
                workflow_description,
                "success",
                f"created {len(commands_list)} commands",
            )
            return success_response(
                {
                    "domain": domain,
                    "adapter_path": adapter_path,
                    "adapter_mode": "created",
                    "commands": commands_list,
                    "commands_added": len(commands_list),
                    "commands_total": len(commands_list),
                    "pages_explored": len(explore_result.pages),
                    "actions_found": len(explore_result.actions),
                    "post_analysis": post_analysis,
                }
            )
        else:
            merger = AdapterMerger(domain)
            merge_result = merger.merge(
                explore_result,
                json_mode=effective_json_mode,
                workflow=workflow_description,
            )
            commands_list = [cmd.get("name", "") for cmd in merge_result.merged]
            adapter_path = str(merger.metadata_path.parent / "commands.py")
            print(f"[explore] Adapter 已合并: {adapter_path}", file=sys.stderr)
            write_log(
                "explore",
                domain,
                workflow_description,
                "success",
                f"merged {merge_result.added_count} new commands, total {merge_result.total_count}",
            )
            response_data: dict = {
                "domain": domain,
                "adapter_path": adapter_path,
                "adapter_mode": "merged",
                "commands": commands_list,
                "commands_added": merge_result.added_count,
                "commands_total": merge_result.total_count,
                "pages_explored": len(explore_result.pages),
                "actions_found": len(explore_result.actions),
                "post_analysis": post_analysis,
            }
            if merge_result.conflicts_resolved:
                response_data["conflicts_resolved"] = merge_result.conflicts_resolved
            return success_response(response_data)

    result = asyncio.run(_run())
    print_response(result, effective_json_mode)
