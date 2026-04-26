from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Any


SourceType = Literal["builtin", "atom", "adapter"]
PRIORITY: dict[SourceType, int] = {"builtin": 0, "atom": 1, "adapter": 2}


@dataclass
class CommandEntry:
    name: str
    source: SourceType
    qualified_name: str           # = name 通常；冲突方 = "adapter:{domain}.{name}"
    params: list[dict] = field(default_factory=list)
    returns: dict = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)
    version: str = "0.0.0"
    is_conflict_loser: bool = False


class Registry:
    def __init__(self):
        self._entries: dict[str, CommandEntry] = {}
        self._losers: list[CommandEntry] = []
        self._conflicts: list[str] = []

    def collect(
        self,
        builtin_names: list[str],
        atom_names: list[str],
        adapter_entries: list[tuple[str, str]],   # [(name, domain), ...]
    ) -> "Registry":
        """
        合并三源。builtin > atom > adapter 优先级。
        同名冲突：winner 保留 name；loser 挂 qualified_name="adapter:{domain}.{name}"。
        """
        all_entries: list[CommandEntry] = []

        for n in builtin_names:
            all_entries.append(CommandEntry(name=n, source="builtin", qualified_name=n))

        for n in atom_names:
            all_entries.append(CommandEntry(name=n, source="atom", qualified_name=n))

        for (n, domain) in adapter_entries:
            all_entries.append(CommandEntry(name=n, source="adapter", qualified_name=n,
                                            version="0.0.0"))

        groups: dict[str, list[CommandEntry]] = {}
        for e in all_entries:
            groups.setdefault(e.name, []).append(e)

        for name, candidates in groups.items():
            candidates.sort(key=lambda e: PRIORITY[e.source])
            winner = candidates[0]
            self._entries[name] = winner

            for loser in candidates[1:]:
                domain = next(
                    (d for (n, d) in adapter_entries if n == name),
                    "unknown"
                )
                loser.qualified_name = f"adapter:{domain}.{name}"
                loser.is_conflict_loser = True
                self._losers.append(loser)
                msg = (
                    f"registry conflict: '{name}' from {loser.source}"
                    f" overridden by {winner.source} → use '{loser.qualified_name}'"
                )
                self._conflicts.append(msg)

        return self

    @property
    def conflicts(self) -> list[str]:
        return list(self._conflicts)

    def get(self, name: str) -> CommandEntry | None:
        entry = self._entries.get(name)
        if entry:
            return entry
        # 也能通过 qualified_name 查冲突方
        for loser in self._losers:
            if loser.qualified_name == name:
                return loser
        return None

    def list(self, source: SourceType | None = None) -> list[CommandEntry]:
        entries = list(self._entries.values()) + self._losers
        if source:
            return [e for e in entries if e.source == source]
        return entries

    def to_agent_md_dict(self) -> list[dict]:
        return [
            {
                "name": e.name,
                "source": e.source,
                "qualified_name": e.qualified_name,
                "params": e.params,
                "returns": e.returns,
                "examples": e.examples,
                "version": e.version,
            }
            for e in self._entries.values()
        ]

    def to_explain_dict(self) -> dict:
        return {
            "commands": self.to_agent_md_dict(),
            "conflicts": self._conflicts,
        }
