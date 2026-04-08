# adapter 命令级 `--resume` 设计

**日期：** 2026-04-07
**主题：** 为现有 checkpoint / 断点续执行能力补齐用户可达 CLI 闭环，并修正文档承诺

## 背景

当前仓库已经具备断点保存与恢复的底层能力：

- `src/cliany_site/checkpoint.py` 负责按 `domain + command_name` 读写断点
- `src/cliany_site/action_runtime.py` 已支持 `start_index` 参数，并在失败时保存断点
- 运行时日志会提示用户“可使用 `--resume` 继续执行”

但真实用户入口尚未闭环：

- 生成出来的 adapter 命令没有 `--resume`
- README 已宣称支持 `--resume`，但与真实 CLI 不一致

因此，本次设计的目标不是新增全新恢复机制，而是把已有能力补齐为可达产品面。

## 目标

1. 为生成的 adapter 命令增加 `--resume` 选项
2. 让 `--resume` 正确读取 checkpoint 并从中断位置继续执行
3. 在无断点或断点无效时给出清晰反馈
4. 修正 README，让文档承诺与实际命令一致

## 非目标

本次不做以下扩展：

- 不新增独立内置 `resume` 命令
- 不修改 checkpoint 存储格式
- 不引入多断点管理界面
- 不处理跨命令、跨 adapter 的通用恢复编排

## 方案选择

本次采用：**adapter 命令级 `--resume`**。

示例：

```bash
cliany-site github.com search --resume
```

选择理由：

- 与现有 checkpoint 键模型 `domain + command_name` 完全一致
- 与用户执行心智一致：恢复的是某个具体命令，而不是抽象恢复任务
- 改动范围最小，不需要新增一套命令面和解析逻辑

## 设计细节

### 1. CLI 入口

在代码生成模板中，为每个 adapter 命令新增：

```python
@click.option("--resume", is_flag=True, default=False, help="从最近断点继续执行")
```

该参数仅作用于生成的 adapter 命令，不作用于 `explore` 命令。

### 2. 恢复逻辑

执行流程如下：

1. 命令启动后，若未指定 `--resume`，保持当前行为不变
2. 若指定 `--resume`：
   - 读取 `checkpoint.py` 中 `DOMAIN + command_name` 的断点
   - 取 `completed_indices` 中最大值，加一后作为 `start_index`
   - 调用 `execute_action_steps(..., start_index=start_index)`
3. 若未找到断点，则返回明确错误响应，不静默退化为普通执行
4. 若断点存在但 `completed_indices` 为空，则从第 0 步开始执行，并在响应中说明断点存在但尚未完成任何步骤

### 3. 参数策略

checkpoint 当前会保存 `params`。本次不改变其结构，但恢复时采用如下规则：

- 若用户本次显式传入参数，则以本次参数为准
- 若用户本次未传参数，则沿用当前命令执行路径的默认参数组装方式
- 本次不做“自动回填历史参数到 CLI 参数解析”的增强，以避免引入额外复杂度

这意味着：`--resume` 负责恢复执行位置，不负责重建完整调用上下文。

### 4. 用户反馈

建议输出以下反馈语义：

- 成功恢复：提示“从第 N 步继续执行”
- 无断点：提示“未找到可恢复断点，请先执行一次失败流程”
- 断点无效：提示“断点数据损坏或不可用，请重新执行命令”

### 5. README 对齐

README 中的“断点续执行”示例改为与 adapter 命令一致，例如：

```bash
cliany-site github.com search --resume
```

避免继续暗示 `explore --resume` 或其他不存在的入口。

## 影响范围

### 代码文件

- `src/cliany_site/codegen/templates.py`
- `README.md`
- 可能涉及生成命令相关测试文件

### 测试

需要覆盖：

- 生成模板包含 `--resume`
- `--resume` 时能读取 checkpoint 并传递 `start_index`
- 无断点时给出清晰错误反馈
- README 示例与真实入口一致

## 风险与约束

### 1. 仅对新生成或重新生成的 adapter 生效

由于 `--resume` 入口来自代码生成模板，历史已经生成在用户目录下的 adapter 不会自动拥有新选项，除非重新 explore / merge / regenerate。

### 2. 历史参数不自动重建

checkpoint 虽保存 `params`，但本次不做参数自动重放，以避免与 Click 参数解析和命令签名耦合过深。

### 3. README 需说明边界

文档中应明确“`--resume` 用于 adapter 命令恢复”，而不是所有命令都支持。

## 验收标准

满足以下条件即视为完成：

1. 新生成的 adapter 命令帮助文本可见 `--resume`
2. 执行 `cliany-site <domain> <command> --resume` 时，能从 checkpoint 推导 `start_index`
3. 无断点时返回清晰错误，而不是静默完整重跑
4. README 示例与真实 CLI 行为一致
5. 对应测试通过
