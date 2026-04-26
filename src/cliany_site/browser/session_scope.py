from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionScope:
    name: str | None
    tab_target_id: str
    created_at: float = field(default_factory=time.time)
    _is_ephemeral: bool = field(default=True, repr=False)
    _scopes_path: Path | None = field(default=None, repr=False)


class ScopesRegistry:
    def __init__(self, path: Path):
        self._path = path

    def load(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, name: str, scope: SessionScope) -> None:
        data = self.load()
        data[name] = {
            "tab_target_id": scope.tab_target_id,
            "created_at": scope.created_at,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def remove(self, name: str) -> None:
        data = self.load()
        data.pop(name, None)
        if data:
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        elif self._path.exists():
            self._path.unlink()

    def get_tab_id(self, name: str) -> str | None:
        return self.load().get(name, {}).get("tab_target_id")


def acquire_scope(name: str | None, scopes_path: Path) -> SessionScope:
    if name is None:
        return SessionScope(
            name=None,
            tab_target_id=f"ephemeral-{uuid.uuid4()}",
            _is_ephemeral=True,
            _scopes_path=None,
        )

    registry = ScopesRegistry(scopes_path)
    raw = registry.load().get(name, {})
    existing_tab_id = raw.get("tab_target_id")

    if existing_tab_id:
        return SessionScope(
            name=name,
            tab_target_id=existing_tab_id,
            created_at=raw.get("created_at", time.time()),
            _is_ephemeral=False,
            _scopes_path=scopes_path,
        )

    scope = SessionScope(
        name=name,
        tab_target_id=f"named-{name}-{uuid.uuid4()}",
        _is_ephemeral=False,
        _scopes_path=scopes_path,
    )
    registry.save(name, scope)
    return scope


def release_scope(scope: SessionScope, keep: bool = False) -> None:
    if scope._is_ephemeral or scope.name is None:
        return

    if not keep and scope._scopes_path is not None:
        ScopesRegistry(scope._scopes_path).remove(scope.name)
