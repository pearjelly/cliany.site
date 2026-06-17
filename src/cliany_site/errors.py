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


class LlmUnavailableError(ExplorerError):
    """LLM 上游服务不可用、限流或网关错误"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class CodegenError(ClanySiteError):
    """代码生成（adapter 输出 / 模板渲染）相关异常"""


class AdapterLoadError(ClanySiteError):
    """适配器动态加载 / 注册相关异常"""


class WorkflowError(ClanySiteError):
    """工作流编排相关异常"""


class SecurityError(ClanySiteError):
    """安全相关异常（加密/沙箱/审计）"""


class UnsafeArchiveError(ClanySiteError):
    """归档文件包含路径穿越或不安全链接条目"""


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
UNSAFE_ARCHIVE = "UNSAFE_ARCHIVE"
BINARY_DOWNLOAD_FAILED = "BINARY_DOWNLOAD_FAILED"
LOCK_TIMEOUT = "LOCK_TIMEOUT"

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
    UNSAFE_ARCHIVE: "归档文件包含路径穿越或不安全链接，拒绝解压",
    BINARY_DOWNLOAD_FAILED: "下载二进制失败，请检查网络连接或使用镜像源",
    LOCK_TIMEOUT: "文件锁等待超时，请稍后重试或检查是否有其他进程占用锁文件",
    "E_CDP_UNAVAILABLE": "请先启动 Chrome：chrome --remote-debugging-port=9222",
    "E_SESSION_EXPIRED": "请重新运行 cliany-site login <url> 登录",
    "E_SELECTOR_NOT_FOUND": "页面结构可能已更改，请尝试 cliany-site check <domain> --fix 修复",
    "E_PAGE_NOT_READY": "页面就绪超时；网络不稳或站点 SPA 渲染慢，可加大 --wait-timeout 或重试。",
    "E_PARSE_FAILED": "解析失败：页面结构可能已变更；尝试 --heal 或重新 explore 该域。",
    "E_EMPTY_RESULT": "命令期望返回非空列表，但提取结果为空；可能是登录态过期、过滤条件过严或选择器失配。",
    "E_LLM_DISABLED": "请设置 CLIANY_ANTHROPIC_API_KEY 或 CLIANY_OPENAI_API_KEY 环境变量",
    "E_LLM_UNAVAILABLE": (
        "LLM 上游服务暂不可用或限流；请稍后重试，或切换 CLIANY_LLM_PROVIDER / "
        "CLIANY_OPENAI_BASE_URL。"
    ),
    "E_LEGACY_ADAPTER": "请运行 cliany-site migrate --json 升级旧版 adapter",
    "E_VERIFY_STATIC": "请运行 cliany-site verify <domain> --json 查看详细验证失败原因",
    "E_VERIFY_SMOKE": "请先运行 cliany-site verify <domain> --json，查看静态校验结果后再重试",
    "E_HEAL_CAP_EXCEEDED": "已达到自动修复上限，请重新探索页面或手动修复选择器",
    "E_AGENT_MD_CONFLICT": "AGENT.md 与当前生成内容冲突，请重新生成或手动合并后再试",
    "E_REGISTRY_CONFLICT": "命令注册冲突，请检查是否存在同名 adapter 或重复命令",
    "E_INVALID_PARAM": "请检查命令参数格式，运行 cliany-site <cmd> --help 查看帮助",
    "E_TIMEOUT": "操作超时，请检查 Chrome 是否响应或网络连接",
    "E_CDP_DISCONNECTED": "Chrome 连接已断开，请重启 Chrome 后重试",
    "E_EVAL_DISABLED": "当前环境禁止执行评估脚本，请检查安全策略或运行模式",
    "E_EVAL_BLACKLIST": "检测到受限表达式或危险调用，请修改脚本后重试",
    "E_UNKNOWN": "发生未知错误，请使用 --debug 标志运行以获取详细信息",
    "E_QA_OFFLINE_MISSING_FAKE_LLM": "离线 QA 需要 fake LLM，请先配置测试替身或切换到在线模式",
    "E_DIAGNOSE": "请重新运行命令并加上 --diagnose --json 以查看根因",
    "E_UNSUPPORTED_PLATFORM": "当前平台不支持此功能，请查看 docs/ 了解兼容平台",
    "E_MISSING_CAPABILITY": "当前浏览器提供方缺少所需能力，请切换到 Chrome 或检查 provider 配置",
    "E_PROVIDER_NOT_FOUND": "未找到浏览器提供方，请检查 CLIANY_BROWSER_PROVIDER 设置",
    "E_PROVIDER_VERSION_TOO_OLD": "浏览器提供方版本过旧，请升级后重试",
    "E_BINARY_NOT_FOUND": "所需二进制文件未找到，请运行 cliany-site obscura install <version>",
    "E_STALE_PID": "检测到过期进程记录，请清理后重试或重新安装",
    "E_PORT_CONFLICT": "端口被占用，请关闭占用进程或更换端口",
    "E_DOWNLOAD_FAILED": "下载失败，请检查网络连接或使用镜像源",
    "E_VERSION_MISMATCH": "版本不匹配，请升级 cliany-site 与相关组件到兼容版本",
}
