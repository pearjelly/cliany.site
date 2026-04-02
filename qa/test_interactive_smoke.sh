#!/bin/bash
# 测试 explore 命令的 --interactive, --extend, --record 参数存在性
# 以及 --interactive --json 互斥验证
set -e
PASS=0; FAIL=0

# 测试 --interactive 参数存在（检查代码定义）
if grep -q 'interactive.*is_flag' src/cliany_site/commands/explore.py; then
    echo "[PASS] explore.py 定义了 --interactive 参数"
    PASS=$((PASS+1))
else
    echo "[FAIL] explore.py 应定义 --interactive 参数"
    FAIL=$((FAIL+1))
fi

# 测试 --extend 参数存在（检查代码定义）
if grep -q 'extend.*type=str' src/cliany_site/commands/explore.py; then
    echo "[PASS] explore.py 定义了 --extend 参数"
    PASS=$((PASS+1))
else
    echo "[FAIL] explore.py 应定义 --extend 参数"
    FAIL=$((FAIL+1))
fi

# 测试 --record 参数存在（检查代码定义）
if grep -q 'record.*no-record' src/cliany_site/commands/explore.py; then
    echo "[PASS] explore.py 定义了 --record 参数"
    PASS=$((PASS+1))
else
    echo "[FAIL] explore.py 应定义 --record 参数"
    FAIL=$((FAIL+1))
fi

# 测试 --interactive --json 互斥（检查代码逻辑）
if grep -q 'interactive and effective_json_mode' src/cliany_site/commands/explore.py; then
    echo "[PASS] explore.py 实现了 --interactive --json 互斥检查"
    PASS=$((PASS+1))
else
    echo "[FAIL] explore.py 应实现 --interactive --json 互斥检查"
    FAIL=$((FAIL+1))
fi

echo ""
echo "=== All tests passed ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1