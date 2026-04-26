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
    target_name: str = ""
    target_role: str = ""
    target_attributes: dict[str, str] = field(default_factory=dict)
    selector: str = ""
    extract_mode: str = "text"
    fields_map: dict = field(default_factory=dict)


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
    explore_model: str = ""
    smoke: list[dict] = field(default_factory=list)
    canonical_actions: list[dict] = field(default_factory=list)
    selector_pool: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        import dataclasses

        return dataclasses.asdict(self)


@dataclass
class TurnSnapshot:
    turn_index: int
    actions_before_count: int
    pages_before_count: int
    browser_history_index: int


@dataclass
class StepRecord:
    step_index: int
    action_data: dict
    llm_response_raw: str
    timestamp: str
    screenshot_path: str | None = None
    axtree_snapshot_path: str | None = None
    rolled_back: bool = False


@dataclass
class RecordingManifest:
    domain: str
    session_id: str
    url: str
    workflow: str
    started_at: str
    steps: list[StepRecord] = field(default_factory=list)
    completed: bool = False
