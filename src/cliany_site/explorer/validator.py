from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """单步动作的验证结果。"""

    success: bool = True
    changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_ELEMENT_ACTION_TYPES = {"click", "type", "select"}
_NAVIGATE_ACTION_TYPES = {"navigate"}
_PASSTHROUGH_ACTION_TYPES = {"submit", "reuse_atom"}


def _get_action_type(step: object) -> str:
    if isinstance(step, dict):
        return step.get("action_type", "")
    return getattr(step, "action_type", "")


def _get_description(step: object) -> str:
    if isinstance(step, dict):
        return (
            step.get("target_name")
            or step.get("description")
            or step.get("target_ref")
            or ""
        )
    return (
        getattr(step, "target_name", None)
        or getattr(step, "description", None)
        or getattr(step, "target_ref", None)
        or ""
    )


class ActionValidator:
    """纯逻辑动作验证器 — 根据调用方提供的状态检验步骤，不依赖 CDP/Chrome。"""

    def validate_step(
        self,
        step: object,
        *,
        before_url: str | None = None,
        after_url: str | None = None,
        element_found: bool | None = None,
    ) -> ValidationResult:
        result = ValidationResult()
        action_type = _get_action_type(step)

        if action_type in _NAVIGATE_ACTION_TYPES:
            if before_url is not None and after_url is not None:
                if before_url != after_url:
                    result.changes.append(f"URL 变化: {before_url} → {after_url}")
                else:
                    result.warnings.append("导航操作未产生 URL 变化")

        elif action_type in _ELEMENT_ACTION_TYPES:
            if element_found is False:
                desc = _get_description(step)
                result.success = False
                result.warnings.append(f"目标元素未找到: {desc}")
            elif element_found is True and action_type == "type":
                value: str = ""
                if isinstance(step, dict):
                    value = step.get("value", "")
                else:
                    value = getattr(step, "value", "") or ""
                if value:
                    desc = _get_description(step)
                    result.changes.append(f"输入值: {value} → {desc}")

        return result

    def validate_sequence(
        self,
        steps: list[object],
        *,
        elements_found: list[bool] | None = None,
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for i, step in enumerate(steps):
            found: bool | None = None
            if elements_found is not None and i < len(elements_found):
                found = elements_found[i]
            result = self.validate_step(step, element_found=found)
            results.append(result)
        return results
