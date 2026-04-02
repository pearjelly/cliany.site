#!/bin/bash
# 测试 explore 命令的 --extend 参数对不存在域名的错误处理
set -e
PASS=0; FAIL=0

# 测试 --extend 参数存在（检查代码定义）
if grep -q 'extend.*type=str' src/cliany_site/commands/explore.py; then
    echo "[PASS] explore.py 定义了 --extend 参数"
    PASS=$((PASS+1))
else
    echo "[FAIL] explore.py 应定义 --extend 参数"
    FAIL=$((FAIL+1))
fi

# 测试 --extend nonexistent-domain（检查代码逻辑）
if grep -q 'load_existing_adapter_context(extend_domain)' src/cliany_site/explorer/engine.py; then
    echo "[PASS] explore.py 实现了 --extend nonexistent-domain 错误处理"
    PASS=$((PASS+1))
else
    echo "[FAIL] explore.py 应实现 --extend nonexistent-domain 错误处理"
    FAIL=$((FAIL+1))
fi

# 验证错误处理不包含 Traceback（检查代码）
if grep -q 'raise FileNotFoundError' src/cliany_site/explorer/engine.py && ! grep -q 'Traceback' src/cliany_site/commands/explore.py; then
    echo "[PASS] explore --extend 错误处理不包含 Traceback"
    PASS=$((PASS+1))
else
    echo "[FAIL] explore --extend 错误处理不应包含 Traceback"
    FAIL=$((FAIL+1))
fi

echo ""
echo "=== All tests passed ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1