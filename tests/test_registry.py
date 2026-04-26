import pytest
from cliany_site.registry import Registry, CommandEntry


def test_collect_empty():
    reg = Registry().collect([], [], [])
    assert reg.list() == []


def test_builtin_wins_over_adapter():
    reg = Registry().collect(
        builtin_names=["state"],
        atom_names=[],
        adapter_entries=[("state", "example.com")],
    )
    winner = reg.get("state")
    assert winner is not None
    assert winner.source == "builtin"
    assert not winner.is_conflict_loser


def test_adapter_loser_gets_qualified_name():
    reg = Registry().collect(
        builtin_names=["state"],
        atom_names=[],
        adapter_entries=[("state", "example.com")],
    )
    loser = reg.get("adapter:example.com.state")
    assert loser is not None
    assert loser.source == "adapter"
    assert loser.is_conflict_loser


def test_atom_wins_over_adapter():
    reg = Registry().collect(
        builtin_names=[],
        atom_names=["navigate"],
        adapter_entries=[("navigate", "example.com")],
    )
    winner = reg.get("navigate")
    assert winner.source == "atom"


def test_builtin_wins_over_atom():
    reg = Registry().collect(
        builtin_names=["doctor"],
        atom_names=["doctor"],
        adapter_entries=[],
    )
    winner = reg.get("doctor")
    assert winner.source == "builtin"


def test_conflict_reported():
    reg = Registry().collect(
        builtin_names=["state"],
        atom_names=[],
        adapter_entries=[("state", "example.com")],
    )
    assert len(reg.conflicts) == 1
    assert "registry conflict" in reg.conflicts[0]
    assert "adapter:example.com.state" in reg.conflicts[0]


def test_no_conflict_when_different_names():
    reg = Registry().collect(
        builtin_names=["doctor"],
        atom_names=["state"],
        adapter_entries=[("search", "example.com")],
    )
    assert reg.conflicts == []
    assert len(reg.list()) == 3


def test_list_by_source():
    reg = Registry().collect(
        builtin_names=["doctor", "list"],
        atom_names=["state"],
        adapter_entries=[("search", "example.com")],
    )
    builtins = reg.list(source="builtin")
    assert len(builtins) == 2
    atoms = reg.list(source="atom")
    assert len(atoms) == 1


def test_to_explain_dict_shape():
    reg = Registry().collect(
        builtin_names=["doctor"],
        atom_names=[],
        adapter_entries=[],
    )
    result = reg.to_explain_dict()
    assert "commands" in result
    assert "conflicts" in result
    assert isinstance(result["commands"], list)
    assert result["commands"][0]["name"] == "doctor"
    assert "source" in result["commands"][0]
