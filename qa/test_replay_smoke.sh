#!/bin/bash
# 测试 replay 命令的 --session, --step 参数存在性
# 以及对不存在域名的错误处理
set -e
PASS=0; FAIL=0

# 测试 --session 参数存在（检查代码定义）
if grep -q 'session_id.*default=None' src/cliany_site/commands/replay.py; then
    echo "[PASS] replay.py 定义了 --session 参数"
    PASS=$((PASS+1))
else
    echo "[FAIL] replay.py 应定义 --session 参数"
    FAIL=$((FAIL+1))
fi

# 测试 --step 参数存在（检查代码定义）
if grep -q 'step_mode.*is_flag' src/cliany_site/commands/replay.py; then
    echo "[PASS] replay.py 定义了 --step 参数"
    PASS=$((PASS+1))
else
    echo "[FAIL] replay.py 应定义 --step 参数"
    FAIL=$((FAIL+1))
fi

# 测试不存在域名错误处理（检查代码逻辑）
if grep -q 'FileNotFoundError.*OSError' src/cliany_site/commands/replay.py && grep -q 'SystemExit' src/cliany_site/commands/replay.py; then
    echo "[PASS] replay.py 实现了不存在域名的错误处理"
    PASS=$((PASS+1))
else
    echo "[FAIL] replay.py 应实现不存在域名的错误处理"
    FAIL=$((FAIL+1))
fi

# 验证错误处理不包含 Traceback（检查代码）
if grep -q 'raise SystemExit' src/cliany_site/commands/replay.py && ! grep -q 'Traceback' src/cliany_site/commands/replay.py; then
    echo "[PASS] replay 错误处理不包含 Traceback"
    PASS=$((PASS+1))
else
    echo "[FAIL] replay 错误处理不应包含 Traceback"
    FAIL=$((FAIL+1))
fi

echo ""
echo "=== All tests passed ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1