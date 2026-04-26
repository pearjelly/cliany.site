#!/usr/bin/env bash
set -euo pipefail
echo "test_verify.sh: 验证 verify 命令注册"
uv run cliany-site verify --help
echo "✓ test_verify: verify 子命令已注册"
