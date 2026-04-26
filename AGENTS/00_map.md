# Codebase Map
_Last updated: 2026-04-25_

## Quick Reference
- **Stack**: Python 3.13+, AsyncOpenAI (v1.50+), Graphiti (`graphiti-core`), Neo4j 5.26, Tavily
- **Entry point**: `main.py` → `main()` → `SyncMemoryAgent` → `MemoryAgent`
- **Run**: `python main.py`
- **Start Neo4j**: `docker-compose up -d`
- **Test command**: No test suite — test scripts in root: `test_episode_simple.py`, `test_conversation.py`, `test_graphiti_simple.py`
- **Neo4j browser**: http://localhost:7474 (neo4j / password)

## Module Index

| Module | Path | Purpose | Key contracts |
|--------|------|---------|---------------|
| main (CLI) | `main.py` | REPL loop, command dispatch, user-switch | `→ contracts/main.md` |
| agent | `src/agent.py` | MemoryAgent (async) + SyncMemoryAgent (sync wrapper) | `→ contracts/agent.md` |
| graphiti_client | `src/graphiti_client.py` | GraphitiMemoryClient — Neo4j/Graphiti ops | `→ contracts/graphiti_client.md` |
| tools | `src/tools.py` | ToolRegistry + WebSearchTool (Tavily) | `→ contracts/tools.md` |
| config | `src/config.py` | Env var config classes; validates on startup | `→ contracts/config.md` |
| user_session | `src/user_session.py` | Persistent last-user storage in `~/.agent_memory/` | `→ contracts/user_session.md` |
| visualizer | `src/visualizer.py` | Interactive HTML knowledge graph (vis.js) | `→ contracts/visualizer.md` |

## Data Model Summary

Neo4j holds two node types: `Episodic` (one per conversation turn, carries `group_id = user_id` and `valid_at` timestamp) and `Entity` (named things extracted by Graphiti's LLM). Episodic nodes link to Entity nodes via `:MENTIONS` edges. Entity-to-Entity temporal relationships are stored as `:RELATES_TO` edges with `valid_at`/`invalid_at` fields. All user data is scoped by `group_id` — queries always filter on it. There are no foreign keys or explicit user-table; user identity exists only as a `group_id` label on graph nodes.

## Per-turn Flow

```
main.py input
  → SyncMemoryAgent.process_message()        [sync wrapper]
    → MemoryAgent.process_message()          [async]
      1. get_context_for_query()             [15s timeout, 3 results, cap 1200 chars]
      2. _get_ai_response()                  [routing call, max_tokens=4000]
      3. if tool_calls: _handle_tool_calls() [parallel tool exec, synthesis max_tokens=16000]
      4. return final_response
      5. background: _store_episode_background() [fire-and-forget, 3 attempts]
```

→ For hazards: `01_hazards.md`
→ For task playbooks: `playbooks/`
