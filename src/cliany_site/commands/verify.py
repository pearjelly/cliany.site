from __future__ import annotations

import hashlib
import importlib.resources as importlib_resources
import json
import logging
from pathlib import Path
from typing import Any, cast

import click

from cliany_site.config import get_config
from cliany_site.envelope import ok
from cliany_site.marketplace import MANIFEST_VERSION
from cliany_site.metadata import LegacyMetadataError, MetadataParseError, load_metadata

logger = logging.getLogger(__name__)

BANNED_PATTERNS = ["eval(", "exec(", "__import__(", "subprocess.", "os.system("]
REQUIRED_MANIFEST_FILES = {"commands.py", "metadata.json"}


def _load_schema() -> dict:
    try:
        ref = importlib_resources.files("cliany_site").joinpath("schemas/metadata.v3.json")
        content = ref.read_text(encoding="utf-8")
        return cast(dict[str, Any], json.loads(content))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("无法加载 schema 文件: %s", exc)
        return {}


def _scan_security(commands_py: Path) -> list[str]:
    issues: list[str] = []
    try:
        source = commands_py.read_text(encoding="utf-8")
    except OSError:
        return issues

    for lineno, line in enumerate(source.splitlines(), 1):
        for pattern in BANNED_PATTERNS:
            if pattern in line:
                issues.append(f"第 {lineno} 行包含禁用模式: {pattern!r}")
    return issues


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_manifest(adapter_dir: Path, domain: str) -> dict[str, Any]:
    manifest_path = adapter_dir / "manifest.json"
    if not manifest_path.exists():
        return {
            "status": "missing",
            "issues": [],
            "action": "未检测到 market manifest；若需要分发，请运行 cliany-site market publish <domain>。",
        }

    issues: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "status": "error",
            "issues": [f"manifest.json 解析失败: {exc}"],
            "action": "请重新安装该 adapter，或在来源环境重新运行 cliany-site market publish <domain>。",
        }

    manifest_version = str(manifest.get("manifest_version", ""))
    if manifest_version != MANIFEST_VERSION:
        issues.append(f"manifest_version 应为 {MANIFEST_VERSION!r}，实际为 {manifest_version!r}")

    manifest_domain = str(manifest.get("domain", ""))
    if manifest_domain != domain:
        issues.append(f"manifest.domain 应为 {domain!r}，实际为 {manifest_domain!r}")

    files = manifest.get("files")
    file_hashes = manifest.get("file_hashes")
    if not isinstance(files, list):
        issues.append("manifest.files 必须是数组")
        files = []
    if not isinstance(file_hashes, dict):
        issues.append("manifest.file_hashes 必须是对象")
        file_hashes = {}

    manifest_files = {str(f) for f in files}
    hash_files = {str(f) for f in file_hashes}

    missing_required = sorted(REQUIRED_MANIFEST_FILES - manifest_files)
    if missing_required:
        issues.append(f"manifest.files 缺少必要文件: {', '.join(missing_required)}")

    missing_hashes = sorted(manifest_files - hash_files)
    if missing_hashes:
        issues.append(f"manifest.file_hashes 缺少文件: {', '.join(missing_hashes)}")

    unknown_hashes = sorted(hash_files - manifest_files)
    if unknown_hashes:
        issues.append(f"manifest.file_hashes 包含未声明文件: {', '.join(unknown_hashes)}")

    for filename in sorted(manifest_files):
        if Path(filename).name != filename:
            issues.append(f"manifest.files 包含不安全文件名: {filename}")
            continue

        file_path = adapter_dir / filename
        if not file_path.is_file():
            issues.append(f"已安装 adapter 缺少声明文件: {filename}")
            continue

        expected_hash = str(file_hashes.get(filename, ""))
        if expected_hash:
            actual_hash = _sha256_file(file_path)
            if actual_hash != expected_hash:
                issues.append(f"文件哈希不匹配: {filename}")

    if issues:
        return {
            "status": "error",
            "issues": issues,
            "action": "请重新安装可信 adapter 包，或在来源环境重新运行 cliany-site market publish <domain> 后再安装。",
        }

    return {
        "status": "ok",
        "issues": [],
        "action": "manifest 与已安装文件一致。",
    }


