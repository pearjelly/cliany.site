#!/bin/bash
set -e

VERSION="${1:-}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"

echo "=== 发布 cliany-site 到 PyPI ==="

python -c "import build" 2>/dev/null || python -m pip install build twine

if [ -n "$VERSION" ]; then
    echo "更新版本号到 $VERSION..."
    cd "$PROJECT_DIR"
    sed -i.bak "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    rm -f pyproject.toml.bak
fi

cd "$PROJECT_DIR"
rm -rf "$DIST_DIR"
python -m build

echo "构建产物:"
ls -lh "$DIST_DIR"

TOKEN_FILE="$(dirname "$0")/.pypi-token"
if [ -z "$PYPI_TOKEN" ] && [ -f "$TOKEN_FILE" ]; then
    echo "提示: 正在使用本地 scripts/.pypi-token；请勿提交该文件，CI/正式发布建议使用 PYPI_TOKEN 环境变量。" >&2
    PYPI_TOKEN=$(cat "$TOKEN_FILE")
fi

echo "上传到 PyPI (Token 认证)..."
if [ -n "$PYPI_TOKEN" ]; then
    twine upload "$DIST_DIR"/* -u "__token__" -p "$PYPI_TOKEN" --skip-existing
else
    echo "错误: 未找到 PyPI Token。请设置 PYPI_TOKEN，或仅在本机创建已忽略的 scripts/.pypi-token。"
    exit 1
fi

echo "=== 发布完成 ==="
