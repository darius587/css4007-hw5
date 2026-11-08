import json
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# Load instructions from the supplied JSON file
DATA_PATH = Path(__file__).parent / "data" / "helpdesk.json"

with open(DATA_PATH, "r", encoding="utf-8") as file:
    helpdesk_data = json.load(file)


# Graph state
class HelpdeskState(TypedDict):
    message: str
    category: str
    reply: str


# Node 1: classify the request
def read_request(state: HelpdeskState):
    message = state["message"].lower()

    has_wifi = "wifi" in message or "wi-fi" in message
    has_password = "password" in message

    if has_wifi and has_password:
        category = "clarify"
    elif has_wifi:
        category = "wifi"
    elif has_password:
        category = "password"
    else:
        category = "other"

    return {"category": category}

# Conditional routing
def choose_next_node(state: HelpdeskState):
    return state["category"]


# Wi-Fi help node
def wifi_help(state: HelpdeskState):
    instructions = helpdesk_data["instructions"]["wifi"]

    reply = instructions["title"] + "\n"
    for step in instructions["steps"]:
        reply += "- " + step + "\n"

    return {"reply": reply}


# Password help node
def password_help(state: HelpdeskState):
    instructions = helpdesk_data["instructions"]["password"]

    reply = instructions["title"] + "\n"
    for step in instructions["steps"]:
        reply += "- " + step + "\n"

    return {"reply": reply}


# Other questions
def other_help(state: HelpdeskState):
    return {
        "reply": "Is your problem related to Wi-Fi or password?"
    }

def clarify_problem(state: HelpdeskState):
    return {
        "reply": (
            "Your message mentions both Wi-Fi and password. "
            "Which problem would you like to solve first?"
        )
    }


# Build LangGraph
builder = StateGraph(HelpdeskState)

builder.add_node("read_request", read_request)
builder.add_node("wifi_help", wifi_help)
builder.add_node("password_help", password_help)
builder.add_node("other_help", other_help)
builder.add_node("clarify_problem", clarify_problem)

builder.add_edge(START, "read_request")


builder.add_conditional_edges(
    "read_request",
    choose_next_node,
    {
        "wifi": "wifi_help",
        "password": "password_help",
        "other": "other_help",
        "clarify": "clarify_problem",
    },
)


builder.add_edge("wifi_help", END)
builder.add_edge("password_help", END)
builder.add_edge("other_help", END)
builder.add_edge("clarify_problem", END)

graph = builder.compile()


# Test messages
test_messages = [
    "I cannot connect to Wi-Fi.",
    "I forgot my PASSWORD.",
    "My laptop screen is broken.",
    "My Wi-Fi password does not work.",
]



for message in test_messages:
    print("\n" + "=" * 60)
    print("USER:", message)

    initial_state = {
        "message": message,
        "category": "",
        "reply": "",
    }

    current_state = initial_state.copy()

    for event in graph.stream(initial_state):
        for node_name, update in event.items():
            current_state.update(update)

            print("NODE:", node_name)
            print("NODE UPDATE:", update)
            print("STATE AFTER NODE:", current_state.copy())

    result = current_state

    print("CATEGORY:", result["category"])
    print("REPLY:\n", result["reply"])
