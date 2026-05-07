# cliany-site v0.10.0 发布指南

**日期:** 2026-05-07
**范围:** metadata schema v3, DOM 剪枝, Lazy Loading, 修复缓存, 诊断模式

## 1. 摘要

cliany-site v0.10.0 是一个里程碑版本，引入了 **metadata schema v3** 的硬切换。该版本在探索效率（Token 减少 30-50%）、启动速度（提升 2-5 倍）和稳定性（智能诊断 + 修复缓存）方面实现了巨大飞跃。这些核心能力大量借鉴自 opencli 的先进实践，旨在将网页自动化 CLI 推向工业级标准。

## 2. BREAKING: Metadata Schema v3

由于底层数据结构的重大优化，v0.10.0 强制要求使用 `schema_version: 3`。

### 为什么升级到 v3？
- **支持复合控件提取**: 需要存储 `<select>` 等控件的选项元数据，旧版 schema 无法承载。
- **Lazy Loading 优化**: 精简了 `metadata.json` 的首屏加载字段，将重量级动作序列分离。
- **能力路由支持**: 增加了 `capabilities` 字段，记录 API endpoints 以实现 browser/api 双通道回放。

### 影响范围
所有 `schema_version` 为 2 或更低（或缺失）的旧版适配器将被标记为 `legacy` 并停止工作。

---

## 3. 核心新功能深度解析

### 3.1 DOM 剪枝 + 复合控件提取 (T02/T03)
在探索阶段，系统现在实施四层剪枝策略：
1. **深度剪枝**: 自动忽略对交互无关的极深层级。
2. **节点数控制**: 优先保留关键交互节点。
3. **屏蔽角色**: 剔除装饰性元素（如 SVG 背景）。
4. **压缩序列**: 对冗余结构进行折叠。

此外，自动提取 `<select>`、`<input type=date>` 和 `<input type=file>` 的选项元数据。
**效果**: LLM 接收到的 Token 数量减少 30%~50%，显著降低成本并提升复杂页面的规划成功率。

### 3.2 Lazy Adapter Registry (T05/T06)
旧版本在启动时会扫描并 import 所有适配器，当适配器数量较多时会导致明显的启动延迟。
- **`discover()`**: 现在仅读取轻量级的 `metadata.json`。
- **按需加载**: 只有在真正执行 `cliany-site <domain> <cmd>` 时，才会通过 `importlib` 加载对应的模块。
**效果**: CLI 启动速度从数百毫秒降低至数十毫秒，提升 2-5 倍。

### 3.3 Repair Cache 修复缓存 (T10)
当 `--heal` 机制成功修复一个元素定位后，结果将被缓存到 `repair-cache.json` 中。
- **LRU 策略**: 每域名支持 100 条缓存记录。
- **跳过 LLM**: 相同的故障模式再次发生时，直接命中缓存，无需调用 LLM 即可完成自愈。

### 3.4 诊断模式 (T20/T22/T23)
新版本引入了全局 `--diagnose` 标志。
```bash
cliany-site --diagnose --json <domain> <cmd>
```
当命令失败时，系统会自动收集当前页面状态（AXTree、Console 日志、Network 请求），发送给 LLM 进行深入诊断，并输出 `root_cause` 与 `suggested_fix`。生成的适配器模板已内置该 hook。

---

## 4. 迁移指南 (Migration)

### 使用 migrate 命令
我们提供了一键迁移工具：
```bash
# 预览迁移项
cliany-site migrate --dry-run

# 执行迁移
cliany-site migrate --json
```
该命令会自动扫描旧版适配器，补齐缺失字段，升级 schema 版本，并自动生成 `.bak` 备份文件。

---

## 5. 开发者新工具

### 5.1 离线 QA 模式
为了方便集成测试，我们引入了 `FakeChatModel`：
- 设置 `CLIANY_QA_OFFLINE=1` 进入离线模式。
- 通过 `CLIANY_QA_FAKE_LLM_RESPONSES` 指定预定义的 LLM 响应响应。

### 5.2 全局新标志
- `--force-browser`: 即使适配器支持 API 通道，也强制使用浏览器回放。
- `--diagnose`: 开启失败时的 LLM 自动诊断。

---

## 6. 常见问题 (FAQ)

**Q: 我的旧适配器报错 `SCHEMA_VERSION_MISMATCH` 怎么办？**
A: 请运行 `cliany-site migrate` 进行升级，或使用 `cliany-site explore` 重新生成。

**Q: 如何查看当前已加载适配器的 schema 版本？**
A: 使用 `cliany-site list --json` 可以查看每个适配器的元数据细节。

**Q: 诊断模式会产生额外费用吗？**
A: 是的，`--diagnose` 会触发一次额外的 LLM 调用。建议仅在排查顽固故障时开启。

---

## 7. 结语

---

## 8. 未来展望

随着 v0.10.0 的发布，cliany-site 已经具备了处理大规模复杂表单和动态页面的能力。在接下来的版本中，我们将重点探索：
1. **多模态视觉校验**: 结合截图进行更精准的元素验证。
2. **社区适配器广场**: 让用户能够更方便地分享和发现优秀的自动化脚本。
3. **更深度的 API 合成**: 自动从浏览器操作中推导出完整的 REST API 访问方式。

感谢所有开发者的反馈与支持！

