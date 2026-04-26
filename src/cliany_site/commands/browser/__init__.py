import importlib
import pkgutil

import click

browser_group = click.Group(name="browser", help="浏览器原子命令（零 LLM）")

_pkg_path = __path__
for _finder, _name, _ispkg in pkgutil.iter_modules(_pkg_path):
    if not _name.startswith("_"):
        importlib.import_module(f"cliany_site.commands.browser.{_name}")
