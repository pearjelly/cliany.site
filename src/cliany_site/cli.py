import importlib.metadata as metadata
import sys
from collections.abc import Sequence
from typing import NoReturn

import click

from cliany_site.config import get_config
from cliany_site.envelope import ErrorCode
from cliany_site.envelope import err as envelope_err
from cliany_site.logging_config import (
    LEVEL_DEBUG,
    LEVEL_QUIET,
    LEVEL_VERBOSE,
    setup_logging,
)
from cliany_site.response import print_response


def _ensure_dirs():
    cfg = get_config()
    cfg.adapters_dir.mkdir(parents=True, exist_ok=True)
    cfg.sessions_dir.mkdir(parents=True, exist_ok=True)


def _print_startup_banner(json_mode: bool) -> None:
    if json_mode:
        return
    import sys
    sys.stderr.write("⚡ cliany-site v0.9.0 — Agent-first web CLI\n")
    sys.stderr.flush()


def _is_json_mode(args: list[str] | None) -> bool:
    argv = list(args) if args is not None else sys.argv[1:]
    return "--json" in argv


def _build_click_error(exc: click.ClickException) -> dict:
    message = str(exc)
    ctx = getattr(exc, "ctx", None)
    command = ctx.command_path if ctx is not None else "cli"

    if isinstance(exc, click.UsageError):
        return envelope_err(
            command=command,
            code=ErrorCode.E_INVALID_PARAM,
            message=message,
            hint="使用 'cliany-site --help' 查看可用命令",
        )
    return envelope_err(command=command, code=ErrorCode.E_UNKNOWN, message=message)


def _render_error(exc: Exception, json_mode: bool) -> None:
    if json_mode:
        if isinstance(exc, click.ClickException):
            response = _build_click_error(exc)
        else:
            response = envelope_err(
                command="cli",
                code=ErrorCode.E_UNKNOWN,
                message=str(exc),
            )
        print_response(response, json_mode=True, exit_on_error=False)
        return

    if isinstance(exc, click.ClickException):
        exc.show(file=sys.stderr)
    else:
        click.echo(f"Error: {exc}", err=True)


class SafeGroup(click.Group):
    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: object,
    ) -> NoReturn:
        argv = list(args) if args is not None else sys.argv[1:]
        _print_startup_banner(_is_json_mode(argv))
        try:
            result = super().main(
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                windows_expand_args=windows_expand_args,
                **extra,
            )
        except click.exceptions.Exit as exc:
            raise SystemExit(exc.exit_code) from exc
        except SystemExit:
            raise
        except click.ClickException as exc:
            _render_error(exc, json_mode=_is_json_mode(argv))
            raise SystemExit(1) from exc
        except Exception as exc:
            _render_error(exc, json_mode=_is_json_mode(argv))
            raise SystemExit(1) from exc

        if isinstance(result, int):
            raise SystemExit(result)
        raise SystemExit(0)


@click.group(cls=SafeGroup, invoke_without_command=True)
@click.version_option(metadata.version("cliany-site"), "--version")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出模式")
@click.option("--verbose", "-v", is_flag=True, default=False, help="显示详细日志 (INFO)")
@click.option("--debug", is_flag=True, default=False, help="显示调试日志 (DEBUG)")
@click.option("--cdp-url", default=None, help="远程 CDP 地址 (如 ws://host:9222)")
@click.option("--headless", is_flag=True, default=False, help="以 Headless 模式启动 Chrome")
@click.option("--sandbox", is_flag=True, default=False, help="沙箱模式：限制跨域导航和危险操作")
@click.option("--explain", is_flag=True, default=False, help="输出 registry 命令契约 JSON")
@click.pass_context
def cli(ctx, json_mode, verbose, debug, cdp_url, headless, sandbox, explain):
    """cliany-site: 将任意网站 CLI 化"""
    _ensure_dirs()
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    ctx.obj["cdp_url"] = cdp_url
    ctx.obj["headless"] = headless
    ctx.obj["sandbox"] = sandbox

    if debug:
        log_level = LEVEL_DEBUG
    elif verbose:
        log_level = LEVEL_VERBOSE
    else:
        log_level = LEVEL_QUIET
    setup_logging(level=log_level, json_format=json_mode)

    if explain:
        import json as _json

        from cliany_site.envelope import ErrorCode
        from cliany_site.registry import Registry

        try:
            version = metadata.version("cliany-site")
        except Exception:
            version = "unknown"

        builtin_names = list(ctx.command.commands.keys())
        reg = Registry().collect(
            builtin_names=builtin_names,
            atom_names=[],
            adapter_entries=[],
        )

        commands = []
        for entry in reg.to_explain_dict().get("commands", []):
            commands.append({
                "name": entry.get("name", ""),
                "source": entry.get("source", "builtin"),
                "params": entry.get("params", []),
                "returns": entry.get("returns", {}),
                "examples": entry.get("examples", [])
            })

        error_codes = []
        for attr_name in dir(ErrorCode):
            if attr_name.startswith("E_"):
                error_codes.append({
                    "code": attr_name,
                    "message": str(getattr(ErrorCode, attr_name)),
                    "hint": None
                })

        result = {
            "schema_version": "1",
            "binary": "cliany-site",
            "version": version,
            "commands": commands,
            "error_codes": error_codes
        }

        if json_mode:
            click.echo(_json.dumps(result, ensure_ascii=False, indent=2))
        else:
            from rich.console import Console
            console = Console()
            console.print_json(json=_json.dumps(result))
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


from cliany_site.commands.check import check_cmd
from cliany_site.commands.doctor import doctor
from cliany_site.commands.explore import explore_cmd
from cliany_site.commands.list_cmd import list_cmd
from cliany_site.commands.login import login
from cliany_site.commands.market import market_group
from cliany_site.commands.replay import replay
from cliany_site.commands.report import report_group
from cliany_site.commands.serve import serve_cmd
from cliany_site.commands.tui import tui_cmd
from cliany_site.commands.workflow import workflow_group

cli.add_command(doctor)
cli.add_command(login)
cli.add_command(explore_cmd)
cli.add_command(list_cmd)
cli.add_command(replay)
cli.add_command(tui_cmd)
cli.add_command(report_group)
cli.add_command(check_cmd)
cli.add_command(workflow_group)
cli.add_command(market_group)
cli.add_command(serve_cmd)

from cliany_site.commands.browser import browser_group

cli.add_command(browser_group)

from cliany_site.commands.verify import verify_cmd

cli.add_command(verify_cmd)

from cliany_site.commands.adapter_cmd import adapter_group

cli.add_command(adapter_group)

from cliany_site.loader import register_adapters

register_adapters(cli)


if __name__ == "__main__":
    cli()
