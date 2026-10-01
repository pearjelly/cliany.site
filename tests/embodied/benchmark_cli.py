"""Run one CLI command with isolated cliany-site data and the user's normal HOME."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from cliany_site import config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-home", type=Path, required=True)
    parser.add_argument("cli_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cli_args = args.cli_args[1:] if args.cli_args[:1] == ["--"] else args.cli_args
    if not cli_args:
        parser.error("a cliany-site command is required")

    config._config = replace(config.get_config(), home_dir=args.runtime_home)
    from cliany_site.cli import cli

    cli(args=cli_args, prog_name="cliany-site")


if __name__ == "__main__":
    main()
