# Business Logic Index
_Last updated: 2026-04-25_

Searchable index of functions that implement core behavioral rules in this codebase.
No domain-specific financial calculations exist — the key logic here is memory retrieval,
episode storage, search formatting, and user isolation.

---

## Memory Context Retrieval

**Function**: `GraphitiMemoryClient.get_context_for_query(query, user_id, num_results)`
**File**: `src/graphiti_client.py:214`
**Summary**: Searches the knowledge graph and returns a formatted string injected into the LLM system prompt.

**Formula / logic**:
Call Graphiti's vector search scoped to `group_ids=[user_id]`. Each result is a dict or object; extract `content`, `text`, or `name` field in that priority order, prefix with `"- "`. Join all parts with newlines under a `"Relevant memories:"` header.

**Non-obvious behavior**:
- Returns the literal string `"No relevant memories found."` (not empty string, not None) when no results exist
- Returns `"Error retrieving memories."` on exception — never raises to the caller
- Result is capped at 1200 characters in `MemoryAgent.process_message()` before injection into the system prompt
- The 15-second timeout on this call is applied in `process_message()`, not here

**Produces**: Memory context string — consumed by `MemoryAgent._get_ai_response()` as system prompt addendum

→ See also: `contracts/graphiti_client.md`, `01_hazards.md#graphiti-search`

---

## Episode Storage (Background Write)

**Function**: `MemoryAgent._store_episode_background(user_message, final_response)`
**File**: `src/agent.py:371`
**Summary**: Writes a conversation turn to the knowledge graph as an Episodic node. Runs fire-and-forget after the user receives their response.

**Formula / logic**:
Concatenate `"User: {user_message}\nAgent: {final_response}"` as the episode body.
Attempt `GraphitiMemoryClient.add_episode()` up to 3 times with exponential backoff (2s, 4s on attempts 2 and 3). On permanent failure, log error and silently discard — never surfaces to the user.

**Non-obvious behavior**:
- Never awaited inline — always scheduled via `asyncio.ensure_future()`
- Only fires if `self.memory_available = True`
- Error responses (strings starting with known prefixes in `_ERROR_PREFIXES`) are NOT stored — checked in `process_message()` before the fire-and-forget is scheduled
- Graphiti internally uses LLM calls to extract entities; these run asynchronously after `add_episode()` returns

**Produces**: `Episodic` node in Neo4j with `group_id=user_id`, `valid_at=now`

→ See also: `contracts/agent.md`, `01_hazards.md#never-await-episode-storage-inline`

---

## Search Result Formatting

**Function**: `WebSearchTool.format_search_results(response)`
**File**: `src/tools.py:66`
**Summary**: Converts raw Tavily API response into a text string for the LLM.

**Formula / logic**:
If `response` contains an `"answer"` key, prepend it with `"Answer: "` prefix. Then for each result, format as `"{idx}. {title}\n   URL: {url}\n   {content}\n"`. Content is capped at 300 characters per result to limit token usage.

**Non-obvious behavior**:
- Returns the literal string `"No results found"` when both answer and results are absent
- Returns `"Search error: {msg}"` when `"error"` key is present in response
- The agent calls with `max_results=3` — only 3 results are ever processed

**Produces**: Formatted search context string — consumed by `MemoryAgent._handle_tool_calls()` as a tool result message

→ See also: `contracts/tools.md`

---

## User Isolation

**Mechanism**: `group_id` field on every Neo4j node
**Enforced in**: `GraphitiMemoryClient.add_episode()`, `GraphitiMemoryClient.search()`, `GraphitiMemoryClient.delete_user()`

**Formula / logic**:
Every `add_episode()` call passes `group_id=user_id` to Graphiti. Every `search()` call passes `group_ids=[user_id]` (list form required by Graphiti's API). `delete_user()` calls `clear_data(driver, group_ids=[user_id])` from `graphiti_core`.

**Non-obvious behavior**:
- There is no user table or auth — isolation is purely a graph label filter
- A user with no episodes does not appear in `list_users()` results
- Deleting a user removes all their `Episodic` nodes, extracted `Entity` nodes, and edges — but only those scoped to their `group_id`

→ See also: `contracts/graphiti_client.md`, `01_hazards.md#never-write-to-neo4j-without-a-group_id`
