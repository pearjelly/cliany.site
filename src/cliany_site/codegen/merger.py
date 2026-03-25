from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cliany_site.codegen.generator import AdapterGenerator, _safe_domain
from cliany_site.explorer.models import (
    ActionStep,
    CommandSuggestion,
    ExploreResult,
    PageInfo,
)


@dataclass
class ConflictInfo:
    name: str
    existing: dict[str, Any]
    incoming: dict[str, Any]


@dataclass
class MergeResult:
    merged: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[ConflictInfo] = field(default_factory=list)
    conflicts_resolved: list[dict[str, Any]] = field(default_factory=list)
    added_count: int = 0
    total_count: int = 0


class AdapterMerger:
    def __init__(self, domain: str):
        self.domain = domain
        self._adapter_dir = (
            Path.home() / ".cliany-site" / "adapters" / _safe_domain(domain)
        )
        self._metadata_path = self._adapter_dir / "metadata.json"
        self._commands_path = self._adapter_dir / "commands.py"

    @property
    def metadata_path(self) -> Path:
        return self._metadata_path

    def load_existing(self) -> list[dict[str, Any]]:
        if not self._metadata_path.exists():
            return []

        try:
            data = json.loads(self._metadata_path.read_text(encoding="utf-8"))
            commands = data.get("commands", [])
            if not isinstance(commands, list):
                return []

            if commands and isinstance(commands[0], str):
                return []

            normalized: list[dict[str, Any]] = []
            for item in commands:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                normalized.append(item)
            return normalized
        except (json.JSONDecodeError, OSError):
            return []

    def merge_commands(
        self,
        existing: list[dict[str, Any]],
        new_commands: list[CommandSuggestion],
        new_actions: list[ActionStep],
    ) -> MergeResult:
        result = MergeResult()

        existing_by_name: dict[str, dict[str, Any]] = {}
        for cmd in existing:
            if not isinstance(cmd, dict):
                continue
            name = str(cmd.get("name") or "").strip()
            if not name or name in existing_by_name:
                continue
            existing_by_name[name] = cmd
            result.merged.append(cmd)

        for cmd in new_commands:
            new_def = self._build_command_definition(cmd, new_actions)
            name = str(new_def.get("name") or "").strip()
            if not name:
                continue

            if name in existing_by_name:
                result.conflicts.append(
                    ConflictInfo(
                        name=name,
                        existing=existing_by_name[name],
                        incoming=new_def,
                    )
                )
                continue

            result.merged.append(new_def)
            existing_by_name[name] = new_def
            result.added_count += 1

        result.total_count = len(result.merged)
        return result

    def save_merged(self, merge_result: MergeResult) -> None:
        explore_result = self._rebuild_explore_result(merge_result.merged)
        generator = AdapterGenerator()
        code = generator.generate(explore_result, self.domain)
        existing_metadata = self._load_existing_metadata()

        self._adapter_dir.mkdir(parents=True, exist_ok=True)

        self._atomic_write_text(self._commands_path, code)

        metadata = {
            "domain": self.domain,
            "commands": merge_result.merged,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_url": existing_metadata.get("source_url", f"https://{self.domain}"),
            "workflow": existing_metadata.get("workflow", ""),
        }
        self._atomic_write_json(self._metadata_path, metadata)

    def _load_existing_metadata(self) -> dict[str, Any]:
        if not self._metadata_path.exists():
            return {}

        try:
            data = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

        return data if isinstance(data, dict) else {}

    def merge(
        self, explore_result: ExploreResult, json_mode: bool = True
    ) -> MergeResult:
        existing = self.load_existing()
        merge_result = self.merge_commands(
            existing=existing,
            new_commands=explore_result.commands,
            new_actions=explore_result.actions,
        )

        if merge_result.conflicts and json_mode:
            existing_names = {
                str(cmd.get("name") or "").strip()
                for cmd in merge_result.merged
                if isinstance(cmd, dict)
            }

            for conflict in merge_result.conflicts:
                base_name = conflict.name
                suffix = 2
                candidate = f"{base_name}-{suffix}"
                while candidate in existing_names:
                    suffix += 1
                    candidate = f"{base_name}-{suffix}"

                resolved = dict(conflict.incoming)
                resolved["name"] = candidate
                merge_result.merged.append(resolved)
                merge_result.added_count += 1
                existing_names.add(candidate)
                merge_result.conflicts_resolved.append(
                    {
                        "original_name": base_name,
                        "action": "renamed",
                        "final_name": candidate,
                    }
                )

            merge_result.total_count = len(merge_result.merged)

        elif merge_result.conflicts and not json_mode:
            import click

            existing_names = {
                str(cmd.get("name") or "").strip()
                for cmd in merge_result.merged
                if isinstance(cmd, dict)
            }

            for conflict in merge_result.conflicts:
                base_name = conflict.name
                click.echo(f"\n命令冲突：'{base_name}' 已存在于当前适配器中。")
                click.echo(f"  现有：{conflict.existing.get('description', '')}")
                click.echo(f"  新增：{conflict.incoming.get('description', '')}")
                choice = click.prompt(
                    f"命令 '{base_name}' 已存在。请选择操作",
                    type=click.Choice(["1", "2", "3"]),
                    default="2",
                    show_choices=False,
                    prompt_suffix="\n  1=覆盖（用新命令替换旧命令）\n  2=保留原有（跳过新命令）\n  3=重命名新的（自动重命名新命令）\n请输入选择 [1/2/3]",
                )

                if choice == "1":
                    # 覆盖：用新命令替换现有命令
                    merge_result.merged = [
                        cmd
                        if str(cmd.get("name") or "").strip() != base_name
                        else dict(conflict.incoming)
                        for cmd in merge_result.merged
                        if isinstance(cmd, dict)
                    ]
                    merge_result.added_count += 1
                    merge_result.conflicts_resolved.append(
                        {
                            "original_name": base_name,
                            "action": "overwritten",
                            "final_name": base_name,
                        }
                    )
                    click.echo(f"  ✓ 已覆盖命令 '{base_name}'")
                elif choice == "2":
                    # 保留原有：跳过新命令
                    merge_result.conflicts_resolved.append(
                        {
                            "original_name": base_name,
                            "action": "kept_existing",
                            "final_name": base_name,
                        }
                    )
                    click.echo(f"  ✓ 保留原有命令 '{base_name}'")
                else:
                    # 重命名新的：使用与 json_mode=True 相同的后缀逻辑
                    suffix = 2
                    candidate = f"{base_name}-{suffix}"
                    while candidate in existing_names:
                        suffix += 1
                        candidate = f"{base_name}-{suffix}"

                    resolved = dict(conflict.incoming)
                    resolved["name"] = candidate
                    merge_result.merged.append(resolved)
                    merge_result.added_count += 1
                    existing_names.add(candidate)
                    merge_result.conflicts_resolved.append(
                        {
                            "original_name": base_name,
                            "action": "renamed",
                            "final_name": candidate,
                        }
                    )
                    click.echo(f"  ✓ 新命令已重命名为 '{candidate}'")

            merge_result.total_count = len(merge_result.merged)

        self.save_merged(merge_result)
        return merge_result

    def _build_command_definition(
        self,
        command: CommandSuggestion,
        actions: list[ActionStep],
    ) -> dict[str, Any]:
        cmd_actions: list[dict[str, Any]] = []
        for step_idx in command.action_steps or []:
            if not isinstance(step_idx, int):
                continue
            if 0 <= step_idx < len(actions):
                action = actions[step_idx]
                cmd_actions.append(
                    {
                        "action_type": action.action_type,
                        "page_url": action.page_url,
                        "target_ref": action.target_ref,
                        "target_url": action.target_url,
                        "value": action.value,
                        "description": action.description,
                        "target_name": action.target_name,
                        "target_role": action.target_role,
                        "target_attributes": action.target_attributes,
                    }
                )

        return {
            "name": command.name,
            "description": command.description,
            "args": command.args,
            "action_steps": command.action_steps,
            "actions": cmd_actions,
        }

    def _rebuild_explore_result(
        self, merged_commands: list[dict[str, Any]]
    ) -> ExploreResult:
        all_actions: list[ActionStep] = []
        all_commands: list[CommandSuggestion] = []

        for cmd_def in merged_commands:
            if not isinstance(cmd_def, dict):
                continue

            name = str(cmd_def.get("name") or "").strip()
            if not name:
                continue

            action_start = len(all_actions)
            cmd_actions = cmd_def.get("actions", [])
            action_count = 0
            if isinstance(cmd_actions, list):
                for raw_action in cmd_actions:
                    if not isinstance(raw_action, dict):
                        continue

                    raw_attributes = raw_action.get("target_attributes", {})
                    if isinstance(raw_attributes, dict):
                        target_attributes = {
                            str(key): str(value)
                            for key, value in raw_attributes.items()
                        }
                    else:
                        target_attributes = {}

                    all_actions.append(
                        ActionStep(
                            action_type=str(raw_action.get("action_type") or ""),
                            page_url=str(raw_action.get("page_url") or ""),
                            target_ref=str(raw_action.get("target_ref") or ""),
                            target_url=str(raw_action.get("target_url") or ""),
                            value=str(raw_action.get("value") or ""),
                            description=str(raw_action.get("description") or ""),
                            target_name=str(raw_action.get("target_name") or ""),
                            target_role=str(raw_action.get("target_role") or ""),
                            target_attributes=target_attributes,
                        )
                    )
                    action_count += 1

            args = cmd_def.get("args", [])
            all_commands.append(
                CommandSuggestion(
                    name=name,
                    description=str(cmd_def.get("description") or ""),
                    args=args if isinstance(args, list) else [],
                    action_steps=list(range(action_start, action_start + action_count)),
                )
            )

        pages = [PageInfo(url=f"https://{self.domain}", title=self.domain)]
        return ExploreResult(pages=pages, actions=all_actions, commands=all_commands)

    def _atomic_write_text(self, path: Path, content: str) -> None:
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.replace(tmp_path, str(path))
        except (OSError, TypeError, ValueError):
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _atomic_write_json(self, path: Path, payload: dict[str, Any]) -> None:
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(path))
        except (OSError, TypeError, ValueError):
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


__all__ = ["AdapterMerger", "MergeResult", "ConflictInfo"]
