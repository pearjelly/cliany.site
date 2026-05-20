"""obscura 命令组 — 管理 Obscura 浏览器 provider。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from cliany_site.binary.cache import CacheError, CacheManager
from cliany_site.binary.platforms import UnsupportedPlatformError, normalize_platform
from cliany_site.binary.process import ProcessManager
from cliany_site.envelope import ErrorCode, err, ok
from cliany_site.errors import BINARY_DOWNLOAD_FAILED, ClanySiteError
from cliany_site.response import print_response

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _effective_json(ctx: click.Context, json_mode: bool | None) -> bool:
    root_obj = ctx.find_root().obj or {}
    if isinstance(root_obj, dict):
        return json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    return bool(json_mode)


def _download_with_retry(url: str, timeout: int = 60, max_attempts: int = 3, base_backoff: float = 1.0) -> bytes:
    import socket
    import time
    import urllib.request
    from urllib.error import HTTPError, URLError

    last_exc: Exception = RuntimeError("未执行下载")
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read()
        except HTTPError as e:
            if e.code and 400 <= e.code < 500:
                raise
            last_exc = e
        except (URLError, socket.timeout, ConnectionResetError) as e:
            last_exc = e

        if attempt < max_attempts - 1:
            wait = base_backoff * (2 ** attempt)
            time.sleep(wait)

    exc_obj = ClanySiteError(f"下载失败（重试 {max_attempts} 次后）: {last_exc}")
    exc_obj.error_code = BINARY_DOWNLOAD_FAILED  # type: ignore[attr-defined]
    raise exc_obj from last_exc


def _download_and_install(version: str, cache_mgr: CacheManager) -> Path:
    import platform as _platform

    from cliany_site.binary.platforms import normalize_platform
    from cliany_site.binary.releases import resolve_release

    plat = normalize_platform(sys.platform, _platform.machine())
    spec = resolve_release(version, plat)

    archive_bytes = _download_with_retry(spec.download_url, timeout=60)

    return cache_mgr.install(spec, archive_bytes)


@click.group(name="obscura", help="管理 Obscura 浏览器 provider（实验性）")
def obscura_group():
    """obscura 子命令组入口。"""


@obscura_group.command(name="install")
@click.argument("version")
@click.option("--json", "json_mode", is_flag=True, default=None)
@click.pass_context
def install_cmd(ctx: click.Context, version: str, json_mode: bool | None):
    """下载并安装指定版本的 Obscura 二进制。"""
    import platform as _platform

    json_mode = _effective_json(ctx, json_mode)

    if not version or not _VERSION_RE.match(version):
        result = err("obscura.install", ErrorCode.E_INVALID_PARAM,
                     f"版本格式无效: {version!r}，必须为 x.y.z 形式")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    try:
        normalize_platform(sys.platform, _platform.machine())
    except UnsupportedPlatformError as exc:
        result = err("obscura.install", ErrorCode.E_UNSUPPORTED_PLATFORM,
                     f"不支持的平台: {exc.target_key}")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    cache_mgr = CacheManager()

    if cache_mgr.is_installed(version):
        binary_path = cache_mgr.get_binary_path(version)
        result = ok("obscura.install", {
            "version": version,
            "path": str(binary_path),
            "already_installed": True,
        })
        print_response(result, json_mode=json_mode, exit_on_error=False)
        return

    try:
        binary_path = _download_and_install(version, cache_mgr)
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "error_code", ErrorCode.E_DOWNLOAD_FAILED)
        result = err("obscura.install", code, str(exc))
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    result = ok("obscura.install", {
        "version": version,
        "path": str(binary_path),
        "already_installed": False,
    })
    print_response(result, json_mode=json_mode, exit_on_error=False)


@obscura_group.command(name="use")
@click.argument("version")
@click.option("--json", "json_mode", is_flag=True, default=None)
@click.pass_context
def use_cmd(ctx: click.Context, version: str, json_mode: bool | None):
    """切换 active Obscura 版本。"""
    json_mode = _effective_json(ctx, json_mode)
    cache_mgr = CacheManager()

    try:
        cache_mgr.set_active_version(version)
        binary_path = cache_mgr.get_binary_path(version)
    except CacheError as exc:
        result = err("obscura.use", exc.error_code, str(exc))
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    result = ok("obscura.use", {
        "active_version": version,
        "path": str(binary_path),
    })
    print_response(result, json_mode=json_mode, exit_on_error=False)


@obscura_group.command(name="status")
@click.option("--json", "json_mode", is_flag=True, default=None)
@click.pass_context
def status_cmd(ctx: click.Context, json_mode: bool | None):
    """显示 Obscura provider 状态摘要。"""
    json_mode = _effective_json(ctx, json_mode)
    cache_mgr = CacheManager()

    active_version = cache_mgr.get_active_version()
    installed_versions = cache_mgr.list_versions()

    binary_path: str | None = None
    if active_version:
        try:
            binary_path = str(cache_mgr.get_binary_path(active_version))
        except CacheError:
            binary_path = None

    proc_status = ProcessManager().get_status()

    source = "managed" if (active_version and binary_path) else "external"

    capabilities = {
        "provider": "obscura",
        "supports_axtree": False,
        "supports_navigation": True,
        "supports_screenshot": True,
        "supports_cookies": True,
        "supports_network_events": True,
        "supports_console_events": True,
    }

    result = ok("obscura.status", {
        "active_version": active_version,
        "installed_versions": installed_versions,
        "provider": "obscura",
        "path": binary_path,
        "source": source,
        "capabilities": capabilities,
        "process": {
            "state": proc_status.state,
            "pid": proc_status.pid,
        },
    })
    print_response(result, json_mode=json_mode, exit_on_error=False)


@obscura_group.command(name="clean")
@click.option("--version", "version", default=None, help="要删除的版本号")
@click.option("--all", "all_versions", is_flag=True, default=False, help="删除所有非活跃版本")
@click.option("--json", "json_mode", is_flag=True, default=None)
@click.pass_context
def clean_cmd(ctx: click.Context, version: str | None, all_versions: bool, json_mode: bool | None):
    """删除指定版本缓存（或 --all 删除全部非活跃版本）。"""
    json_mode = _effective_json(ctx, json_mode)

    if not version and not all_versions:
        result = err("obscura.clean", ErrorCode.E_INVALID_PARAM, "必须提供 --version 或 --all 参数")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    if version and all_versions:
        result = err("obscura.clean", ErrorCode.E_INVALID_PARAM, "--version 与 --all 不可同时使用")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    cache_mgr = CacheManager()

    if version:
        try:
            cache_mgr.remove_version(version)
        except CacheError as exc:
            result = err("obscura.clean", exc.error_code, str(exc))
            print_response(result, json_mode=json_mode, exit_on_error=False)
            sys.exit(1)
        result = ok("obscura.clean", {"removed": [version], "skipped": []})
        print_response(result, json_mode=json_mode, exit_on_error=False)
        return

    active_version = cache_mgr.get_active_version()
    installed = cache_mgr.list_versions()
    removed = []
    skipped = []

    for v in installed:
        if v == active_version:
            skipped.append(v)
            continue
        try:
            cache_mgr.remove_version(v)
            removed.append(v)
        except CacheError:
            skipped.append(v)

    result = ok("obscura.clean", {"removed": removed, "skipped": skipped})
    print_response(result, json_mode=json_mode, exit_on_error=False)


@obscura_group.command(name="rollback")
@click.option("--json", "json_mode", is_flag=True, default=None)
@click.pass_context
def rollback_cmd(ctx: click.Context, json_mode: bool | None):
    """将 active version 回退到已安装的上一个版本。"""
    json_mode = _effective_json(ctx, json_mode)
    cache_mgr = CacheManager()

    installed = cache_mgr.list_versions()
    active = cache_mgr.get_active_version()

    if active is None or len(installed) == 0:
        result = err("obscura.rollback", ErrorCode.E_BINARY_NOT_FOUND, "没有已安装的版本，无法回退")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    if active not in installed:
        result = err("obscura.rollback", ErrorCode.E_BINARY_NOT_FOUND,
                     f"当前活跃版本 {active} 未在已安装列表中")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    idx = installed.index(active)
    if idx == 0:
        result = err("obscura.rollback", ErrorCode.E_BINARY_NOT_FOUND,
                     f"当前已是最旧版本 {active}，无法回退")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    prev_version = installed[idx - 1]
    try:
        cache_mgr.set_active_version(prev_version)
    except CacheError as exc:
        result = err("obscura.rollback", exc.error_code, str(exc))
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    result = ok("obscura.rollback", {
        "previous_version": active,
        "active_version": prev_version,
    })
    print_response(result, json_mode=json_mode, exit_on_error=False)


@obscura_group.command(name="upgrade")
@click.argument("version")
@click.option("--json", "json_mode", is_flag=True, default=None)
@click.pass_context
def upgrade_cmd(ctx: click.Context, version: str, json_mode: bool | None):
    """显式安装新版本并切换为活跃版本。"""
    import platform as _platform

    json_mode = _effective_json(ctx, json_mode)

    if not version or not _VERSION_RE.match(version):
        result = err("obscura.upgrade", ErrorCode.E_INVALID_PARAM,
                     f"版本格式无效: {version!r}，必须为 x.y.z 形式")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    try:
        normalize_platform(sys.platform, _platform.machine())
    except UnsupportedPlatformError as exc:
        result = err("obscura.upgrade", ErrorCode.E_UNSUPPORTED_PLATFORM,
                     f"不支持的平台: {exc.target_key}")
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    cache_mgr = CacheManager()

    try:
        binary_path = _download_and_install(version, cache_mgr)
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "error_code", ErrorCode.E_DOWNLOAD_FAILED)
        result = err("obscura.upgrade", code, str(exc))
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    try:
        cache_mgr.set_active_version(version)
    except CacheError as exc:
        result = err("obscura.upgrade", exc.error_code, str(exc))
        print_response(result, json_mode=json_mode, exit_on_error=False)
        sys.exit(1)

    result = ok("obscura.upgrade", {
        "version": version,
        "path": str(binary_path),
        "active_version": version,
    })
    print_response(result, json_mode=json_mode, exit_on_error=False)


@obscura_group.command(name="doctor")
@click.option("--json", "json_mode", is_flag=True, default=None)
@click.pass_context
def doctor_cmd(ctx: click.Context, json_mode: bool | None):
    """输出 Obscura 专项诊断信息。"""
    import platform as _platform

    json_mode = _effective_json(ctx, json_mode)
    cache_mgr = CacheManager()

    active_version = cache_mgr.get_active_version()
    installed_versions = cache_mgr.list_versions()

    proc_status = ProcessManager().get_status()
    stale_pid = proc_status.stale

    try:
        plat = normalize_platform(sys.platform, _platform.machine())
        platform_info: dict = {"ok": True, "target_key": plat.target_key}
    except UnsupportedPlatformError as exc:
        platform_info = {"ok": False, "target_key": exc.target_key, "error": str(exc)}

    capabilities = {
        "provider": "obscura",
        "supports_axtree": False,
        "supports_navigation": True,
        "supports_screenshot": True,
        "supports_cookies": True,
        "supports_network_events": True,
        "supports_console_events": True,
    }

    result = ok("obscura.doctor", {
        "cache": {
            "installed_versions": installed_versions,
            "active_version": active_version,
        },
        "stale_pid": stale_pid,
        "platform": platform_info,
        "capabilities": capabilities,
        "process": {
            "state": proc_status.state,
            "pid": proc_status.pid,
        },
    })
    print_response(result, json_mode=json_mode, exit_on_error=False)
