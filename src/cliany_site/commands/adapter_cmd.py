from __future__ import annotations

import contextlib
import json
import logging
import time

import click

from cliany_site.config import get_config
from cliany_site.envelope import ErrorCode, err, ok

logger = logging.getLogger(__name__)

adapter_group = click.Group("adapter", help="adapter 管理命令")


def _merge_healed_into_metadata(metadata: dict, healed: dict) -> dict:
    import copy

    merged = copy.deepcopy(metadata)
    new_selectors: dict = healed.get("new_selectors") or {}
    new_actions: list = healed.get("new_actions") or []
    healed_command: str = healed.get("healed_command", "")

    if new_selectors:
        pool = merged.setdefault("selector_pool", [])
        for ref, selector in new_selectors.items():
            pool.append({"ref": ref, "selector": selector, "healed": True})

    if new_actions and healed_command:
        for cmd in merged.get("commands", []):
            if cmd.get("name") == healed_command:
                cmd["healed_actions"] = new_actions
                break

    heal_entry = {
        "command": healed_command,
        "timestamp": healed.get("heal_meta", {}).get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        "calls_used": healed.get("heal_meta", {}).get("calls_used", 0),
        "tokens_used": healed.get("heal_meta", {}).get("tokens_used", 0),
    }
    merged.setdefault("heal_history", []).append(heal_entry)

    return merged


def _verify_merged(domain: str, merged: dict) -> list[str]:
    from cliany_site.commands.verify import _load_schema, _scan_security

    issues: list[str] = []
    schema = _load_schema()

    if schema:
        try:
            import jsonschema as _jsonschema

            _jsonschema.validate(merged, schema)
        except Exception as exc:  # noqa: BLE001
            issues.append(str(exc))
            return issues

    cfg = get_config()
    commands_py = cfg.adapters_dir / domain / "commands.py"
    if commands_py.exists():
        sec_issues = _scan_security(commands_py)
        issues.extend(sec_issues)

    return issues


@adapter_group.command("accept-heal")
@click.argument("domain")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def accept_heal(ctx: click.Context, domain: str, json_mode: bool | None) -> None:
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    cfg = get_config()
    healed_path = cfg.adapters_dir / domain / "metadata.healed.json"
    metadata_path = cfg.adapters_dir / domain / "metadata.json"

    if not healed_path.exists():
        envelope = err(
            "adapter accept-heal",
            ErrorCode.E_UNKNOWN,
            f"未找到 metadata.healed.json: {healed_path}",
            hint="先运行带 --heal 的命令以生成 healed.json",
            source="builtin",
        )
        _output(envelope, effective_json)
        ctx.exit(1)
        return

    try:
        healed = json.loads(healed_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        envelope = err(
            "adapter accept-heal",
            ErrorCode.E_UNKNOWN,
            f"无法读取 healed.json: {exc}",
            source="builtin",
        )
        _output(envelope, effective_json)
        ctx.exit(1)
        return

    metadata: dict = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            envelope = err(
                "adapter accept-heal",
                ErrorCode.E_UNKNOWN,
                f"无法读取 metadata.json: {exc}",
                source="builtin",
            )
            _output(envelope, effective_json)
            ctx.exit(1)
            return

    merged = _merge_healed_into_metadata(metadata, healed)
    issues = _verify_merged(domain, merged)

    if issues:
        envelope = err(
            "adapter accept-heal",
            ErrorCode.E_VERIFY_STATIC,
            f"静态检查失败，healed.json 已保留: {issues[0]}",
            details={"issues": issues},
            source="builtin",
        )
        _output(envelope, effective_json)
        ctx.exit(1)
        return

    tmp_path = metadata_path.with_suffix(".tmp")
    try:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(metadata_path)
        healed_path.unlink(missing_ok=True)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        envelope = err(
            "adapter accept-heal",
            ErrorCode.E_UNKNOWN,
            f"写入 metadata.json 失败: {exc}",
            source="builtin",
        )
        _output(envelope, effective_json)
        ctx.exit(1)
        return

    envelope = ok(
        "adapter accept-heal",
        {"domain": domain, "merged": True},
        source="builtin",
    )
    _output(envelope, effective_json)


def _output(envelope: dict, json_mode: bool) -> None:
    if json_mode:
        import json as _json

        click.echo(_json.dumps(envelope, ensure_ascii=False, indent=2))
    else:
        if envelope.get("ok"):
            click.echo(f"✓ accept-heal 成功: {envelope.get('data', {})}")
        else:
            err_obj = envelope.get("error") or {}
            click.echo(f"✗ {err_obj.get('code', 'ERROR')}: {err_obj.get('message', '')}")
