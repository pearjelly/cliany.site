import ast
import importlib.util
import json

import pytest

from cliany_site.atoms.models import AtomCommand
from cliany_site.browser.selector import MAIN_RESULT_LIST_ROOT, MAIN_RESULT_LIST_SCOPE
from cliany_site.codegen import runtime_helpers
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.codegen.merger import AdapterMerger
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo


def result(scoped=False):
    target = {"role": "list", "name": "Package results", "attributes": {"id": "results"}, "suffix": ""}
    if scoped:
        target = {"role": "list", "name": "", "attributes": {}, "suffix": "", "scope": MAIN_RESULT_LIST_SCOPE}
    return ExploreResult(
        pages=[PageInfo("https://example.test/catalog", "Catalog")],
        actions=[
            ActionStep(
                "extract",
                "https://example.test/catalog",
                selector=MAIN_RESULT_LIST_ROOT if scoped else "#results",
                extract_mode="list",
                extract_target=target,
            )
        ],
        commands=[CommandSuggestion("search-packages", "Read packages", [], [0], expects_nonempty=False)],
    )


@pytest.mark.parametrize("scoped", [False, True])
def test_generator_persists_target_and_requires_supported_runtime(tmp_home, monkeypatch, scoped):
    explore = result(scoped)
    capability = "execute_scoped_extract_steps_via_atoms" if scoped else "execute_semantic_steps_via_atoms"
    code = AdapterGenerator().generate(explore, "example.test")
    ast.parse(code, feature_version=(3, 11))
    assert f"{capability} as execute_steps_via_atoms" in code
    assert '"extract_target"' in code
    save_adapter("example.test", code, explore_result=explore)
    folder = get_config().adapters_dir / "example.test"
    metadata = json.loads((folder / "metadata.json").read_text())
    assert metadata["commands"][0]["actions"][0]["extract_target"] == explore.actions[0].extract_target
    monkeypatch.delattr(runtime_helpers, capability)
    spec = importlib.util.spec_from_file_location("unsupported_semantic_adapter", folder / "commands.py")
    module = importlib.util.module_from_spec(spec)
    with pytest.raises(ImportError, match=capability):
        spec.loader.exec_module(module)


@pytest.mark.parametrize("scoped", [False, True])
def test_merge_keeps_semantic_identity_in_rebuilt_actions(tmp_home, scoped):
    explore = result(scoped)
    merger = AdapterMerger("example.test")
    merged = merger.merge_commands(existing=[], new_commands=explore.commands, new_actions=explore.actions)
    merger.save_merged(merged)
    metadata = json.loads((get_config().adapters_dir / "example.test" / "metadata.json").read_text())
    assert metadata["commands"][0]["actions"][0]["extract_target"] == explore.actions[0].extract_target
    assert metadata["commands"][0]["expects_nonempty"] is False
    rebuilt = merger._rebuild_explore_result(metadata["commands"])
    assert rebuilt.actions[0].extract_target == explore.actions[0].extract_target


def test_new_target_is_forwarded_but_legacy_atoms_keep_existing_arguments(monkeypatch):
    calls = []

    def run_atom(arguments, **kwargs):
        calls.append(arguments)
        return {"ok": True, "data": {}}

    monkeypatch.setattr(runtime_helpers, "run_atom", run_atom)
    step = {"type": "extract", "selector": "#results", "extract_mode": "list"}
    runtime_helpers._execute_single_step(step, "example.test")
    target = result().actions[0].extract_target
    runtime_helpers._execute_single_step({**step, "extract_target": target}, "example.test")
    assert "--target-json" not in calls[0]
    assert json.loads(calls[1][calls[1].index("--target-json") + 1]) == target


@pytest.mark.parametrize("scoped", [False, True])
def test_semantic_atom_exports_require_supported_action_runtime(tmp_home, monkeypatch, scoped):
    atom = AtomCommand(
        "semantic-atom",
        "read",
        "Read results",
        "example.test",
        [],
        [{"type": "extract", "extract_target": result(scoped).actions[0].extract_target}],
        "",
        "Read results",
    )
    monkeypatch.setattr("cliany_site.codegen.generator.load_atoms", lambda domain: [atom])
    generator = AdapterGenerator("example.test")
    generator.generate_with_atoms()
    code = (get_config().adapters_dir / "example.test" / "commands.py").read_text()
    ast.parse(code, feature_version=(3, 11))
    capability = "execute_scoped_extract_action_steps" if scoped else "execute_semantic_action_steps"
    assert f"{capability} as execute_action_steps" in code


@pytest.mark.parametrize("scoped", [False, True])
def test_reused_semantic_atom_requires_supported_runtime(tmp_home, monkeypatch, scoped):
    atom = AtomCommand(
        "semantic-atom",
        "read",
        "Read results",
        "example.test",
        [],
        [{"type": "extract", "extract_target": result(scoped).actions[0].extract_target}],
        "",
        "Read results",
    )
    monkeypatch.setattr("cliany_site.codegen.generator.load_atoms", lambda domain: [atom])
    explore = ExploreResult(
        actions=[ActionStep("reuse_atom", "https://example.test", target_ref="semantic-atom"), *result().actions],
        commands=[CommandSuggestion("read-packages", "Read packages", [], [0])],
    )
    code = AdapterGenerator().generate(explore, "example.test")
    capability = "execute_scoped_extract_steps_via_atoms" if scoped else "execute_semantic_steps_via_atoms"
    assert f"{capability} as execute_steps_via_atoms" in code