def _verify_single(domain: str, schema: dict) -> dict:
    cfg = get_config()
    adapter_dir = cfg.adapters_dir / domain
    metadata_path = adapter_dir / "metadata.json"
    commands_py = adapter_dir / "commands.py"

    result: dict = {"domain": domain, "verdict": "ok", "issues": [], "smoke": None}

    # Step 1: 加载 metadata（检测旧版/解析失败）
    try:
        metadata = load_metadata(metadata_path)
    except LegacyMetadataError as exc:
        result["verdict"] = "legacy_adapter"
        result["issues"] = [str(exc)]
        return result
    except MetadataParseError as exc:
        result["verdict"] = "schema_error"
        result["issues"] = [str(exc)]
        return result

    # Step 2: jsonschema 完整验证
    if schema:
        try:
            import jsonschema as _jsonschema

            _jsonschema.validate(metadata, schema)
        except _jsonschema.ValidationError as exc:
            result["verdict"] = "schema_error"
            result["issues"] = [exc.message]
            return result
        except Exception as exc:  # noqa: BLE001
            result["verdict"] = "schema_error"
            result["issues"] = [str(exc)]
            return result

    # Step 3: AST 安全扫描
    if commands_py.exists():
        security_issues = _scan_security(commands_py)
        if security_issues:
            result["verdict"] = "security_issue"
            result["issues"] = security_issues
            return result

    manifest_result = _verify_manifest(adapter_dir, domain)
    result["manifest"] = manifest_result
    if manifest_result["status"] == "error":
        result["verdict"] = "manifest_error"
        result["issues"] = manifest_result["issues"]
        return result

    return result


def _run_smoke(domain: str) -> bool:
    import asyncio

    try:
        from cliany_site.browser.cdp import CDPConnection

        async def _check() -> bool:
            cdp = CDPConnection()
            return await cdp.check_available()

        return asyncio.run(_check())
    except Exception:  # noqa: BLE001
        return False


def _print_human(results: list[dict]) -> None:
    if not results:
        click.echo("没有找到 adapter")
        return

    for r in results:
        verdict = r["verdict"]
        domain = r["domain"]
        issues = r.get("issues", [])
        smoke = r.get("smoke")
        manifest = r.get("manifest")

        if verdict == "ok":
            icon = "✓"
        elif verdict == "legacy_adapter":
            icon = "⚠"
        else:
            icon = "✗"

        parts = [f"{icon} {domain}  verdict={verdict}"]
        if issues:
            parts.append(f"issues={issues}")
        if smoke is not None:
            parts.append(f"smoke={'pass' if smoke else 'fail'}")
        if isinstance(manifest, dict):
            parts.append(f"manifest={manifest.get('status')}")

        click.echo("  ".join(parts))


@click.command("verify")
@click.argument("domain", required=False)
@click.option("--smoke", "smoke", is_flag=True, default=False, help="附加 CDP 冒烟测试（需要 Chrome）")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def verify_cmd(
    ctx: click.Context,
    domain: str | None,
    smoke: bool,
    json_mode: bool | None,
) -> None:
    """静态检查 adapter 完整性（schema + 安全扫描），可选 CDP 冒烟"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    cfg = get_config()
    schema = _load_schema()

    domains_to_verify: list[str] = []
    if domain:
        adapter_dir = cfg.adapters_dir / domain
        if adapter_dir.exists():
            domains_to_verify = [domain]
    else:
        if cfg.adapters_dir.exists():
            domains_to_verify = sorted(
                d.name for d in cfg.adapters_dir.iterdir() if d.is_dir()
            )

    results: list[dict] = []
    for d in domains_to_verify:
        r = _verify_single(d, schema)
        if smoke:
            smoke_ok = _run_smoke(d)
            r["smoke"] = smoke_ok
            if not smoke_ok and r["verdict"] == "ok":
                r["verdict"] = "smoke_failed"
                r["issues"] = list(r.get("issues", [])) + ["CDP 冒烟测试失败"]
        results.append(r)

    envelope = ok(
        command="verify",
        data={
            "domain": domain or "all",
            "results": results,
        },
        source="builtin",
    )

    if effective_json_mode:
        import json as _json

        click.echo(_json.dumps(envelope, ensure_ascii=False, indent=2))
    else:
        _print_human(results)
