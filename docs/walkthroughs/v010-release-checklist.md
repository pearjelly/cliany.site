# v0.10.0 发布清单

## 发布前检查

### 1. 确认测试全绿
```bash
uv run pytest -q
```
预期输出：所有测试通过（类似 "1160 passed"）。

### 2. 确认 QA 脚本通过
```bash
bash qa/run_all.sh
```
预期输出：所有 QA 检查通过。

### 3. 构建包
```bash
uv build
```
预期输出：生成 `dist/` 目录中的 `.whl` 和 `.tar.gz` 文件。

## 发布步骤（需手动执行）

### 4. 发布到 PyPI
```bash
uv publish
```
注意：需要配置 PyPI 凭据（`__token__` 或用户名/密码）。

### 5. 创建 Git Tag 并推送
```bash
git tag v0.10.0
git push origin v0.10.0
```

### 6. 创建 GitHub Release
在 GitHub 上创建 Release：
- Tag: `v0.10.0`
- Title: `v0.10.0`
- Description: 复制自 CHANGELOG.md 的 v0.10.0 条目
- 附加构建产物（可选）：`dist/cliany_site-0.10.0-py3-none-any.whl` 和 `dist/cliany_site-0.10.0.tar.gz`

## 发布后验证
- 确认 PyPI 页面：https://pypi.org/project/cliany-site/ 显示 v0.10.0
- 确认 GitHub Release 已创建
- 可选：安装测试 `pip install cliany-site==0.10.0`