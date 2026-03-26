#!/bin/bash
set -e

VERSION="${1:-}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"

echo "=== 发布 cliany-site 到 PyPI ==="

python -c "import build" 2>/dev/null || pip install build twine

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

echo "上传到 PyPI (Token 认证)..."
PYPI_TOKEN="${PYPI_TOKEN:-}"
if [ -n "$PYPI_TOKEN" ]; then
    twine upload "$DIST_DIR"/* -u "__token__" -p "$PYPI_TOKEN"
else
    twine upload "$DIST_DIR"/*
fi

echo "=== 发布完成 ==="
