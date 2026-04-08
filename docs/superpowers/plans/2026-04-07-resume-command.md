# adapter 命令级 --resume Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为生成的 adapter 命令补齐 `--resume` 用户入口，利用现有 checkpoint 恢复执行位置，并同步修正 README 与测试。

**Architecture:** 在代码生成模板层为 adapter 命令增加 `--resume` 选项，并在命令运行时通过 `checkpoint.py` 读取 `domain + command_name` 对应断点，计算 `start_index` 后传给 `execute_action_steps(...)`。README 只描述真实存在的 adapter 级恢复入口，测试覆盖模板生成、恢复分支和无断点提示。

**Tech Stack:** Python 3.11、Click、pytest、现有 codegen 模板系统、checkpoint/action runtime

---

## 文件结构

- Modify: `src/cliany_site/codegen/templates.py`
  - 为生成命令添加 `--resume`
  - 在命令执行前读取 checkpoint 并推导 `start_index`
  - 在无断点时返回清晰错误响应
- Modify: `README.md`
  - 将断点恢复示例改为真实 adapter 命令入口
- Modify: `tests/test_codegen.py`
  - 校验生成模板输出包含 `--resume`
- Modify: `tests/test_sdk.py` or `tests/test_cross_module.py`
  - 如有必要，补跨模块恢复逻辑测试思路
- Modify: `tests/test_checkpoint.py` or `tests/test_cli_integration.py`
  - 增加恢复分支和无断点提示测试

## Chunk 1: 模板入口与恢复逻辑

### Task 1: 为生成命令增加 `--resume` 选项

**Files:**
- Modify: `src/cliany_site/codegen/templates.py`
- Test: `tests/test_codegen.py`

- [ ] **Step 1: 写一个失败测试，断言生成命令包含 `--resume` 选项**

```python
def test_generated_command_includes_resume_option():
    code = render_command_block(command, all_actions, 0)
    assert '@click.option("--resume"' in code
```

- [ ] **Step 2: 运行单测确认当前失败**

Run: `pytest tests/test_codegen.py -k resume -v`
Expected: FAIL，提示生成模板中没有 `--resume`

- [ ] **Step 3: 在模板中增加 `--resume` Click 选项与函数参数**

```python
@click.option("--resume", is_flag=True, default=False, help="从最近断点继续执行")
def command(..., resume: bool, ...):
```

- [ ] **Step 4: 再次运行单测确认模板输出通过**

Run: `pytest tests/test_codegen.py -k resume -v`
Expected: PASS

- [ ] **Step 5: 提交这一小步（如本轮需要提交）**

```bash
git add src/cliany_site/codegen/templates.py tests/test_codegen.py
git commit -m "为生成命令添加 resume 入口"
```

### Task 2: 通过 checkpoint 推导 `start_index`

**Files:**
- Modify: `src/cliany_site/codegen/templates.py`
- Test: `tests/test_checkpoint.py` or `tests/test_cross_module.py`

- [ ] **Step 1: 写一个失败测试，断言 `--resume` 时会读取 checkpoint 并传递 `start_index`**

```python
def test_resume_uses_checkpoint_start_index():
    checkpoint = {"completed_indices": [0, 1, 2]}
    # mock load_checkpoint -> checkpoint
    # mock execute_action_steps and assert start_index == 3
```

- [ ] **Step 2: 运行该测试确认失败**

Run: `pytest tests/test_checkpoint.py -k resume -v`
Expected: FAIL，提示未传递 `start_index`

- [ ] **Step 3: 在模板运行逻辑中加入 checkpoint 读取与 `start_index` 计算**

```python
start_index = 0
if resume:
    ckpt = load_checkpoint(DOMAIN, command_name)
    if not ckpt:
        return error_response(...)
    completed = ckpt.get("completed_indices", [])
    start_index = max(completed) + 1 if completed else 0

await execute_action_steps(..., start_index=start_index)
```

- [ ] **Step 4: 运行测试确认恢复逻辑通过**

Run: `pytest tests/test_checkpoint.py -k resume -v`
Expected: PASS

- [ ] **Step 5: 再运行相关模板/执行链路测试，避免生成命令被破坏**

Run: `pytest tests/test_codegen.py tests/test_checkpoint.py tests/test_cross_module.py -v`
Expected: PASS

## Chunk 2: 错误反馈与文档对齐

### Task 3: 无断点时返回清晰错误

**Files:**
- Modify: `src/cliany_site/codegen/templates.py`
- Test: `tests/test_checkpoint.py` or `tests/test_cli_integration.py`

- [ ] **Step 1: 写一个失败测试，断言无 checkpoint 时 `--resume` 返回明确错误**

```python
def test_resume_without_checkpoint_returns_actionable_error():
    result = invoke_generated_command(["--resume"])
    assert result["success"] is False
    assert "未找到可恢复断点" in result["error"]["message"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_checkpoint.py -k "no checkpoint or resume" -v`
Expected: FAIL

- [ ] **Step 3: 实现无断点错误响应**

```python
return error_response(
    EXECUTION_FAILED,
    "未找到可恢复断点",
    "请先执行一次失败流程后再使用 --resume",
)
```

- [ ] **Step 4: 运行相关测试确认通过**

Run: `pytest tests/test_checkpoint.py -k resume -v`
Expected: PASS

### Task 4: 修正 README 断点恢复示例

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 查找 README 中所有 `--resume` 与断点续执行描述**

Run: `grep -n "resume\|断点续执行" README.md`
Expected: 找到开发体验和示例区域

- [ ] **Step 2: 将文案改为 adapter 命令级恢复示例**

```bash
cliany-site github.com search --resume
```

- [ ] **Step 3: 确认 README 不再暗示 `explore --resume` 或不存在的入口**

Run: `grep -n "resume" README.md`
Expected: 只保留与 adapter 命令一致的描述

## Chunk 3: 回归验证

### Task 5: 跑最小必要测试集并确认无回归

**Files:**
- Test: `tests/test_codegen.py`
- Test: `tests/test_checkpoint.py`
- Test: `tests/test_cli_integration.py`
- Test: `README.md`

- [ ] **Step 1: 运行模板与 checkpoint 相关测试**

Run: `pytest tests/test_codegen.py tests/test_checkpoint.py -v`
Expected: PASS

- [ ] **Step 2: 运行 CLI 集成测试，确认帮助输出与参数解析未破坏**

Run: `pytest tests/test_cli_integration.py -v`
Expected: PASS

- [ ] **Step 3: 如有需要，运行更窄的回归测试覆盖生成命令相关路径**

Run: `pytest tests/test_cross_module.py tests/test_sdk.py -k "command or checkpoint or resume" -v`
Expected: PASS 或无匹配测试

- [ ] **Step 4: 手工检查 README 示例与设计一致**

Check:
- `README.md` 中 `--resume` 示例使用 adapter 命令
- `docs/superpowers/specs/2026-04-07-resume-command-design.md` 与实现行为一致

- [ ] **Step 5: 提交最终变更**

```bash
git add README.md src/cliany_site/codegen/templates.py tests/test_codegen.py tests/test_checkpoint.py tests/test_cli_integration.py
git commit -m "补齐 adapter 命令的 resume 恢复入口"
```
