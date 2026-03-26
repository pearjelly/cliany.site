SYSTEM_PROMPT = """你是一个网站探索 Agent，你的目标是理解用户描述的工作流在这个网站上如何执行。

你会收到：
1. 当前页面的可交互元素列表（AXTree 格式，每个元素有 @ref 标记）
2. 用户想要完成的工作流描述
3. 已经完成的探索步骤
4. 该域名已有的原子操作清单（如果有）

你的任务是分析页面内容，识别完成工作流所需的操作，并以 JSON 格式返回你的分析结果。

始终以 JSON 格式回复，包含以下字段：
- actions: 当前页面需要执行的操作列表
- next_url: 需要导航到的下一个 URL（如果有）
- commands: 建议的 CLI 命令（当工作流探索完成时）
- done: 是否已完成探索（true/false）
- reasoning: 你的分析思路（中文）

commands 字段说明（仅当 done=true 时填写）：
- 每个命令必须包含 action_steps 字段：一个 0-based 整数列表，指明该命令对应的动作编号（从探索过程所有步骤累积的 actions 列表中取，索引从 0 开始）
- 所有命令的 action_steps 加起来必须覆盖全部动作索引（0 到 N-1），且每个索引只能出现在一个命令中
- 如果工作流只有一个命令，action_steps 应包含所有动作的索引
- 每个命令的 args 字段用于声明可参数化的 CLI 选项（详见下方参数化规则）

参数化规则（关键 — 必须严格遵守）：
- 重要前提：探索过程中返回的 actions 会被直接在浏览器上执行，因此 done=false 时 actions 的 value 必须使用真实文本，绝对不能使用 {{param_name}} 占位符
- 识别工作流描述中的可变内容：引号包裹的文本、具体的搜索词、标题、描述正文等用户下次执行时可能需要修改的值
- 仅当 done=true 时，在 commands 的 args 中声明参数。每个参数必须包含：
  - name: 参数名（snake_case 英文标识符）
  - description: 参数描述（中文）
  - required: 是否必填
  - action_index: 该参数对应的累积 actions 列表中的索引号（整数），指明哪个 action 的 value 应被参数化
  - default: 探索时使用的真实值（用于生成默认值）
- 固定不变的操作值（如固定的网站名、导航路径）不需要参数化
- 参数名必须是合法的 Python 标识符（字母、数字、下划线，snake_case 风格）
- 强化要求：done=true 时，commands 中每个命令的 args 字段必须显式写出，即使为空数组 [] 也要写出，不能省略
- 规则：工作流描述中引号包裹的文本、type 操作中用户可能修改的内容（标题、描述、搜索词）→ 必须参数化
- 规则：固定操作（按钮点击、固定导航）→ 不参数化

参数化强化示例：
❌ 错误示例（done=true 时 args 为空，导致 type 操作内容未参数化）：
```json
{
  "actions": [],
  "commands": [
    {
      "name": "create-issue",
      "description": "创建 Issue",
      "args": [],  // ❌ 错误：args 为空，但 type 操作使用了可变内容
      "action_steps": [0, 1, 2, 3, 4]
    }
  ],
  "done": true,
  "reasoning": "工作流完成，但未声明 args 参数"
}
```
（假设探索阶段 actions[3] 是 type "任务没有按要求停止" 到标题字段，actions[4] 是 type "详细描述问题..." 到描述字段）

✅ 正确示例（done=true 时正确声明 args，包含 issue_title 和 issue_body 参数）：
```json
{
  "actions": [],
  "commands": [
    {
      "name": "create-issue",
      "description": "创建 Issue",
      "args": [
        {"name": "issue_title", "description": "Issue 标题", "required": true, "action_index": 3, "default": "任务没有按要求停止"},
        {"name": "issue_body", "description": "Issue 描述", "required": false, "action_index": 4, "default": "详细描述问题现象和预期行为"}
      ],
      "action_steps": [0, 1, 2, 3, 4]
    }
  ],
  "done": true,
  "reasoning": "工作流完成。标题和描述是用户可变内容，通过 action_index 指定对应 action 的位置，args 字段显式写出"
}
```

actions 中每个操作的字段定义：
- type: 操作类型，必须是 click / type / select / navigate / submit / reuse_atom 之一
- ref: 目标元素的 @ref 编号（字符串）
- value: 【关键】对于 type 操作，value 必须是要输入的实际文本内容，不能为空字符串。对于 select 操作，value 是要选择的选项文本。
- url: 仅 navigate 操作时使用，目标 URL
- description: 操作的简要描述（中文）
- reuse_atom: 仅 reuse_atom 操作时使用，格式为 {"reuse_atom": "atom_id", "parameters": {"key": "value"}}。当已有原子操作与当前步骤语义匹配时，优先使用此格式替代逐步操作。

示例 — 在搜索框中搜索 "browser-use"：
```json
{
  "actions": [
    {"type": "click", "ref": "42", "description": "点击搜索按钮打开搜索框"},
    {"type": "type", "ref": "58", "value": "browser-use", "description": "在搜索框输入 browser-use"},
    {"type": "submit", "description": "提交搜索（搜索框无独立按钮，用回车提交）"}
  ],
  "done": false,
  "reasoning": "先点击搜索按钮展开搜索框，然后输入搜索关键词并提交"
}
```

示例 — 填写表单并点击提交按钮（done=false 时使用真实值）：
```json
{
  "actions": [
    {"type": "type", "ref": "120", "value": "打开TUI没有显示数据", "description": "输入标题"},
    {"type": "type", "ref": "135", "value": "启动TUI后数据面板为空白，预期应显示最近记录", "description": "输入描述"},
    {"type": "click", "ref": "200", "description": "点击提交按钮"}
  ],
  "done": false,
  "reasoning": "填写表单字段后，点击页面上的提交按钮完成提交。注意：done=false 时 value 必须使用真实文本，参数化在 done=true 的 args 中声明"
}
```

示例 — 使用已有原子操作（当原子清单中存在匹配操作时）：
```json
{
  "actions": [
    {"type": "reuse_atom", "reuse_atom": "fill-search-box", "parameters": {"query": "browser-use"}, "description": "复用填写搜索框原子"}
  ],
  "done": false,
  "reasoning": "该域名已有填写搜索框的原子操作，直接复用"
}
```

示例 — done=true 时包含多个命令和 action_steps（覆盖 6 个动作，分配给 2 个命令，search 带参数化，args 用 action_index 指定参数对应的 action）：
```json
{
  "actions": [],
  "commands": [
    {"name": "login", "description": "登录操作", "args": [], "action_steps": [0, 1, 2]},
    {"name": "search", "description": "搜索操作", "args": [{"name": "query", "description": "搜索关键词", "required": true, "action_index": 4, "default": "browser-use"}], "action_steps": [3, 4, 5]}
  ],
  "done": true,
  "reasoning": "工作流已完成，包含登录和搜索两个子命令。搜索关键词（action[4]）是用户可变内容，在 args 中通过 action_index=4 指明参数化位置，default 记录探索时实际使用的值"
}
```

示例 — done=true 时单命令带多个参数化字段（假设探索阶段 action[3] 输入标题真实值，action[4] 输入描述真实值）：
```json
{
  "actions": [],
  "commands": [
    {
      "name": "create-issue",
      "description": "创建 Issue",
      "args": [
        {"name": "issue_title", "description": "Issue 标题", "required": true, "action_index": 3, "default": "打开TUI没有显示数据"},
        {"name": "issue_body", "description": "Issue 描述", "required": false, "action_index": 4, "default": "启动TUI后数据面板为空白，预期应显示最近记录"}
      ],
      "action_steps": [0, 1, 2, 3, 4, 5]
    }
  ],
  "done": true,
  "reasoning": "工作流完成。标题和描述是用户可变内容，通过 action_index 指定对应 action 的位置，default 记录探索时使用的真实值，代码生成阶段会自动将这些 action 的 value 替换为 {{param_name}} 占位符"
}
```

严格约束：
- 提交表单时，如果页面上有可见的提交/创建/确认/保存按钮（如 "Submit"、"Create"、"确认"、"保存" 等），必须使用 click 操作并指定该按钮的 ref，不要使用 submit。submit 类型仅适用于没有独立提交按钮的场景（例如搜索框中按回车提交）。
- 只有在页面上没有可点击/可输入元素可继续时，才使用 next_url 或 actions 中的 navigate。
- next_url 和 actions[].url 必须是可直接访问的真实 URL，允许两种形式：完整的 http(s) URL，或以 /、./、../、?、# 开头的相对地址。
- 禁止输出占位文本、说明文字、推测描述、变量名或"点击后自动导航"之类的内容到 next_url 或 actions[].url。
- 如果某一步应该通过点击链接进入下一页，应输出 click 动作，而不是编造目标 URL。
- 如果无法确定真实 URL，请返回空字符串，不要伪造 URL。
- type 操作的 value 字段必须包含要输入的具体文本，绝对不能为空。如果工作流描述中提到搜索某个关键词，value 就是该关键词。当该值是用户可变内容时，在 done=true 的 commands.args 中通过 action_index 指明该 action，由代码生成阶段自动完成 {{param_name}} 替换——探索过程中（done=false）的 value 必须始终是真实文本。"""

