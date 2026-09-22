# Jev 意图定位（实验性，Unreleased）

当用户知道要做什么、但不知道控件的准确名称时，用自然语言寻找当前页面中的元素。本入口只返回 ref、名称、角色、概率、置信度与模型版本，不点击、不输入、不生成 URL 或 CSS，也不替代探索模型。

配置本地环境变量 `TYPESAFE_API_KEY` 后：

```bash
cliany-site --cdp-url http://localhost:9222 browser find \
  --by intent --value "输入订单号的搜索框" --allow-remote \
  --min-confidence 0.8 --json
```

尚未发布到 PyPI v0.16.356，需使用包含本修改的源码。`CLIANY_JEV_MODEL` 可指定模型，默认 `jev-latest`。使用浏览器当前页面，不恢复登录 session；页面刷新后 ref 可能失效，应重新定位。

## 设计依据

[官方介绍](https://typesafe.ai/blog/introducing-system-one-models-and-jev)将 Jev 定位为结构化决策模型，不提供任意字符串生成。本项目采用 [Choice](https://docs.typesafe.ai/primitives/choice)：选项由当前 AXTree 生成，并包含“无法确定”。通过[官方 HTTP API](https://docs.typesafe.ai/api)调用，无需额外模型 SDK。

类型安全不等于语义永远正确，官方性能数字也不是本项目实测。[confidence 文档](https://docs.typesafe.ai/confidence)说明 confidence 来自概率分布，不等同于所选项概率；本入口同时检查两者。

## 数据与保护边界

- 默认不联网，必须显式传入 `--allow-remote`；普通 text/role/attr 查找不变。
- 外发用户意图、元素名称与角色。名称截为 512 字符、角色 80 字符，意图上限 4096 字符。不发送 Cookie、输入值、属性、URL、截图或整页文本。名称和意图仍可能包含敏感信息，不应在禁止外发的页面使用。
- 最多 254 个元素加一个 abstain 选项；超限停止，不静默截断。`--limit` 不裁剪意图候选，意图模式最多返回一个目标。
- 每次最多一次请求，5 秒超时，不自动重试、不跟随重定向；不输出认证信息或错误响应正文。
- 检查类型、候选集合、有限概率、归一化、最大概率项及置信度。低于门槛、并列、none、同名同角色多个候选均失败。0.8 是初始策略，尚未在本项目数据集上校准。
- `CLIANY_QA_OFFLINE=1` 禁止真实调用，即使配置了密钥也一样。
- 返回目标只是建议，不构成操作授权；不接入自动点击、自动修复或写入审批。

## 验证状态

2026-09-22：21 项 Jev 定向测试、2921 项完整离线回归通过，124 个源文件通过类型检查。

离线协议测试覆盖未授权外发、密钥缺失、HTTP 错误、候选越界、NaN、非归一化概率、置信度不足与同名歧义。真实 Chromium 测试使用实际 AXTree 和模拟 HTTP 响应，验证候选映射及页面无副作用；它不是 Jev 能力评测。

当前环境没有 TypeSafe 密钥，尚未调用真实 Jev。取得 early-access 访问后，以公开或合成页面建立标注集，分别测量准确率、拒绝率、错误接受率、p50/p95 延迟与 token 使用，并对比确定性名称匹配。通过门槛前保持只读建议模式，不宣传提速倍数。
