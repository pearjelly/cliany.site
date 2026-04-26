#!/usr/bin/env bash
set -euo pipefail
echo "atom_part_c.sh: 验证 browser extract/eval 命令注册"
uv run cliany-site browser --help | grep -E "extract|eval"
echo "✓ atom_part_c: extract/eval 子命令已注册"
