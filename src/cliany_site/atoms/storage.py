import dataclasses
import json
from pathlib import Path

from cliany_site.atoms.models import AtomCommand, AtomParameter


ADAPTERS_DIR = Path.home() / ".cliany-site" / "adapters"
_ACTION_FIELDS = (
    "action_type",
    "page_url",
    "target_url",
    "value",
    "description",
    "target_name",
    "target_role",
    "target_attributes",
)


def _safe_domain(domain: str) -> str:
    return domain.replace("/", "_").replace(":", "_")


def _atoms_dir(domain: str) -> Path:
    return ADAPTERS_DIR / _safe_domain(domain) / "atoms"


def _atom_path(domain: str, atom_id: str) -> Path:
    return _atoms_dir(domain) / f"{atom_id}.json"


def _sanitize_actions(actions: list[dict]) -> list[dict]:
    sanitized_actions: list[dict] = []
    for action in actions:
        if not isinstance(action, dict):
            continue

        cleaned: dict = {}
        if "action_type" in action:
            cleaned["action_type"] = action.get("action_type")
        elif "type" in action:
            cleaned["action_type"] = action.get("type")

        if "page_url" in action:
            cleaned["page_url"] = action.get("page_url")

        if "target_url" in action:
            cleaned["target_url"] = action.get("target_url")
        elif "url" in action:
            cleaned["target_url"] = action.get("url")

        for field_name in (
            "value",
            "description",
            "target_name",
            "target_role",
            "target_attributes",
        ):
            if field_name in action:
                cleaned[field_name] = action.get(field_name)

        if "target_attributes" in cleaned and not isinstance(
            cleaned["target_attributes"], dict
        ):
            cleaned["target_attributes"] = {}

        sanitized_actions.append(
            {k: cleaned[k] for k in _ACTION_FIELDS if k in cleaned}
        )

    return sanitized_actions


def _deserialize_atom(data: dict) -> AtomCommand:
    params_raw = data.get("parameters", [])
    parameters: list[AtomParameter] = []
    if isinstance(params_raw, list):
        for item in params_raw:
            if not isinstance(item, dict):
                continue
            parameters.append(
                AtomParameter(
                    name=str(item.get("name", "")),
                    description=str(item.get("description", "")),
                    default=str(item.get("default", "")),
                    required=bool(item.get("required", False)),
                )
            )

    actions_raw = data.get("actions", [])
    actions = _sanitize_actions(actions_raw) if isinstance(actions_raw, list) else []

    return AtomCommand(
        atom_id=str(data.get("atom_id", "")),
        name=str(data.get("name", "")),
        description=str(data.get("description", "")),
        domain=str(data.get("domain", "")),
        parameters=parameters,
        actions=actions,
        created_at=str(data.get("created_at", "")),
        source_workflow=str(data.get("source_workflow", "")),
    )


def save_atom(atom: AtomCommand) -> str:
    path = _atom_path(atom.domain, atom.atom_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = dataclasses.asdict(atom)
    payload["actions"] = _sanitize_actions(atom.actions)

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_atom(domain: str, atom_id: str) -> AtomCommand | None:
    path = _atom_path(domain, atom_id)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None

    if not isinstance(data, dict):
        return None
    return _deserialize_atom(data)


def load_atoms(domain: str) -> list[AtomCommand]:
    atoms_dir = _atoms_dir(domain)
    if not atoms_dir.exists():
        return []

    atoms: list[AtomCommand] = []
    for atom_file in sorted(atoms_dir.glob("*.json")):
        try:
            data = json.loads(atom_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            continue
        if isinstance(data, dict):
            atoms.append(_deserialize_atom(data))

    return atoms


def list_atoms(domain: str) -> list[dict]:
    atoms_dir = _atoms_dir(domain)
    if not atoms_dir.exists():
        return []

    lightweight_items: list[dict] = []
    for atom_file in sorted(atoms_dir.glob("*.json")):
        try:
            data = json.loads(atom_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            continue

        if not isinstance(data, dict):
            continue

        lightweight_items.append(
            {
                "atom_id": str(data.get("atom_id", atom_file.stem)),
                "name": str(data.get("name", "")),
                "description": str(data.get("description", "")),
                "domain": str(data.get("domain", domain)),
                "source_workflow": str(data.get("source_workflow", "")),
                "created_at": str(data.get("created_at", "")),
            }
        )

    return lightweight_items
