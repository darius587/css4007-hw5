import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    ToolMessage,
    AIMessage,
)
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tools import (
    find_instructions,
    check_service_status,
    prepare_ticket,
)

load_dotenv()

MAX_TOOL_ROUNDS = 5
STATUS_PROFILE = "normal"

tools = [
    find_instructions,
    check_service_status,
    prepare_ticket,
]

model = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0,
).bind_tools(tools)


class HelpdeskState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_rounds: int


def call_model(state: HelpdeskState):
    system_prompt = f"""
You are a university IT helpdesk assistant.

Use tools to answer Wi-Fi and password recovery questions.

Rules:
1. Use find_instructions for troubleshooting steps.
2. Use check_service_status to check service availability.
3. The current fictional status profile is "{STATUS_PROFILE}".
4. Never claim the status data is live.
5. Do not invent repair times.
6. Use prepare_ticket only when the user requests a ticket
   or troubleshooting has failed.
7. A ticket is a local draft, not a submitted support request.
8. Never request or store passwords, recovery codes, or API keys.
9. Do not invent tool results.
10. Reply clearly and briefly.

If a tool reports an error, explain the limitation.
"""

    response = model.invoke(
        [SystemMessage(content=system_prompt)]
        + state["messages"]
    )

    return {"messages": [response]}


def route_after_model(state: HelpdeskState):
    last_message = state["messages"][-1]

    if not last_message.tool_calls:
        return END

    if state["tool_rounds"] >= MAX_TOOL_ROUNDS:
        return "tool_limit"

    return "tools"


def execute_tools(state: HelpdeskState):
    tool_node = ToolNode(tools)
    result = tool_node.invoke(state)

    return {
        "messages": result["messages"],
        "tool_rounds": state["tool_rounds"] + 1,
    }



def tool_limit(state: HelpdeskState):
    last_message = state["messages"][-1]

    results = [
        ToolMessage(
            content="Tool execution limit reached. Tool was not executed.",
            tool_call_id=call["id"],
        )
        for call in last_message.tool_calls
    ]

    return {
        "messages": results + [
            AIMessage(
                content=(
                    "I reached the maximum number of tool rounds. "
                    "I cannot perform additional checks in this request."
                )
            )
        ]
    }



builder = StateGraph(HelpdeskState)

builder.add_node("model", call_model)
builder.add_node("tools", execute_tools)
builder.add_node("tool_limit", tool_limit)

builder.add_edge(START, "model")

builder.add_conditional_edges(
    "model",
    route_after_model,
    {
        "tools": "tools",
        "tool_limit": "tool_limit",
        END: END,
    },
)

builder.add_edge("tools", "model")
builder.add_edge("tool_limit", END)

graph = builder.compile()


if __name__ == "__main__":
    question = (
    "I cannot connect to campus Wi-Fi. "
    "I already checked that Wi-Fi is enabled and "
    "forgot and reconnected to the Campus-Demo network, "
    "but the problem remains. "
    "My demo user ID is student001 and "
    "my thread ID is thread001. "
    "Please prepare a local support ticket draft."
    )

    initial_state = {
        "messages": [HumanMessage(content=question)],
        "tool_rounds": 0,
    }

    result = graph.invoke(
        initial_state,
        config={"recursion_limit": 20},
    )

    print("\nUSER:", question)

    for message in result["messages"]:
        if getattr(message, "tool_calls", None):
            print("\nTOOL CALLS:", message.tool_calls)

        if isinstance(message, ToolMessage):
            print("\nTOOL RESULT:", message.content)

    print("\nFINAL ANSWER:")
    print(result["messages"][-1].content)
    print("\nTOOL ROUNDS:", result["tool_rounds"])
