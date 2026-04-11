# CLI 执行主路径 sandbox 闭环 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 root `--sandbox` 对生成 adapter 命令的 CLI 执行路径真实生效，并用 README 与测试固定该行为。

**Architecture:** 在代码生成模板中读取 root context 的 `sandbox` 标志，为当前 `DOMAIN` 构造 `SandboxPolicy`，对汇总后的 `action_steps` 先执行 `validate_action_steps(...)`，发现违规立即返回错误响应，否则再进入 `execute_action_steps(...)`。README 只声明当前覆盖 CLI adapter 执行路径。

**Tech Stack:** Python 3.11、Click、pytest、现有 codegen 模板、sandbox 策略模块

---

## 文件结构

- Modify: `src/cliany_site/codegen/templates.py`
  - 读取 root sandbox 标志
  - 组装 `SandboxPolicy.from_domain(DOMAIN)`
  - 执行前调用 `validate_action_steps(...)`
  - 违规时返回标准错误响应
- Modify: `README.md`
  - 补充 sandbox 当前覆盖范围说明
- Modify: `tests/test_codegen.py`
  - 校验模板输出包含 sandbox 读取与校验逻辑
- Modify: `tests/test_security.py` or `tests/test_cli_integration.py`
  - 如有必要，补充更贴近主路径行为的断言

## Chunk 1: 模板接线

### Task 1: 让生成命令读取 root `sandbox`

**Files:**
- Modify: `src/cliany_site/codegen/templates.py`
- Test: `tests/test_codegen.py`

- [ ] **Step 1: 写失败测试，断言生成命令会读取 root `sandbox`**

```python
def test_generated_command_reads_root_sandbox_flag():
    code = render_command_block(command, all_actions, 0)
    assert 'root_ctx = ctx.find_root()' in code
    assert 'sandbox_enabled = root_obj.get("sandbox", False)' in code
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `uv run pytest tests/test_codegen.py -k sandbox -v`
Expected: FAIL

- [ ] **Step 3: 在模板中接入 root sandbox 读取逻辑**

```python
root_ctx = ctx.find_root()
root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
sandbox_enabled = root_obj.get("sandbox", False)
```

- [ ] **Step 4: 重跑测试确认通过**

Run: `uv run pytest tests/test_codegen.py -k sandbox -v`
Expected: PASS

### Task 2: 在执行前做 sandbox 预检

**Files:**
- Modify: `src/cliany_site/codegen/templates.py`
- Test: `tests/test_codegen.py`

- [ ] **Step 1: 写失败测试，断言生成命令会调用 `SandboxPolicy.from_domain` 和 `validate_action_steps`**

```python
def test_generated_command_validates_actions_when_sandbox_enabled():
    code = render_command_block(command, all_actions, 0)
    assert 'from cliany_site.sandbox import SandboxPolicy, validate_action_steps' in code
    assert 'policy = SandboxPolicy.from_domain(DOMAIN)' in code
    assert 'violations = validate_action_steps(action_steps, policy)' in code
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_codegen.py -k sandbox -v`
Expected: FAIL

- [ ] **Step 3: 实现 sandbox 预检逻辑**

```python
if sandbox_enabled:
    policy = SandboxPolicy.from_domain(DOMAIN)
    violations = validate_action_steps(action_steps, policy)
    if violations:
        first = violations[0]
        return error_response(...)
```

- [ ] **Step 4: 重跑测试确认通过**

Run: `uv run pytest tests/test_codegen.py -k sandbox -v`
Expected: PASS

## Chunk 2: 错误反馈与文档对齐

### Task 3: 固定违规错误语义

**Files:**
- Modify: `src/cliany_site/codegen/templates.py`
- Test: `tests/test_codegen.py`

- [ ] **Step 1: 写失败测试，断言违规时返回明确错误提示**

```python
def test_generated_command_returns_sandbox_error_message():
    code = render_command_block(command, all_actions, 0)
    assert '沙箱阻止执行' in code
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_codegen.py -k sandbox -v`
Expected: FAIL

- [ ] **Step 3: 实现统一错误提示**

```python
return error_response(
    EXECUTION_FAILED,
    f"沙箱阻止执行: 第 {first['index']} 步 {first['action']}",
    first["error"],
)
```

- [ ] **Step 4: 运行相关测试确认通过**

Run: `uv run pytest tests/test_codegen.py -k sandbox -v`
Expected: PASS

### Task 4: 更新 README 的 sandbox 边界说明

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 查找 README 中 `--sandbox` 描述**

Run: `grep -n "sandbox" README.md`
Expected: 命中特性说明区

- [ ] **Step 2: 补充“当前优先作用于 CLI adapter 执行路径”的说明**

- [ ] **Step 3: 确认 README 不再暗示 SDK / API 也已同步闭环**

Run: `grep -n "sandbox" README.md`
Expected: 文案边界清晰

## Chunk 3: 回归验证

### Task 5: 运行最小回归集

**Files:**
- Test: `tests/test_codegen.py`
- Test: `tests/test_security.py`
- Test: `tests/test_cli_integration.py`

- [ ] **Step 1: 运行 sandbox 与模板相关测试**

Run: `uv run pytest tests/test_codegen.py tests/test_security.py -v`
Expected: PASS

- [ ] **Step 2: 运行 CLI 集成测试，确认 root 参数解析未被破坏**

Run: `uv run pytest tests/test_cli_integration.py -v`
Expected: PASS

- [ ] **Step 3: 编译检查 Python 源码**

Run: `uv run python -m compileall src/cliany_site`
Expected: PASS

- [ ] **Step 4: 提交本轮闭环（如用户要求）**

```bash
git add README.md src/cliany_site/codegen/templates.py tests/test_codegen.py tests/test_security.py
git commit -m "feat(CLI): 接通 sandbox 执行预检"
```
