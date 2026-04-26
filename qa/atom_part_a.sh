#!/usr/bin/env bash
set -euo pipefail
echo "atom_part_a.sh: 验证 browser 命令注册"
uv run cliany-site browser --help | grep -E "state|navigate|wait|screenshot"
echo "✓ atom_part_a: browser 子命令已注册"
