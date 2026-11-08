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

### 1. Model and provider

I used **Claude through OpenRouter** with LangChain and LangGraph.

- Provider: OpenRouter
- Model ID: `anthropic/claude-haiku-5.5`
- Adapter: `ChatOpenAI`
- API base URL: `https://openrouter.ai/api/v1`

The API key is stored in `.env` and is not uploaded to GitHub.

### 2. Model and tool loop

The LangGraph workflow is:

```text
START
  |
  v
model
  |
  +-- No tool calls --------> END
  |
  +-- Tool calls
         |
         v
       tools
         |
         v
       model
         |
         +-- Final answer --> END

If tool limit is reached:
model --> tool_limit --> END
```

The model decides which tools to call. LangGraph executes the tools and returns the results to the model. The model can then generate a final answer or request another tool.

### 3. Three tools

I implemented three reusable tools in `tools.py`.

**`find_instructions`**

Reads `data/helpdesk.json` and returns Wi-Fi or password recovery instructions.

**`check_service_status`**

Reads `data/service_status.json` and returns fictional service status information. It supports normal, outage, and unknown status scenarios.

**`prepare_ticket`**

Creates a local support ticket draft using `data/ticket_template.json`. The ticket is saved in `local-storage/tickets/` as JSON. It is not submitted to a real helpdesk.

### 4. Direct tool calls

I tested the tools directly using `test_tools_manual.py`.

Examples:

```python
find_instructions.invoke({"topic": "wifi"})

check_service_status.invoke({
    "service": "wifi",
    "profile": "normal"
})

prepare_ticket.invoke({
    "user_id": "demo-user-a",
    "thread_id": "demo-thread-1",
    "category": "wifi",
    "summary": "Wi-Fi does not connect",
    "steps_tried": ["Checked Wi-Fi settings"],
    "service_status": "operational",
    "status_profile": "normal",
    "reference_ids": ["GUIDE-WIFI"]
})
```

The tools returned troubleshooting instructions, service status information, and a ticket draft.

Evidence: `outputs/part2_tools_test.txt`.

### 5. Actual model run with multiple tools

I tested this request:

"I cannot connect to campus Wi-Fi. Please give me troubleshooting instructions and check the service status."

Claude called two tools:

1. `find_instructions`
2. `check_service_status`

The first tool returned the Campus-Demo Wi-Fi instructions and reference ID `GUIDE-WIFI`.

The second tool returned `status: operational` for the `normal` profile.

Claude used both results to provide troubleshooting steps and explain that the service status was fictional, not live.

The execution finished in **one tool round**.

Evidence: `outputs/part2_normal_trace.txt`.

I also tested an outage, an unavailable status source, and ticket creation. The results are saved in the `outputs/` directory.

### 6. Loop limit

I used `MAX_TOOL_ROUNDS = 5` to prevent unlimited tool execution.

When the limit is reached, LangGraph routes execution to `tool_limit` instead of executing more tools.

To test this, I temporarily set `MAX_TOOL_ROUNDS = 0`.

Claude requested a tool, but the tool was not executed. The graph returned:

"Tool execution limit reached."

The execution finished with `TOOL ROUNDS: 0`.

After testing, I restored the limit to five rounds.

Evidence: `outputs/part2_tool_limit_trace.txt`.

### 7. Answers to the four questions

**Q1. How does the model decide which tool to use?**

The model reads the user's request and selects a tool based on its name, description, and arguments. LangGraph then executes the selected tool.

**Q2. Why are the tools implemented separately from the model?**

The tools contain reusable Python functions that read local data and prepare ticket drafts. This separates data operations from language generation and allows the tools to be tested without an LLM.

**Q3. How does the model use results from multiple tools?**

The tool results are returned to the model as messages. The model uses these results to produce one combined answer. For example, it combines Wi-Fi troubleshooting instructions with service status information.

**Q4. Why is a loop limit necessary?**

The model may request additional tools repeatedly. A loop limit prevents unlimited execution, excessive API requests, and unnecessary costs. My graph stops further tool execution when the limit is reached.

### 8. Limitations

The service status data is fictional and does not represent real university systems.

Ticket drafts are stored locally and are not submitted automatically.

The model may choose different tool calls between runs, but the tools use the provided JSON data.

