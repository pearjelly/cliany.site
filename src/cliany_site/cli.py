import sys
from importlib.metadata import version
from pathlib import Path
from typing import NoReturn, Sequence

import click

from cliany_site.errors import COMMAND_NOT_FOUND, EXECUTION_FAILED
from cliany_site.response import error_response, print_response


def _ensure_dirs():
    home = Path.home() / ".cliany-site"
    (home / "adapters").mkdir(parents=True, exist_ok=True)
    (home / "sessions").mkdir(parents=True, exist_ok=True)


def _is_json_mode(args: list[str] | None) -> bool:
    argv = list(args) if args is not None else sys.argv[1:]
    return "--json" in argv


def _build_click_error(exc: click.ClickException) -> dict:
    message = str(exc)
    code = EXECUTION_FAILED
    fix = None
    if isinstance(exc, click.UsageError):
        if "No such command" in message:
            code = COMMAND_NOT_FOUND
        fix = "使用 'cliany-site --help' 查看可用命令"
    return error_response(code=code, message=message, fix=fix)


def _render_error(exc: Exception, json_mode: bool) -> None:
    if json_mode:
        if isinstance(exc, click.ClickException):
            response = _build_click_error(exc)
        else:
            response = error_response(EXECUTION_FAILED, str(exc))
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
        argv = list(args) if args is not None else None
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
            raise SystemExit(exc.exit_code)
        except SystemExit:
            raise
        except click.ClickException as exc:
            _render_error(exc, json_mode=_is_json_mode(argv))
            raise SystemExit(1)
        except Exception as exc:
            _render_error(exc, json_mode=_is_json_mode(argv))
            raise SystemExit(1)

        if isinstance(result, int):
            raise SystemExit(result)
        raise SystemExit(0)


@click.group(cls=SafeGroup, invoke_without_command=True)
@click.version_option(version("cliany-site"), "--version")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出模式")
@click.pass_context
def cli(ctx, json_mode):
    """cliany-site: 将任意网站 CLI 化"""
    _ensure_dirs()
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


from cliany_site.commands.doctor import doctor
from cliany_site.commands.explore import explore_cmd
from cliany_site.commands.login import login
from cliany_site.commands.list_cmd import list_cmd
from cliany_site.commands.tui import tui_cmd
from cliany_site.commands.report import report_group

cli.add_command(doctor)
cli.add_command(login)
cli.add_command(explore_cmd)
cli.add_command(list_cmd)
cli.add_command(tui_cmd)
cli.add_command(report_group)

from cliany_site.loader import register_adapters

register_adapters(cli)


if __name__ == "__main__":
    cli()
