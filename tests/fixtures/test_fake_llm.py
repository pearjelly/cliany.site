import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from tests.fixtures.fake_llm import FakeChatModel


def test_responses_returned_in_order():
    model = FakeChatModel(responses=["first", "second", "third"])
    r1 = model.invoke([HumanMessage(content="hi")])
    r2 = model.invoke([HumanMessage(content="hi")])
    r3 = model.invoke([HumanMessage(content="hi")])
    assert r1.content == "first"
    assert r2.content == "second"
    assert r3.content == "third"


def test_last_response_repeated():
    model = FakeChatModel(responses=["a", "b"])
    model.invoke([HumanMessage(content="1")])
    model.invoke([HumanMessage(content="2")])
    r3 = model.invoke([HumanMessage(content="3")])
    r4 = model.invoke([HumanMessage(content="4")])
    assert r3.content == "b"
    assert r4.content == "b"


def test_ainvoke_returns_aimessage():
    model = FakeChatModel(responses=["test response"])
    result = asyncio.run(model.ainvoke([HumanMessage(content="hello")]))
    assert isinstance(result, AIMessage)
    assert result.content == "test response"


def test_single_response_always_returned():
    model = FakeChatModel(responses=["only one"])
    for _ in range(5):
        result = model.invoke([HumanMessage(content="hi")])
        assert result.content == "only one"
