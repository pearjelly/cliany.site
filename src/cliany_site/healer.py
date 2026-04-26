from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HealResult:
    ok: bool
    new_selectors: dict[str, str] = field(default_factory=dict)
    new_actions: list[dict] = field(default_factory=list)
    calls_used: int = 0
    tokens_used: int = 0
    error: str | None = None


class Healer:
    def heal(
        self,
        domain: str,
        command: str,
        failure_envelope: dict,
        axtree_summary: str = "",
        max_calls: int | None = None,
        max_tokens: int | None = None,
    ) -> HealResult:
        if os.environ.get("CLIANY_HEAL_DISABLE", "").strip() in ("1", "true", "yes"):
            return HealResult(ok=False, error="E_HEAL_CAP_EXCEEDED")

        resolved_max_calls = self._resolve_max_calls(max_calls)
        resolved_max_tokens = self._resolve_max_tokens(max_tokens)

        if resolved_max_calls <= 0:
            return HealResult(ok=False, error="E_HEAL_CAP_EXCEEDED")

        from cliany_site.config import get_config

        cfg = get_config()
        metadata_path = cfg.adapters_dir / domain / "metadata.json"
        healed_path = cfg.adapters_dir / domain / "metadata.healed.json"

        metadata: dict = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("无法读取 metadata.json: %s", exc)

        try:
            llm = self._get_llm()
        except OSError as exc:
            logger.warning("无法初始化 LLM: %s", exc)
            return HealResult(ok=False, error=str(exc))

        prompt = self._build_prompt(domain, command, failure_envelope, axtree_summary, metadata)

        calls_used = 0
        tokens_used = 0
        response_text = ""

        for attempt in range(resolved_max_calls):
            if tokens_used >= resolved_max_tokens:
                return HealResult(
                    ok=False,
                    calls_used=calls_used,
                    tokens_used=tokens_used,
                    error="E_HEAL_CAP_EXCEEDED",
                )
            try:
                response = llm.invoke(prompt)
                calls_used += 1
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    tokens_used += response.usage_metadata.get("total_tokens", 0)
                elif hasattr(response, "response_metadata"):
                    meta = response.response_metadata or {}
                    usage = meta.get("usage", {})
                    tokens_used += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

                response_text = response.content if hasattr(response, "content") else str(response)
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM 调用失败 (attempt %d): %s", attempt + 1, exc)
                if attempt + 1 >= resolved_max_calls:
                    return HealResult(
                        ok=False,
                        calls_used=calls_used,
                        tokens_used=tokens_used,
                        error=f"LLM call failed: {exc}",
                    )
                time.sleep(1)

        if tokens_used > resolved_max_tokens:
            return HealResult(
                ok=False,
                calls_used=calls_used,
                tokens_used=tokens_used,
                error="E_HEAL_CAP_EXCEEDED",
            )

        parsed = self._parse_response(response_text)
        if not parsed:
            return HealResult(
                ok=False,
                calls_used=calls_used,
                tokens_used=tokens_used,
                error="LLM 响应解析失败",
            )

        new_selectors: dict[str, str] = parsed.get("new_selectors", {})
        new_actions: list[dict] = parsed.get("new_actions", [])

        healed_content = {
            "schema_version": 2,
            "domain": domain,
            "healed_command": command,
            "new_selectors": new_selectors,
            "new_actions": new_actions,
            "heal_meta": {
                "calls_used": calls_used,
                "tokens_used": tokens_used,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }

        try:
            healed_path.parent.mkdir(parents=True, exist_ok=True)
            healed_path.write_text(
                json.dumps(healed_content, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.error("写入 healed.json 失败: %s", exc)
            return HealResult(
                ok=False,
                calls_used=calls_used,
                tokens_used=tokens_used,
                error=f"写入失败: {exc}",
            )

        return HealResult(
            ok=True,
            new_selectors=new_selectors,
            new_actions=new_actions,
            calls_used=calls_used,
            tokens_used=tokens_used,
        )

    @staticmethod
    def _resolve_max_calls(max_calls: int | None) -> int:
        if max_calls is not None:
            return max_calls
        raw = os.environ.get("CLIANY_HEAL_MAX_CALLS", "")
        if raw:
            try:
                return int(raw)
            except ValueError:
                pass
        return 3

    @staticmethod
    def _resolve_max_tokens(max_tokens: int | None) -> int:
        if max_tokens is not None:
            return max_tokens
        raw = os.environ.get("CLIANY_HEAL_MAX_TOKENS", "")
        if raw:
            try:
                return int(raw)
            except ValueError:
                pass
        return 4000

    @staticmethod
    def _get_llm():
        from cliany_site.explorer.engine import _get_llm

        return _get_llm(role="heal")

    @staticmethod
    def _build_prompt(
        domain: str,
        command: str,
        failure_envelope: dict,
        axtree_summary: str,
        metadata: dict,
    ) -> str:
        error_info = ""
        if failure_envelope:
            err_obj = failure_envelope.get("error") or {}
            error_info = f"错误码: {err_obj.get('code', 'unknown')}\n错误信息: {err_obj.get('message', '')}"

        commands_info = ""
        if metadata:
            for cmd in metadata.get("commands", []):
                if cmd.get("name") == command:
                    commands_info = json.dumps(cmd, ensure_ascii=False, indent=2)
                    break

        return (
            f"你是一个网页自动化修复专家。以下适配器命令执行失败，请分析并提供修复建议。\n\n"
            f"域名: {domain}\n命令: {command}\n\n"
            f"失败信息:\n{error_info}\n\n"
            f"命令定义:\n{commands_info or '（未找到命令定义）'}\n\n"
            f"当前页面 AXTree 摘要:\n{axtree_summary or '（未提供）'}\n\n"
            "请以 JSON 格式返回修复建议，包含以下字段：\n"
            '- new_selectors: dict，键为 ref（如 "ref_1"），值为新的 CSS selector 字符串\n'
            "- new_actions: list，每项为修复后的 action 步骤 dict\n\n"
            '只返回 JSON，不要其他内容。示例：\n{"new_selectors": {"ref_1": "#new-selector"}, "new_actions": []}'
        )

    @staticmethod
    def _parse_response(text: str) -> dict | None:
        import re

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group(0)

        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
