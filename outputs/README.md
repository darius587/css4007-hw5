# HW5 — Execution Logs and Results

This folder contains execution logs from the My LangGraph Helpdesk project.

## Part 1 — Deterministic Graph

- `part1_original_trace.txt` — Original graph execution before adding the clarification route.
- `part1_trace.txt` — Updated graph execution with the `clarify_problem` node.

## Part 2 — LLM and Tools

- `part2_normal_trace.txt` — Normal service status test.
- `part2_wifi_outage_trace.txt` — Wi-Fi outage test.
- `part2_status_unavailable_trace.txt` — Test with unavailable service status.
- `part2_ticket_trace.txt` — Local support ticket preparation test.
- `part2_tool_limit_trace.txt` — Tool execution limit test.
- `part2_tools_test.txt` — Tool testing output.
- `part2_final_trace.txt` — Additional Part 2 execution trace.

## Part 3 — Memory and Persistence

Part 3 uses SQLite to save conversation checkpoints and user language preferences.

Local database files are stored in the ignored `local-storage/` directory.

Memory persistence and user isolation were tested manually and with automated tests.

## Part 4 — Automated Tests

The project includes automated tests for:

- Graph routing and tool limits.
- User language preferences.
- Tool functionality.
- SQLite checkpoint persistence.
- User and thread isolation.

Run the tests with:

```powershell
python -m pytest tests/ -v
```

**Local test result: 21 passed.**

GitHub Actions also completed successfully.

## Notes

The logs in this folder are generated from project execution.

The project uses fictional helpdesk data. Local tickets are drafts and are not submitted to a real support system.

SQLite databases and other local runtime data are stored under `local-storage/` and are not committed to Git.