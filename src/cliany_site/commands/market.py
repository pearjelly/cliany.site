from __future__ import annotations

import click

from cliany_site.errors import ADAPTER_NOT_FOUND, EXECUTION_FAILED
from cliany_site.marketplace import (
    get_adapter_info,
    install_adapter,
    list_backups,
    pack_adapter,
    rollback_adapter,
    uninstall_adapter,
)
from cliany_site.response import error_response, print_response, success_response


@click.group("market", help="适配器市场：打包/安装/卸载/回滚")
def market_group() -> None:
    pass


@market_group.command("publish")
@click.argument("domain")
@click.option("--version", "-v", default="0.1.0", help="版本号")
@click.option("--author", "-a", default="", help="作者")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def publish_cmd(ctx: click.Context, domain: str, version: str, author: str, json_mode: bool) -> None:
    """打包并导出适配器"""
    root = ctx.find_root()
    jm = json_mode or (isinstance(root.obj, dict) and root.obj.get("json_mode", False))

    try:
        pack_path = pack_adapter(domain, version=version, author=author)
        resp = success_response({"domain": domain, "version": version, "pack_path": str(pack_path)})
    except FileNotFoundError as exc:
        resp = error_response(ADAPTER_NOT_FOUND, str(exc))
    except OSError as exc:
        resp = error_response(EXECUTION_FAILED, str(exc))

    print_response(resp, json_mode=jm)


@market_group.command("install")
@click.argument("pack_path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, default=False, help="强制覆盖已安装版本")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def install_cmd(ctx: click.Context, pack_path: str, force: bool, json_mode: bool) -> None:
    """从分发包安装适配器"""
    root = ctx.find_root()
    jm = json_mode or (isinstance(root.obj, dict) and root.obj.get("json_mode", False))

    try:
        manifest = install_adapter(pack_path, force=force)
        resp = success_response(manifest.to_dict())
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        resp = error_response(EXECUTION_FAILED, str(exc))
    except OSError as exc:
        resp = error_response(EXECUTION_FAILED, str(exc))

    print_response(resp, json_mode=jm)


@market_group.command("uninstall")
@click.argument("domain")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def uninstall_cmd(ctx: click.Context, domain: str, json_mode: bool) -> None:
    """卸载指定域名的适配器"""
    root = ctx.find_root()
    jm = json_mode or (isinstance(root.obj, dict) and root.obj.get("json_mode", False))

    removed = uninstall_adapter(domain)
    if removed:
        resp = success_response({"domain": domain, "removed": True})
    else:
        resp = error_response(ADAPTER_NOT_FOUND, f"adapter '{domain}' 不存在")

    print_response(resp, json_mode=jm)


@market_group.command("info")
@click.argument("domain")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def info_cmd(ctx: click.Context, domain: str, json_mode: bool) -> None:
    """查看适配器详细信息"""
    root = ctx.find_root()
    jm = json_mode or (isinstance(root.obj, dict) and root.obj.get("json_mode", False))

    info = get_adapter_info(domain)
    resp = success_response(info) if info else error_response(ADAPTER_NOT_FOUND, f"adapter '{domain}' 不存在")

    print_response(resp, json_mode=jm)


@market_group.command("rollback")
@click.argument("domain")
@click.option("--index", "-i", default=0, type=int, help="备份索引 (0=最新)")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def rollback_cmd(ctx: click.Context, domain: str, index: int, json_mode: bool) -> None:
    """回滚适配器到备份版本"""
    root = ctx.find_root()
    jm = json_mode or (isinstance(root.obj, dict) and root.obj.get("json_mode", False))

    success = rollback_adapter(domain, backup_index=index)
    if success:
        resp = success_response({"domain": domain, "rolled_back": True})
    else:
        backups = list_backups(domain)
        if not backups:
            resp = error_response(ADAPTER_NOT_FOUND, f"adapter '{domain}' 没有可用的备份")
        else:
            resp = error_response(EXECUTION_FAILED, f"回滚失败 (索引 {index}，共 {len(backups)} 个备份)")

    print_response(resp, json_mode=jm)


@market_group.command("backups")
@click.argument("domain")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def backups_cmd(ctx: click.Context, domain: str, json_mode: bool) -> None:
    """列出适配器的所有备份"""
    root = ctx.find_root()
    jm = json_mode or (isinstance(root.obj, dict) and root.obj.get("json_mode", False))

    backups = list_backups(domain)
    resp = success_response({"domain": domain, "backups": backups})
    print_response(resp, json_mode=jm)
