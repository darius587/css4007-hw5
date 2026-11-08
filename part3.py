import os
import sqlite3
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode

from tools import find_instructions, check_service_status, prepare_ticket


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "local-storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = STORAGE_DIR / "checkpoints.sqlite"
USER_DB_PATH = STORAGE_DIR / "user_memory.sqlite"

load_dotenv(BASE_DIR / ".env")

MAX_TOOL_ROUNDS = 5

TOOLS = [
    find_instructions,
    check_service_status,
    prepare_ticket,
]

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0,
)

model = llm.bind_tools(TOOLS)
tool_node = ToolNode(TOOLS)


class MemoryState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_rounds: int


def initialize_user_memory():
    with sqlite3.connect(USER_DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                language TEXT NOT NULL
            )
        """)


def save_language(user_id: str, language: str):
    with sqlite3.connect(USER_DB_PATH) as connection:
        connection.execute("""
            INSERT INTO user_preferences (user_id, language)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET language = excluded.language
        """, (user_id, language))


def load_language(user_id: str) -> str:
    with sqlite3.connect(USER_DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT language
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return row[0] if row else "English"


def call_model(state: MemoryState, config):
    user_id = config["configurable"]["user_id"]
    thread_id = config["configurable"]["thread_id"]
    language = load_language(user_id)

    system_prompt = f"""
You are a university IT helpdesk assistant.

Help students solve university IT problems.
Use conversation history to understand follow-up questions.
Use tools to find instructions, check service status, and prepare tickets.

Use tools when the user asks for instructions or service status.
Do not invent service status or repair times.
Do not claim that a support ticket was submitted.
Tickets are local drafts only.
The helpdesk data is fictional.
Ask for missing information when necessary.
Do not share information from other users.

Current user ID: {user_id}
Current thread ID: {thread_id}

Preferred response language: {language}
Always respond in the preferred language.
"""

    response = model.invoke([
        SystemMessage(content=system_prompt),
        *state["messages"],
    ])

    return {"messages": [response]}


def execute_tools(state: MemoryState, config):
    result = tool_node.invoke(state, config=config)

    return {
        "messages": result["messages"],
        "tool_rounds": state.get("tool_rounds", 0) + 1,
    }


def route_after_model(state: MemoryState):
    last_message = state["messages"][-1]

    if not getattr(last_message, "tool_calls", None):
        return END

    if state.get("tool_rounds", 0) >= MAX_TOOL_ROUNDS:
        return "tool_limit"

    return "tools"


def tool_limit(state: MemoryState):
    last_message = state["messages"][-1]

    pending_results = [
        ToolMessage(
            content="Tool execution limit reached.",
            tool_call_id=call["id"],
        )
        for call in last_message.tool_calls
    ]

    return {
        "messages": [
            *pending_results,
            AIMessage(
                content=(
                    "The tool execution limit was reached. "
                    "I cannot perform additional checks."
                )
            ),
        ]
    }


builder = StateGraph(MemoryState)

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


def main():
    initialize_user_memory()

    user_id = input("User ID: ").strip()
    if not user_id:
        print("User ID cannot be empty.")
        return

    thread_id = input("Thread ID: ").strip()
    if not thread_id:
        print("Thread ID cannot be empty.")
        return

    language = load_language(user_id)
    print(f"Saved language: {language}")

    connection = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
    )

    try:
        checkpointer = SqliteSaver(connection)
        graph = builder.compile(checkpointer=checkpointer)

        # Keep each user's conversations separate
        config = {
            "configurable": {
                "thread_id": f"{user_id}:{thread_id}",
                "user_id": user_id,
            }
        }

        print("\nUniversity IT Helpdesk Assistant")
        print("Commands: /language ru, /language en, exit\n")

        while True:
            user_input = input("You: ").strip()

            if user_input.lower() == "exit":
                break

            if not user_input:
                continue

            if user_input.lower() == "/language ru":
                save_language(user_id, "Russian")
                language = "Russian"
                print("Language saved: Russian")
                continue

            if user_input.lower() == "/language en":
                save_language(user_id, "English")
                language = "English"
                print("Language saved: English")
                continue

            # Check how many messages were already saved
            previous_state = graph.get_state(config)
            previous_count = len(
                previous_state.values.get("messages", [])
            )

            result = graph.invoke(
                {
                    "messages": [HumanMessage(content=user_input)],
                    "tool_rounds": 0,
                },
                config=config,
            )

            # Show only the tools used for this message
            new_messages = result["messages"][previous_count:]

            for message in new_messages:
                if isinstance(message, AIMessage):
                    for call in message.tool_calls:
                        print(f"[TOOL CALL] {call['name']}")

            print(f"[TOOL ROUNDS] {result.get('tool_rounds', 0)}")

            final_answer = result["messages"][-1].content
            print("\nAssistant:", final_answer)
            print()

    finally:
        connection.close()


if __name__ == "__main__":
    main()
