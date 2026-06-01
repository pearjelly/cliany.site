# PACKAGE GUIDE

## OVERVIEW
`src/cliany_site/` holds the runtime package: root CLI, built-in commands, browser/CDP integration, explorer, codegen, adapter loading, and session persistence.

## STRUCTURE
```text
src/cliany_site/
├── cli.py               # root Click group; global error rendering; adapter registration
├── commands/            # built-in user-facing commands
├── browser/             # CDP connection + AXTree capture
├── explorer/            # LLM planning loop and prompt/data contracts
├── codegen/             # generated adapter emitter
├── loader.py            # discovers and loads `~/.cliany-site/adapters/*/commands.py`
├── session.py           # cookies/session persistence in home dir
├── action_runtime.py    # replay engine for planned actions
└── response.py          # shared success/error envelope printing
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add/change root CLI behavior | `cli.py` | `SafeGroup`, root options, command registration |
| Add built-in command | `commands/` | follow existing Click + `asyncio.run` boundary |
| Change response envelope | `response.py`, `errors.py` | impacts all commands and generated adapters |
| Change adapter discovery/runtime mounting | `loader.py` | reads from home directory, not repo |
| Persist or inspect login state | `session.py` | safe-domain file naming |
| Change replay semantics | `action_runtime.py` | handles click/type/select/navigate/submit |

## CONVENTIONS
- Keep command entrypoints thin; push real work into helpers or async inner functions.
- Preserve root `json_mode` inheritance via `ctx.find_root().obj`.
- Use `Path.home() / ".cliany-site"` for runtime artifacts; do not introduce repo-local state.
- Prefer absolute imports from `cliany_site.*`.
- User-facing copy stays Chinese unless an existing file is clearly English-only.

## ANTI-PATTERNS
- Do not bypass `print_response` / shared error helpers for command output.
- Do not register generated adapters manually in source; `register_adapters()` owns that path.
- Do not hardcode runtime artifacts into the repo tree.
- Do not mix exploratory logic into command modules when a lower-level package already owns it.

## LOCAL CHILD GUIDES
- `explorer/AGENTS.md` — prompt contract, exploration loop, result models.
- `codegen/AGENTS.md` — generated adapter format and metadata rules.

## AUTONOMOUS IMPROVEMENT GUARDRAILS（包级）

> 同步自根 `AGENTS.md` 守则，聚焦 `src/cliany_site/` 包内代码层约束：

- **语义化优先**：禁止引入 CSS 选择器兜底；所有元素定位必须走 `selector_map` 的 role/name 语义匹配。
- **codegen 安全**：修改 `codegen/generator.py` 须保持 type hints 完整，兼容 Python 3.11+；禁止生成 `eval`/`exec`/`os.system`。
- **不编辑生成代码**：标记 `# 自动生成 — DO NOT EDIT` 的 adapter 文件绝对禁止修改。
- **测试隔离**：包内测试必须使用 `tmp_home` fixture，禁止在 repo 内写 `~/.cliany-site/` 运行时状态。
- **不重写现有模块**：只扩展/新增；禁止重写 `testing/snapshot.py`、`browser/cdp.py` 等核心模块。
- **确定性回归**：新增的 LLM 相关测试必须设置 `CLIANY_QA_OFFLINE=1`，走 `FakeChatModel` 而非真实 API。
