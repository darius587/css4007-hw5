import sqlite3

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict


class CheckpointState(TypedDict):
    messages: Annotated[list, add_messages]


def save_message(state):
    return {}


def create_graph(connection):
    builder = StateGraph(CheckpointState)
    builder.add_node("save_message", save_message)
    builder.add_edge(START, "save_message")
    builder.add_edge("save_message", END)

    return builder.compile(
        checkpointer=SqliteSaver(connection)
    )


def test_checkpoint_survives_restart(tmp_path):
    db_path = tmp_path / "checkpoints.sqlite"

    config = {
        "configurable": {
            "thread_id": "user-a:thread-1"
        }
    }

    with sqlite3.connect(db_path, check_same_thread=False) as connection:
        graph = create_graph(connection)

        graph.invoke({
            "messages": [
                HumanMessage(content="My Wi-Fi is not working")
            ]
        }, config=config)

    with sqlite3.connect(db_path, check_same_thread=False) as connection:
        graph = create_graph(connection)
        state = graph.get_state(config)

        assert len(state.values["messages"]) == 1
        assert (
            state.values["messages"][0].content
            == "My Wi-Fi is not working"
        )


def test_conversations_are_isolated(tmp_path):
    db_path = tmp_path / "checkpoints.sqlite"

    config_a = {
        "configurable": {
            "thread_id": "user-a:same-thread"
        }
    }

    config_b = {
        "configurable": {
            "thread_id": "user-b:same-thread"
        }
    }

    with sqlite3.connect(db_path, check_same_thread=False) as connection:
        graph = create_graph(connection)

        graph.invoke({
            "messages": [
                HumanMessage(content="Private Wi-Fi problem")
            ]
        }, config=config_a)

        graph.invoke({
            "messages": [
                HumanMessage(content="Password recovery problem")
            ]
        }, config=config_b)

    with sqlite3.connect(db_path, check_same_thread=False) as connection:
        graph = create_graph(connection)

        messages_a = graph.get_state(
            config_a
        ).values["messages"]

        messages_b = graph.get_state(
            config_b
        ).values["messages"]

        assert len(messages_a) == 1
        assert len(messages_b) == 1

        assert messages_a[0].content == "Private Wi-Fi problem"
        assert messages_b[0].content == "Password recovery problem"


def test_same_user_different_threads(tmp_path):
    db_path = tmp_path / "checkpoints.sqlite"

    config_1 = {
        "configurable": {
            "thread_id": "user-a:thread-1"
        }
    }

    config_2 = {
        "configurable": {
            "thread_id": "user-a:thread-2"
        }
    }

    with sqlite3.connect(db_path, check_same_thread=False) as connection:
        graph = create_graph(connection)

        graph.invoke({
            "messages": [
                HumanMessage(content="First conversation")
            ]
        }, config=config_1)

        graph.invoke({
            "messages": [
                HumanMessage(content="Second conversation")
            ]
        }, config=config_2)

        messages_1 = graph.get_state(
            config_1
        ).values["messages"]

        messages_2 = graph.get_state(
            config_2
        ).values["messages"]

        assert messages_1[0].content == "First conversation"
        assert messages_2[0].content == "Second conversation"
