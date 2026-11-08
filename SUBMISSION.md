# HW5 — My LangGraph helpdesk

## Part 1 — How the graph works

### My graph and state

I created a simple university IT helpdesk using LangGraph without an LLM. The graph reads a user message, identifies the problem, and returns instructions from `data/helpdesk.json`.

**Original graph:**

```text
START
  |
read_request
  |
  +-- wifi_help ------> END
  |
  +-- password_help --> END
  |
  +-- other_help -----> END
```

The graph uses three state fields:

| Field | Description |
| --- | --- |
| `message` | The original user message |
| `category` | The detected problem category |
| `reply` | The final helpdesk response |

**What each node reads and changes:**

- `read_request` reads `message` and updates `category`.
- `wifi_help` reads the Wi-Fi instructions from `data/helpdesk.json` and updates `reply`.
- `password_help` reads the password instructions from `data/helpdesk.json` and updates `reply`.
- `other_help` updates `reply` with a question about Wi-Fi or password.

**Answers to the four questions:**

1. Each node reads the current state and returns an update. The `read_request` node changes the category, while help nodes change the reply.
2. A node updates the state, while a conditional edge chooses which node runs next based on the category.
3. The next node receives the current graph state, not only the previous node's update.
4. `START` is the entry point, `END` finishes execution, and `compile()` creates an executable graph.

### Predictions before running

| Message | Predicted route | Actual route | What I learned |
| --- | --- | --- | --- |
| I cannot connect to Wi-Fi. | wifi_help | wifi_help | Wi-Fi keywords are detected. |
| I forgot my PASSWORD. | password_help | password_help | Routing ignores uppercase and lowercase differences. |
| My laptop screen is broken. | other_help | other_help | Unsupported problems go to other_help. |
| My Wi-Fi password does not work. | wifi_help | wifi_help | Wi-Fi has priority when both topics appear. |

All four predictions matched the original graph results.

The original routing checks for Wi-Fi first. Therefore, a message containing both Wi-Fi and password goes to `wifi_help`.

The original execution results are saved in `outputs/part1_original_trace.txt`.

### My change to the graph

I added a new node called `clarify_problem`.

When a message contains both Wi-Fi and password, the graph asks the user which problem they want to solve first.

**Updated graph:**

```text
START
  |
read_request
  |
  +-- wifi_help --------> END
  |
  +-- password_help ----> END
  |
  +-- other_help -------> END
  |
  +-- clarify_problem --> END
```

**Updated execution trace:**

```text
USER: My Wi-Fi password does not work.

NODE: read_request
NODE UPDATE: {'category': 'clarify'}

NODE: clarify_problem
NODE UPDATE: {'reply': 'Your message mentions both Wi-Fi and password. Which problem would you like to solve first?'}

CATEGORY: clarify
END
```

Before the change, the message went to `wifi_help`. After the change, it goes to `clarify_problem`.

The other three messages still follow their original routes.

**What LangGraph controls:**

LangGraph controls the execution order, conditional edges, state passing, and graph termination.

**What my Python functions decide:**

My functions detect keywords, select categories, and generate replies using the local helpdesk data.

No LLM or API key is used in Part 1.

**Saved execution logs:**

- `outputs/part1_original_trace.txt` — original graph results.
- `outputs/part1_trace.txt` — updated graph results, including state after each node.

## Part 2 — Model and tools

TODO: draw the model/tool loop. Answer the four questions in the brief. Record the model and provider, direct calls to each tool, and one actual run that uses multiple tools. Explain the loop limit.

## Part 3 — Memory

TODO: explain conversation state, thread_id, user identifier, user preference storage, and retrieval from helpdesk.json.

| Situation | Command used | Log file | What happened |
| --- | --- | --- | --- |
| Refer to an earlier message | | | |
| Close, restart and resume | | | |
| Same user, new conversation | | | |
| Different user | | | |

## Part 4 — Running and checking my work

TODO: point to the README setup steps, package versions, memory-reset instructions, tests and GitHub Actions workflow. Explain which mistake each test catches and which runs use a fake model.

## Choices and limitations

TODO: explain the storage and libraries I chose, why they fit this task, and what still does not work reliably.

## Supplied scenarios — my actual results

| Scenario | Command or manual steps | Log file | What happened / what I changed |
| --- | --- | --- | --- |
| S01 — Simple Wi-Fi route | | | |
| S02 — Case-insensitive password route | | | |
| S03 — Unsupported request | | | |
| S04 — Two topics before the graph change | | | |
| S05 — Two topics after adding clarification | | | |
| S06 — Instructions then local ticket | | | |
| S07 — The same request during a Wi-Fi outage | | | |
| S08 — Status source unavailable | | | |
| S09 — Missing ticket details | | | |
| S10 — Use the current conversation | | | |
| S11 — Persist and recall after restart | | | |
| S12 — Preference across threads without replay | | | |
| S13 — Do not share memory between users | | | |
| S14 — Password recovery outage | | | |
