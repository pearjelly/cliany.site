# src/cliany_site/binary/platforms.py
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformTarget:
    os: str           # 'darwin' | 'linux' | 'windows'
    arch: str         # 'x86_64' | 'arm64' | 'amd64'
    target_key: str   # 如 'darwin-arm64', 'linux-x86_64', 'windows-x86_64'
    exe_suffix: str   # '' 或 '.exe'
    archive_ext: str  # '.tar.gz' 或 '.zip'
    is_supported: bool


class UnsupportedPlatformError(Exception):
    target_key: str
    error_code: str

    def __init__(self, target_key: str):
        self.target_key = target_key
        self.error_code = "E_UNSUPPORTED_PLATFORM"
        super().__init__(f"Unsupported platform: {target_key}")


def normalize_platform(sys_platform: str, machine: str) -> PlatformTarget:
    """归一化平台信息，返回 PlatformTarget"""
    # 归一化 OS
    if sys_platform == "darwin":
        os_name = "darwin"
    elif sys_platform == "linux":
        os_name = "linux"
    elif sys_platform == "win32":
        os_name = "windows"
    else:
        raise UnsupportedPlatformError(f"{sys_platform}-{machine}")

    # 归一化架构
    if machine in ("x86_64", "AMD64"):
        arch_name = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch_name = "arm64"
    else:
        raise UnsupportedPlatformError(f"{sys_platform}-{machine}")

    # 构建 target_key
    target_key = f"{os_name}-{arch_name}"

    # 检查支持性
    supported_targets = {
        "darwin-arm64",
        "darwin-x86_64",
        "linux-x86_64",
        "windows-x86_64"
    }

    is_supported = target_key in supported_targets

    # 如果不支持，抛出异常
    if not is_supported:
        raise UnsupportedPlatformError(target_key)

    # 设置文件后缀
    exe_suffix = ".exe" if os_name == "windows" else ""

    # 设置压缩包格式
    archive_ext = ".zip" if os_name == "windows" else ".tar.gz"

    return PlatformTarget(
        os=os_name,
        arch=arch_name,
        target_key=target_key,
        exe_suffix=exe_suffix,
        archive_ext=archive_ext,
        is_supported=is_supported
    )


def get_artifact_filename(target: PlatformTarget) -> str:
    """返回 Obscura release artifact 文件名"""
    # 基于实际 release 命名格式
    if target.target_key == "darwin-arm64":
        return f"obscura-aarch64-macos.tar.gz"
    elif target.target_key == "darwin-x86_64":
        return f"obscura-x86_64-macos.tar.gz"
    elif target.target_key == "linux-x86_64":
        return f"obscura-x86_64-linux.tar.gz"
    elif target.target_key == "windows-x86_64":
        return f"obscura-x86_64-windows.zip"
    else:
        raise UnsupportedPlatformError(target.target_key)