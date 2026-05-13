# v0.11.0 发布清单

## 发布前检查

### 1. 确认基础测试通过
```bash
uv run pytest -q
```
预期输出：所有核心单元测试和集成测试通过。

### 2. 确认 QA 脚本（含 Obscura）通过
```bash
bash qa/run_all.sh
```
特别注意以下 Obscura 相关脚本的输出：
- `qa/test_obscura_smoke.sh`
- `qa/test_obscura_compat.sh`

### 3. 确认环境检查正常
```bash
cliany-site doctor --json
cliany-site obscura doctor --json
```

### 4. 构建验证
```bash
uv build
```
预期输出：在 `dist/` 目录下生成 `cliany_site-0.11.0.tar.gz` 和 `cliany_site-0.11.0-py3-none-any.whl`。

## 发布步骤（需手动执行）

### 5. 发布到 PyPI
```bash
uv publish
```
注意：确保已配置正确的 PyPI 凭据。

### 6. 创建 Git Tag 并推送
```bash
git tag v0.11.0
git push origin v0.11.0
```

### 7. 创建 GitHub Release
在 GitHub 上创建 Release：
- **Tag**: `v0.11.0`
- **Title**: `v0.11.0 - Obscura Experimental Integration`
- **Description**: 复制自 `CHANGELOG.md` 的 `0.11.0` 条目内容。
- **Assets**: 上传 `dist/` 目录下的构建产物。

## 发布后验证

### 8. 确认分发平台
- 检查 PyPI：https://pypi.org/project/cliany-site/ 是否已更新至 v0.11.0。
- 检查 GitHub Releases 页面是否显示正确。

### 9. 确认安装验证
```bash
# 在新环境中安装
pip install cliany-site==0.11.0

# 验证版本
cliany-site --version
```

### 10. Obscura 冒烟验证（可选）
```bash
cliany-site obscura install --json
CLIANY_BROWSER_PROVIDER=obscura cliany-site obscura status --json
```
