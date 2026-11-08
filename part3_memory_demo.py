import sqlite3
import json
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "local-storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = STORAGE_DIR / "checkpoints.sqlite"
USER_DB_PATH = STORAGE_DIR / "user_memory.sqlite"


class MemoryState(TypedDict):
    messages: Annotated[list, add_messages]


def respond(state: MemoryState):
    messages = state["messages"]
    current_message = str(messages[-1].content)

    previous_requests = [
        str(message.content)
        for message in messages[:-1]
        if isinstance(message, HumanMessage)
        and "already tried that" not in str(message.content).lower()
    ]

    if "already tried that" in current_message.lower():
        if previous_requests:
            reply = (
                "I remember your previous request: "
                + previous_requests[-1]
            )
        else:
            reply = "Please tell me what you already tried."
    else:
        reply = "I received your request: " + current_message

    return {"messages": [("assistant", reply)]}


builder = StateGraph(MemoryState)
builder.add_node("respond", respond)
builder.add_edge(START, "respond")
builder.add_edge("respond", END)

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
        row = connection.execute("""
            SELECT language
            FROM user_preferences
            WHERE user_id = ?
        """, (user_id,)).fetchone()

    return row[0] if row else "English"


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
        check_same_thread=False
    )

    try:
        checkpointer = SqliteSaver(connection)
        graph = builder.compile(checkpointer=checkpointer)

        # Combine user ID and thread ID for conversation isolation.
        config = {
            "configurable": {
                "thread_id": f"{user_id}:{thread_id}"
            }
        }

        print("Helpdesk memory demo.")
        print("Commands: /language ru, /language en, exit")

        while True:
            user_input = input("You: ").strip()

            if user_input.lower() == "exit":
                break

            if not user_input:
                continue

            if user_input.lower() == "/language ru":
                save_language(user_id, "Russian")
                language = "Russian"
                print("Assistant: Language saved: Russian")
                continue

            if user_input.lower() == "/language en":
                save_language(user_id, "English")
                language = "English"
                print("Assistant: Language saved: English")
                continue

            result = graph.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )

            reply = str(result["messages"][-1].content)

            if language == "Russian":
                if reply.startswith("I remember your previous request: "):
                    previous = reply.removeprefix(
                        "I remember your previous request: "
                    )
                    reply = f"Я помню ваш предыдущий запрос: {previous}"
                elif reply.startswith("I received your request: "):
                    request = reply.removeprefix(
                        "I received your request: "
                    )
                    reply = f"Я получил ваш запрос: {request}"
                elif reply == "Please tell me what you already tried.":
                    reply = "Пожалуйста, расскажите, что вы уже пробовали."

            print("Assistant:", reply)

    finally:
        connection.close()

if __name__ == "__main__":
    main()