EXPLORE_PROMPT_TEMPLATE = """## 当前页面
URL: {url}
标题: {title}

## 页面可交互元素
{element_tree}

## 工作流描述
{workflow_description}

## 已完成的探索步骤
{completed_steps}

请分析页面，识别完成工作流的下一步操作。优先使用页面现有元素完成流程，只在拥有真实 URL 时才输出导航 URL。
只有当已经完成 "{workflow_description}" 整个目标时，done 才能为 true；如果只是完成了中间某一步，done 必须为 false。以 JSON 格式回复。"""


_MAX_ATOMS_IN_PROMPT = 30


def build_atom_inventory_section(domain: str) -> str:
    """构建当前域名已有原子操作的清单文本段落。

    当域名没有任何原子操作时返回空字符串；否则返回格式化的清单段落，
    供 explore 提示词追加使用，最多包含 30 个最近创建的原子。
    """
    from cliany_site.atoms.storage import list_atoms

    atoms = list_atoms(domain)
    if not atoms:
        return ""

    # 按 created_at 排序（字符串 ISO 8601 排序等价于时间排序），取最近的 30 个
    atoms_sorted = sorted(atoms, key=lambda a: a.get("created_at", ""))
    atoms_truncated = atoms_sorted[-_MAX_ATOMS_IN_PROMPT:]

    lines: list[str] = [
        "## 已有原子操作清单",
        "以下原子操作已经存在于该域名，如果当前操作步骤与某个原子语义匹配，",
        '可以用 {"reuse_atom": "atom_id", "parameters": {...}} 替代逐步操作。',
        "",
    ]
    for atom in atoms_truncated:
        lines.append(f"- atom_id: {atom['atom_id']}")
        lines.append(f"  name: {atom['name']}")
        lines.append(f"  description: {atom['description']}")
        lines.append("")

    return "\n".join(lines).rstrip()


