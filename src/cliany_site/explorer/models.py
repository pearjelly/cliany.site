from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageInfo:
    url: str
    title: str
    elements: list[dict] = field(default_factory=list)


@dataclass
class ActionStep:
    action_type: str
    page_url: str
    target_ref: str = ""
    target_url: str = ""
    value: str = ""
    description: str = ""


@dataclass
class CommandSuggestion:
    name: str
    description: str
    args: list[dict[str, Any]]
    action_steps: list[int]


@dataclass
class ExploreResult:
    pages: list[PageInfo] = field(default_factory=list)
    actions: list[ActionStep] = field(default_factory=list)
    commands: list[CommandSuggestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        import dataclasses

        return dataclasses.asdict(self)
