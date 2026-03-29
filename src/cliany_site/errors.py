# ---------------------------------------------------------------------------
# 异常层级体系
# ---------------------------------------------------------------------------


class ClanySiteError(Exception):
    """cliany-site 所有自定义异常的基类"""


class CdpError(ClanySiteError):
    """CDP 连接 / 浏览器通信相关异常"""


class SessionError(ClanySiteError):
    """Session 持久化（cookies / localStorage）相关异常"""


class ExplorerError(ClanySiteError):
    """工作流探索（LLM 交互 / AXTree 采集）相关异常"""


class CodegenError(ClanySiteError):
    """代码生成（adapter 输出 / 模板渲染）相关异常"""


class AdapterLoadError(ClanySiteError):
    """适配器动态加载 / 注册相关异常"""


class WorkflowError(ClanySiteError):
    """工作流编排相关异常"""


class SecurityError(ClanySiteError):
    """安全相关异常（加密/沙箱/审计）"""


# ---------------------------------------------------------------------------
# 错误码常量（用于 JSON 信封的 error.code 字段）
# ---------------------------------------------------------------------------

CDP_UNAVAILABLE = "CDP_UNAVAILABLE"
SESSION_EXPIRED = "SESSION_EXPIRED"
EXPLORE_FAILED = "EXPLORE_FAILED"
ADAPTER_NOT_FOUND = "ADAPTER_NOT_FOUND"
COMMAND_NOT_FOUND = "COMMAND_NOT_FOUND"
LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
EXECUTION_FAILED = "EXECUTION_FAILED"
CHROME_NOT_FOUND = "CHROME_NOT_FOUND"
WORKFLOW_PARSE_ERROR = "WORKFLOW_PARSE_ERROR"
WORKFLOW_FAILED = "WORKFLOW_FAILED"
BATCH_DATA_ERROR = "BATCH_DATA_ERROR"
BATCH_PARTIAL_FAILURE = "BATCH_PARTIAL_FAILURE"
SANDBOX_VIOLATION = "SANDBOX_VIOLATION"
AUDIT_FAILED = "AUDIT_FAILED"
SESSION_DECRYPT_FAILED = "SESSION_DECRYPT_FAILED"
PACK_FAILED = "PACK_FAILED"
INSTALL_FAILED = "INSTALL_FAILED"
BAD_REQUEST = "BAD_REQUEST"

ERROR_FIX_HINTS: dict[str, str] = {
    CDP_UNAVAILABLE: "请先启动 Chrome：google-chrome --remote-debugging-port=9222",
    SESSION_EXPIRED: "请重新运行 cliany-site login <url> 登录",
    EXPLORE_FAILED: "请检查 LLM API key 和 Chrome CDP 连接",
    ADAPTER_NOT_FOUND: "请先运行 cliany-site explore <url> <workflow> 生成 adapter",
    COMMAND_NOT_FOUND: "请运行 cliany-site list 查看可用命令",
    LLM_UNAVAILABLE: "请设置 CLIANY_LLM_PROVIDER、CLIANY_ANTHROPIC_API_KEY 或 CLIANY_OPENAI_API_KEY 环境变量",
    EXECUTION_FAILED: "请检查 Chrome CDP 连接和 adapter 状态",
    CHROME_NOT_FOUND: "请安装 Chrome 或确认 Chrome 可执行文件在 PATH 中",
    WORKFLOW_PARSE_ERROR: "请检查 YAML 工作流文件格式",
    WORKFLOW_FAILED: "请检查各步骤的 adapter 和命令配置",
    BATCH_DATA_ERROR: "请检查 CSV/JSON 数据文件格式",
    BATCH_PARTIAL_FAILURE: "请检查失败项的错误信息",
    SANDBOX_VIOLATION: "沙箱策略禁止此操作，请检查域名和动作类型",
    AUDIT_FAILED: "生成代码安全审计未通过，请检查 adapter 代码",
    SESSION_DECRYPT_FAILED: "Session 解密失败，请尝试重新登录",
    PACK_FAILED: "适配器打包失败，请检查 adapter 目录",
    INSTALL_FAILED: "适配器安装失败，请检查安装包格式",
    BAD_REQUEST: "请求参数无效，请检查请求体格式",
}
