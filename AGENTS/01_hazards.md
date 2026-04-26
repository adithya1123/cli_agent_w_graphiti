# Hazard Map
_Last updated: 2026-04-25_

## 🔴 NEVER

### Never reintroduce lazy Graphiti initialization
**What**: Do not move `memory_client.initialize()` out of `SyncMemoryAgent.__init__` and into `process_message()`.
**Instead**: Keep the eager `self._loop.run_until_complete(self._async_agent.memory_client.initialize())` in `SyncMemoryAgent.__init__`.
**Why it matters**: All CLI commands (`users`, `delete user`, `visualize`) call the memory client. If initialization is deferred to `process_message`, those commands crash with "Graphiti not initialized" until the user sends a chat message first.

### Never await episode storage inline
**What**: Do not `await _store_episode_background()` directly in `process_message()`.
**Instead**: Use `asyncio.ensure_future(...)` to fire-and-forget.
**Why it matters**: Graphiti's LLM entity-extraction calls can take several seconds. Blocking the user turn on them adds perceptible latency and competes with the next turn for rate-limit quota.

### Never use `tool_choice="auto"` on the synthesis LLM call
**What**: The synthesis call in `_handle_tool_calls()` must use `tool_choice="none"`.
**Instead**: Keep `tool_choice="none"` on that call.
**Why it matters**: Reasoning/o-series models will re-invoke tools on the synthesis call, returning `content=None` and causing a blank response to the user.

### Never write to Neo4j without a `group_id`
**What**: `add_episode()` without `group_id` stores data globally, leaking across users.
**Instead**: Always pass `group_id=self.user_id` when calling `add_episode()`.
**Why it matters**: User isolation is enforced entirely by `group_id` labels in Neo4j — there is no other access control.

### Never call `clear_data()` without scoping to `group_ids`
**What**: `graphiti_core.utils.maintenance.graph_data_operations.clear_data(driver)` with no `group_ids` deletes ALL data in the graph.
**Instead**: Always call `clear_data(driver, group_ids=[user_id])`.
**Why it matters**: Unscoped deletion is irreversible and wipes every user's memory.

---

## 🟡 CAUTION

### max_completion_tokens on the synthesis call must be large
**Where**: `_handle_tool_calls()` in `src/agent.py`
**Detail**: `max_completion_tokens=16000` is intentional. Reasoning models consume tokens on internal reasoning steps. Setting this to 4000 or lower can produce empty responses when the model's reasoning overhead fills the budget before any content is generated.

### Graphiti `search()` requires `group_ids` as a list, not a plain string
**Where**: `GraphitiMemoryClient.search()` in `src/graphiti_client.py`
**Detail**: Graphiti's API parameter is `group_ids=[user_id]` (plural, list). Passing a plain string silently returns all-user results or raises a type error depending on the version.

### Conversation history is NOT included in the tool-synthesis call
**Where**: `_handle_tool_calls()` in `src/agent.py`
**Detail**: The message list built for the synthesis call contains only `system + user_turn + tool_results`. This is intentional — tool results are usually self-contained. Do not add full history there; it inflates token usage and can confuse reasoning models.

### `GRAPHITI_LLM_MODEL` must be set when using reasoning/o-series chat models
**Where**: `src/config.py`, `src/graphiti_client.py`
**Detail**: Graphiti requires structured JSON outputs for entity extraction. O-series/reasoning models may not support that mode. When `OPENAI_CHAT_MODEL` is a reasoning model, set `GRAPHITI_LLM_MODEL` to a standard model (e.g. `gpt-4o-mini`) for Graphiti's internal calls.

### `GraphitiMemory` (sync wrapper) is not used by the main agent
**Where**: `src/graphiti_client.py`
**Detail**: `GraphitiMemory` is a legacy synchronous wrapper. The live code path uses `GraphitiMemoryClient` (async) directly from `MemoryAgent`. `GraphitiMemory` is imported by `agent.py` but not instantiated at runtime. Do not add logic to it expecting the agent to pick it up.

### Visualizer uses a separate direct Neo4j driver, not Graphiti
**Where**: `src/visualizer.py`
**Detail**: `GraphVisualizer` opens its own `neo4j.GraphDatabase.driver` connection. It does not reuse the Graphiti client's driver. If the Graphiti schema changes (node labels, property names), the visualizer's Cypher queries must be updated separately.

---

## ⚪ CONVENTION

### New CLI commands go before the `else` block in `main()`
**Where**: `main.py`
**Detail**: Commands are dispatched via `str.lower().startswith()` checks in order. Add new blocks before the final `else` (message processing). Also update `print_welcome()` and `print_help()`.

### Error responses are never added to conversation history
**Where**: `MemoryAgent.process_message()` in `src/agent.py`
**Detail**: Responses that start with known error prefixes (defined in `_ERROR_PREFIXES`) are not appended to `self.conversation_history`. This prevents error strings from poisoning the context window.

### User IDs are validated to `^[a-zA-Z0-9_\-]{1,50}$`
**Where**: `UserSessionManager.validate_user_id()` in `src/user_session.py`
**Detail**: The validation pattern is also the implicit contract for all `group_id` values written to Neo4j. Do not bypass it.
