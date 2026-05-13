# src/cliany_site/binary/releases.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cliany_site.binary.platforms import PlatformTarget, get_artifact_filename
from cliany_site.envelope import ErrorCode
from cliany_site.errors import ClanySiteError


@dataclass(frozen=True)
class ArtifactSpec:
    """Obscura release artifact 规范"""
    version: str
    platform: PlatformTarget
    download_url: str
    filename: str


class ReleaseNotFoundError(ClanySiteError):
    """Release 不存在异常"""
    pass


class DownloadError(Exception):
    """下载相关异常"""
    error_code: str

    def __init__(self, message: str):
        self.error_code = ErrorCode.E_DOWNLOAD_FAILED
        super().__init__(message)


def resolve_release(
    version: Optional[str],
    platform: PlatformTarget,
    *,
    offline: bool = False,
    cache_root: Path | None = None,
) -> ArtifactSpec:
    """解析 Obscura release，返回 artifact 规范

    Args:
        version: 版本号，必须显式指定，不支持 'latest'
        platform: 目标平台
        offline: 是否离线模式
        cache_root: 缓存根目录，仅在 offline=True 时使用

    Returns:
        ArtifactSpec: artifact 规范

    Raises:
        ReleaseNotFoundError: 当 version 为 'latest' 或 None 时
        DownloadError: 当 offline=True 但缓存中不存在时
    """
    if version == "latest" or version is None:
        raise ReleaseNotFoundError("必须显式指定版本号，不支持 'latest'")

    filename = get_artifact_filename(platform)
    download_url = f"https://github.com/h4ckf0r0day/obscura/releases/download/v{version}/{filename}"

    if offline:
        if cache_root is None:
            raise DownloadError("离线模式需要指定 cache_root")
        cached_file = cache_root / version / filename
        if not cached_file.exists():
            raise DownloadError(f"缓存中不存在版本 {version} 的 artifact: {cached_file}")
        # 返回本地文件 URL
        local_url = f"file://{cached_file.absolute()}"
        return ArtifactSpec(
            version=version,
            platform=platform,
            download_url=local_url,
            filename=filename,
        )

    return ArtifactSpec(
        version=version,
        platform=platform,
        download_url=download_url,
        filename=filename,
    )