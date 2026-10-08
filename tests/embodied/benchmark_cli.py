"""Run one CLI command with isolated cliany-site data and the user's normal HOME."""

from __future__ import annotations

import argparse
import os
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

    os.environ["CLIANY_RUNTIME_HOME"] = str(args.runtime_home.expanduser().resolve())
    config.reset_config()
    from cliany_site.cli import cli

    cli(args=cli_args, prog_name="cliany-site")


if __name__ == "__main__":
    main()
