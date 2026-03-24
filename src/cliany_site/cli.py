import click
import os
from pathlib import Path
from importlib.metadata import version


def _ensure_dirs():
    home = Path.home() / ".cliany-site"
    (home / "adapters").mkdir(parents=True, exist_ok=True)
    (home / "sessions").mkdir(parents=True, exist_ok=True)


@click.group(invoke_without_command=True)
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

cli.add_command(doctor)
cli.add_command(login)
cli.add_command(explore_cmd)


if __name__ == "__main__":
    cli()
