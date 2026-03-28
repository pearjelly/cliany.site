# cliany-site Skill 发布指南

**日期:** 2026-03-28
**状态:** 已就绪，待 ClawHub 授权后一键发布

## Skill 文件结构

```
skills/cliany-site/          # ClawHub 发布包（含 clawdbot 嵌套 metadata）
├── SKILL.md                 # 核心 skill 定义
├── README.md                # ClawHub 发布用 README
├── clawhub.json             # ClawHub 补充元数据
└── scripts/
    └── install.sh           # 多平台一键安装脚本

.opencode/skills/cliany-site/
└── SKILL.md                 # OpenCode 专用版（纯 string-to-string metadata）

SKILL.md (根目录)            # 通用 skill（Claude Code / SkillsMP 自动发现）
```

### 三个 SKILL.md 的区别

| 文件 | 用途 | metadata 格式 | body 语言 |
|------|------|-------------|----------|
| `skills/cliany-site/SKILL.md` | ClawHub 发布 | 嵌套 `metadata.clawdbot`（ClawHub 要求） | 英文 |
| `.opencode/skills/cliany-site/SKILL.md` | OpenCode 项目级 | 扁平 string-to-string（OpenCode 要求） | 英文 |
| `SKILL.md`（根） | Claude Code / SkillsMP | 简洁 metadata | 中文 |

## 发布到 ClawHub

### 前置条件

```bash
# 安装 clawhub CLI
npm i -g clawhub

# 验证版本
clawhub --cli-version
# → 0.9.0
```

### 步骤 1: 登录 ClawHub

```bash
# 浏览器登录（推荐，会打开 GitHub OAuth）
clawhub login

# 或使用 Token 登录（CI 场景）
clawhub login --token "$CLAWHUB_TOKEN" --no-browser

# 验证登录
clawhub whoami
```

> 注意：GitHub 账号需注册超过 1 周才能发布。

### 步骤 2: 发布

```bash
clawhub publish ./skills/cliany-site \
  --slug "cliany-site" \
  --name "cliany-site" \
  --version "0.1.1" \
  --changelog "Initial publish: web workflow automation via Chrome CDP and LLM" \
  --tags "latest"
```

发布成功后可在 https://clawhub.ai 搜索 `cliany-site` 验证。

### 步骤 3: 验证安装

```bash
# 从 ClawHub 安装（验证发布成功）
clawhub install cliany-site

# 或用 openclaw 原生命令
openclaw skills install cliany-site
```

### 13 点审核清单（全部通过）

- [x] frontmatter 使用 `metadata.clawdbot`（非 `openclaw`）
- [x] `requires.env` 列出所有需要的环境变量 → `["CLIANY_ANTHROPIC_API_KEY"]`
- [x] `files` 字段声明脚本存在 → `["scripts/*"]`
- [x] `homepage` 指向 GitHub 仓库 → `https://github.com/pearjelly/cliany.site`
- [x] Shell 脚本无用户输入注入风险（install.sh 仅做文件复制）
- [x] 脚本有 SECURITY MANIFEST 头部
- [x] 脚本有 `set -euo pipefail`
- [x] SKILL.md 包含 External Endpoints 章节
- [x] SKILL.md 包含 Security & Privacy 章节
- [x] 包含 Trust Statement
- [x] 包含 Model Invocation Note
- [x] 无夸大功能声明
- [x] 包内仅含 SKILL.md、README.md、scripts/（+ clawhub.json 补充元数据）

## 发布到 SkillsMP (skillsmp.com)

SkillsMP 从 GitHub 公开仓库自动发现根目录 SKILL.md。

### 前置条件

1. GitHub 仓库 `pearjelly/cliany.site` 设为公开
2. 根目录有 SKILL.md（已有，内容已更新）
3. 仓库获得 2+ stars（SkillsMP 最低收录门槛）

### 加速索引

访问 https://skillsmp.com 搜索 `cliany-site` 验证。
如未收录，可手动提交仓库 URL：`https://github.com/pearjelly/cliany.site`

## 本地安装验证

```bash
# 一键安装到所有检测到的 AI 工具
bash skills/cliany-site/scripts/install.sh

# 验证 OpenCode 加载
# 在 OpenCode 会话中输入：
# /skill cliany-site
```

## 版本更新流程

1. 修改三个文件的版本号：
   - `skills/cliany-site/SKILL.md` → frontmatter 无 version 字段，由 clawhub publish --version 指定
   - `skills/cliany-site/clawhub.json` → `version` 字段
   - `SKILL.md`（根）→ `metadata.version`
   - `.opencode/skills/cliany-site/SKILL.md` → `metadata.version`
2. 重新发布：
   ```bash
   clawhub publish ./skills/cliany-site \
     --slug "cliany-site" \
     --version "0.1.2" \
     --changelog "描述变更内容" \
     --tags "latest"
   ```
3. SkillsMP 会在下次爬虫同步时自动更新

## 批量同步（多 skill 场景）

```bash
# 扫描本地所有 skill 并同步到 ClawHub
clawhub sync --all --bump patch --changelog "Batch update" --tags "latest"

# 预览不实际上传
clawhub sync --all --dry-run
```
