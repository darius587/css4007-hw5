from langchain_core.messages import AIMessage
from langgraph.graph import END

from part3 import (
    MAX_TOOL_ROUNDS,
    route_after_model,
    tool_limit,
)


def test_route_without_tools():
    state = {
        "messages": [AIMessage(content="Hello!")],
        "tool_rounds": 0,
    }

    assert route_after_model(state) == END


def test_route_with_tools():
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "find_instructions",
                "args": {"topic": "wifi"},
                "id": "call_1",
            }
        ],
    )

    state = {
        "messages": [message],
        "tool_rounds": 0,
    }

    assert route_after_model(state) == "tools"


def test_tool_limit_route():
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "check_service_status",
                "args": {"service": "wifi"},
                "id": "call_2",
            }
        ],
    )

    state = {
        "messages": [message],
        "tool_rounds": MAX_TOOL_ROUNDS,
    }

    assert route_after_model(state) == "tool_limit"


def test_tool_limit_response():
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "find_instructions",
                "args": {"topic": "wifi"},
                "id": "call_3",
            }
        ],
    )

    result = tool_limit({
        "messages": [message],
        "tool_rounds": MAX_TOOL_ROUNDS,
    })

    assert len(result["messages"]) == 2
    assert result["messages"][0].tool_call_id == "call_3"
    assert "limit" in result["messages"][1].content.lower()