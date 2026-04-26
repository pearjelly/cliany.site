#!/usr/bin/env bash
set -euo pipefail
echo "atom_part_b.sh: 验证 browser find/click/type 命令注册"
uv run cliany-site browser --help | grep -E "find|click|type"
echo "✓ atom_part_b: find/click/type 子命令已注册"
