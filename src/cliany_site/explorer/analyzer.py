import dataclasses
import json
from datetime import datetime, timezone
from typing import Any

from cliany_site.atoms.models import AtomCommand, AtomParameter
from cliany_site.atoms.storage import load_atoms, save_atom
from cliany_site.explorer.engine import _parse_llm_response, _to_text
from cliany_site.explorer.models import ExploreResult
from cliany_site.explorer.prompts import (
    ATOM_EXTRACTION_PROMPT_TEMPLATE,
    ATOM_EXTRACTION_SYSTEM_PROMPT,
)


class AtomExtractor:
    def __init__(self, llm_client, domain: str):
        self._llm = llm_client
        self._domain = domain

    async def extract_atoms(self, explore_result: ExploreResult) -> list[AtomCommand]:
        existing_atoms = load_atoms(self._domain)
        existing_atom_ids = {atom.atom_id for atom in existing_atoms if atom.atom_id}

        existing_summaries = [
            {
                "atom_id": atom.atom_id,
                "name": atom.name,
                "description": atom.description,
            }
            for atom in existing_atoms
        ]

        workflow_name = self._derive_workflow_name(explore_result)
        actions_json = json.dumps(
            [dataclasses.asdict(action) for action in explore_result.actions],
            ensure_ascii=False,
            indent=2,
        )
        existing_atoms_json = json.dumps(
            existing_summaries,
            ensure_ascii=False,
            indent=2,
        )

        prompt_text = ATOM_EXTRACTION_PROMPT_TEMPLATE.format(
            actions_json=actions_json,
            existing_atoms=existing_atoms_json,
            workflow_name=workflow_name,
            domain=self._domain,
        )
        full_prompt = f"{ATOM_EXTRACTION_SYSTEM_PROMPT}\n\n{prompt_text}"

        try:
            response = await self._llm.ainvoke(full_prompt)
        except RuntimeError:
            return []

        try:
            response_text = self._response_to_text(response)
            parsed = _parse_llm_response(response_text)

            atoms_raw = parsed.get("atoms", [])
            if not isinstance(atoms_raw, list):
                return []

            new_atoms: list[AtomCommand] = []
            for atom_raw in atoms_raw:
                atom = self._to_atom(atom_raw, workflow_name)
                if atom is None:
                    continue
                if atom.atom_id in existing_atom_ids:
                    continue

                save_atom(atom)
                existing_atom_ids.add(atom.atom_id)
                new_atoms.append(atom)

            return new_atoms
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []

    def _derive_workflow_name(self, explore_result: ExploreResult) -> str:
        if explore_result.commands:
            first_command = explore_result.commands[0]
            if first_command.description:
                return first_command.description
            if first_command.name:
                return first_command.name
        return self._domain

    def _response_to_text(self, response: Any) -> str:
        if isinstance(response, str):
            return response
        if hasattr(response, "content"):
            return _to_text(getattr(response, "content"))
        return _to_text(response)

    def _to_atom(self, atom_raw: Any, workflow_name: str) -> AtomCommand | None:
        if not isinstance(atom_raw, dict):
            return None

        atom_id = str(atom_raw.get("atom_id", "") or "").strip()
        if not atom_id:
            return None

        params_raw = atom_raw.get("parameters", [])
        parameters: list[AtomParameter] = []
        if isinstance(params_raw, list):
            for item in params_raw:
                if not isinstance(item, dict):
                    continue
                parameters.append(
                    AtomParameter(
                        name=str(item.get("name", "") or ""),
                        description=str(item.get("description", "") or ""),
                        default=str(item.get("default", "") or ""),
                        required=bool(item.get("required", False)),
                    )
                )

        actions_raw = atom_raw.get("actions", [])
        actions = actions_raw if isinstance(actions_raw, list) else []

        return AtomCommand(
            atom_id=atom_id,
            name=str(atom_raw.get("name", "") or ""),
            description=str(atom_raw.get("description", "") or ""),
            domain=self._domain,
            parameters=parameters,
            actions=actions,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_workflow=workflow_name,
        )