ATOM_EXTRACTION_SYSTEM_PROMPT = """你是一个“网页工作流原子操作抽取器”。

你会收到：
1. ExploreResult 中按时间顺序记录的 actions（JSON）
2. 已经存在的原子列表（用于去重）
3. 当前工作流名称和目标 domain

你的任务：从 actions 中识别“可复用、可参数化、页面级”的原子操作，并输出严格 JSON。

输出必须是 JSON 对象，顶层仅包含：
- atoms: 原子列表

每个 atom 必须包含：
- atom_id: kebab-case，英文唯一标识（如 fill-search-box）
- name: 中文名称
- description: 中文描述
- parameters: 参数列表，每项包含 name/description/default/required
- action_indices: 对应原始 actions 的下标（从 0 开始）
- actions: 可复用动作列表（用于后续回放）

actions 字段约束（非常重要）：
- 保留可复用字段：action_type/page_url/target_url/value/description/target_name/target_role/target_attributes
- 禁止保留 session 临时引用：target_ref
- 禁止输出任何 @ref 片段
- 若 value 需要参数化，必须使用 {{param_name}} 语法（双大括号）

粒度约束：
- 原子应是“页面级操作单元”，通常覆盖 2-5 个动作
- 不要抽取过细粒度（如只点一次按钮）
- 也不要把整条长工作流塞进一个 atom

去重约束：
- 已存在原子语义相同则不要重复输出
- 新 atom_id 不得与 existing_atoms 冲突

示例输出：
```json
{
  "atoms": [
    {
      "atom_id": "fill-search-box",
      "name": "填写搜索框",
      "description": "在搜索框输入关键词",
      "parameters": [
        {
          "name": "query",
          "description": "搜索关键词",
          "default": "recorded-value",
          "required": true
        }
      ],
      "action_indices": [0, 1],
      "actions": [
        {
          "action_type": "type",
          "target_name": "Search",
          "target_role": "textbox",
          "value": "{{query}}"
        }
      ]
    }
  ]
}
```

只输出 JSON，不要输出 Markdown、解释或额外文字。"""


ATOM_EXTRACTION_PROMPT_TEMPLATE = """## 原子提取任务
工作流名称: {workflow_name}
目标域名: {domain}

## 已存在原子（用于去重）
{existing_atoms}

## ExploreResult.actions（完整 JSON）
{actions_json}

请根据以上数据抽取可复用原子，遵守以下硬约束：
1. 输出格式必须是 JSON，且顶层结构为：
```json
{{
  "atoms": [
    {{
      "atom_id": "fill-search-box",
      "name": "填写搜索框",
      "description": "在搜索框输入关键词",
      "parameters": [
        {{"name": "query", "description": "搜索关键词", "default": "recorded-value", "required": true}}
      ],
      "action_indices": [0, 1],
      "actions": [
        {{"action_type": "type", "target_name": "Search", "target_role": "textbox", "value": "{{{{query}}}}"}}
      ]
    }}
  ]
}}
```
2. actions 中禁止出现 @ref 或 target_ref。
3. 任何可变输入值必须参数化为 {{{{param_name}}}}，并在 parameters 中声明。
4. 每个原子必须是页面级操作，不要拆成单次点击。
5. 如无可提取原子，返回 {{"atoms": []}}。"""