## Part 3 — Memory

### Conversation state

I added memory to my helpdesk in `part3.py`.

The graph stores conversation messages using LangGraph `SqliteSaver`.

The conversation history is saved in:

`local-storage/checkpoints.sqlite`

I use two identifiers:

- `user_id` identifies the user.
- `thread_id` identifies the conversation.

The application combines them into one checkpoint identifier:

```python
thread_id = f"{user_id}:{thread_id}"
```

This allows different users and conversations to have separate histories.

### User preferences

I store language preferences in:

`local-storage/user_memory.sqlite`

Users can select English or Russian:

```text
/language en
/language ru
```

The language preference is saved by `user_id`.

When the same user starts a new conversation, the preferred language remains the same, but the previous conversation messages are not copied.

### Retrieval

Helpdesk instructions are stored in `data/helpdesk.json`.

The `find_instructions` tool reads this file when the assistant needs Wi-Fi or password recovery instructions.

This means that helpdesk knowledge is stored separately from conversation history.

### Memory experiments

| Situation | Command used | Log file | What happened |
|---|---|---|---|
| Refer to an earlier message | Run `python part3.py`, send a Wi-Fi problem, then ask a follow-up in the same thread | Interactive Part 3 test | The assistant used the earlier Wi-Fi problem as context. |
| Close, restart and resume | Restart `python part3.py` with the same user ID and thread ID | SQLite checkpoint database | The previous conversation was available after restart. |
| Same user, new conversation | Start a new thread with the same user ID after `/language ru` | SQLite user memory database | Russian preference remained, but the old conversation was not replayed. |
| Different user | Start another user with the same thread name | S13 interactive test | The second user did not receive the first user's history or language preference. |

---

## Part 4 — Running and checking my work

### Setup

The project uses Python 3.13, LangGraph, LangChain, SQLite, pytest, and OpenRouter.

Setup instructions are provided in `README.md`.

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

Configure the OpenRouter API key in `.env` using `.env.example`.

Run each part:

```bash
python part1.py
python part2.py
python part3.py
```

Part 1 works without an API key.

Parts 2 and 3 use Claude through OpenRouter.

### Automated tests

I created four test files:

| Test file | Tests | What the tests check |
|---|---:|---|
| `tests/test_graph.py` | 4 | Graph routing and tool execution limits |
| `tests/test_memory.py` | 5 | Default language, saving, updating, user isolation, and persistence |
| `tests/test_tools.py` | 9 | Instructions, service status, invalid inputs, and local ticket drafts |
| `tests/test_checkpoints.py` | 3 | Checkpoint persistence and conversation isolation |
| **Total** | **21** | **All passed** |

I ran:

```bash
python -m pytest tests/ -v
```

Result:

```text
21 passed
```

### What mistakes the tests catch

The graph tests detect incorrect routing and problems with the tool execution limit.

The memory tests detect incorrect language preferences, missing persistence, and sharing preferences between users.

The tool tests detect unsupported topics, invalid service profiles, incorrect status results, and ticket creation without required information.

The checkpoint tests detect lost conversation history after reopening SQLite and accidental sharing of messages between users or threads.

### Tests without a real model

The automated tests do not call the real Claude model.

They test graph logic, local tools, SQLite memory, and deterministic behavior.

The checkpoint tests use a small test graph instead of the real model.

This makes testing faster and avoids API costs.

I also performed manual experiments using the real model through OpenRouter.

### GitHub Actions

I created a GitHub Actions workflow:

`.github/workflows/tests.yml`

It uses Python 3.13, installs dependencies, and runs pytest.

The workflow uses a dummy API key because the automated tests do not need real model requests.

The earlier workflow run passed. The final workflow should be checked again after pushing the new tests.

### Memory reset

The application stores local data in:

- `local-storage/checkpoints.sqlite` — conversation history.
- `local-storage/user_memory.sqlite` — language preferences.
- `local-storage/tickets/` — local ticket drafts.

To reset memory, I can stop the application and delete the relevant SQLite database files.

The application creates the required storage again when it runs.

The `.env` file and local storage should not be uploaded to GitHub.

---

## Choices and limitations

### My choices

I chose LangGraph because it supports nodes, conditional edges, shared state, and checkpoint memory.

