import pytest

from cliany_site.codegen.params import build_param_overrides
from cliany_site.explorer.models import ActionStep


@pytest.mark.parametrize("index", [0, -1, 2, True, "1", None])
def test_explicit_invalid_index_cannot_fall_back_to_matching_default(index):
    actions = [ActionStep("type", "https://example.com", value="same") for _ in range(2)]
    with pytest.raises(ValueError, match="不属于当前命令"):
        build_param_overrides([{"name": "input", "action_index": index, "default": "same"}], [1], actions)


def test_owned_index_and_implicit_default_remain_supported():
    actions = [ActionStep("type", "https://example.com", value="same") for _ in range(2)]
    assert build_param_overrides([{"name": "input", "action_index": 1}], [1], actions) == {1: "{{input}}"}
    assert build_param_overrides([{"name": "input", "default": "same"}], [1], actions) == {1: "{{input}}"}