I chose OpenRouter because it provides access to Claude using an OpenAI-compatible API.

I chose SQLite because it is simple and does not require a separate database server.

I chose JSON files because they are easy to read, edit, and test.

I used pytest because it allows me to check the application automatically.

I set `MAX_TOOL_ROUNDS = 5` to prevent unlimited tool execution and unnecessary API requests.

### Limitations

- Service statuses are fictional, not live university data.
- Tickets are saved locally and are not sent to a real support system.
- The model may choose different tool calls between runs.
- The application requires an API connection for Parts 2 and 3.
- Conversation memory is stored locally.
- The application does not implement real user authentication.
- Only Wi-Fi and password recovery instructions are supported.

---

## Supplied scenarios — my actual results

| Scenario | Command or manual steps | Log file | What happened / what I changed |
|---|---|---|---|
| S01 — Simple Wi-Fi route | Run `python part1.py` with a Wi-Fi request | `outputs/part1_original_trace.txt` | The graph selected `wifi_help`. |
| S02 — Case-insensitive password route | Test "I forgot my PASSWORD" | `outputs/part1_original_trace.txt` | The graph selected `password_help`. |
| S03 — Unsupported request | Test "My laptop screen is broken" | `outputs/part1_original_trace.txt` | The graph selected `other_help`. |
| S04 — Two topics before the graph change | Test "My Wi-Fi password does not work" | `outputs/part1_original_trace.txt` | The original graph selected `wifi_help`. |
| S05 — Two topics after clarification | Repeat the same request using the updated graph | `outputs/part1_trace.txt` | The graph selected `clarify_problem` and asked which problem to solve first. |
| S06 — Instructions then local ticket | Run Part 2 with troubleshooting and ticket creation | `outputs/part2_ticket_trace.txt` | The assistant used helpdesk tools and prepared a local ticket draft. |
| S07 — Wi-Fi outage | Run Part 2 with the `wifi_outage` profile | `outputs/part2_wifi_outage_trace.txt` | The assistant checked the Wi-Fi outage status. |
| S08 — Status source unavailable | Run Part 2 with the `status_unavailable` profile | `outputs/part2_status_unavailable_trace.txt` | The assistant handled unavailable status information. |
| S09 — Missing ticket details | Run Part 3 and request a ticket without enough details | Manual test; no saved log | The assistant requested missing details instead of inventing them. |
| S10 — Use the current conversation | Ask a Wi-Fi question and a follow-up in the same thread | Manual test; no saved log | The assistant used earlier conversation context. |
| S11 — Persist and recall after restart | Restart Part 3 with the same user ID and thread ID | `tests/test_checkpoints.py` | SQLite checkpoint persistence was verified. |
| S12 — Preference across threads without replay | Set `/language ru` and start a new thread | `tests/test_memory.py`; manual test | The language preference remained while conversation histories stayed separate. |
| S13 — Do not share memory between users | Test two users with the same thread name | `tests/test_checkpoints.py`; manual test | User histories remained isolated. |
| S14 — Password recovery outage | Check password recovery with the `recovery_outage` profile | Manual test; no saved log | The assistant detected the outage and updated its answer. |

### Important scenario observations

**S09 — Missing ticket details**

I asked the assistant to create a ticket without enough information.

The assistant checked the helpdesk information and requested missing details.

It did not create a ticket with invented information.

**S13 — User isolation**

User A selected Russian and discussed a Wi-Fi problem.

User B used the same thread name but a different user ID.

User B received an English response and could not access User A's conversation history.

**S14 — Password recovery outage**

I first checked password recovery under normal conditions.

Then I asked the assistant to check the recovery outage profile.

The assistant called `check_service_status`, detected the outage, and updated its response.

### Conclusion

I created a university IT helpdesk using LangGraph.

In Part 1, I implemented deterministic routing and added a clarification node.

In Part 2, I connected Claude through OpenRouter and created three helpdesk tools.

In Part 3, I added SQLite conversation checkpoints and persistent language preferences.

In Part 4, I tested the graph, tools, memory, and conversation isolation.

All 21 automated tests passed locally.

The project demonstrates how LangGraph can combine graph workflows, language models, tools, and persistent memory.