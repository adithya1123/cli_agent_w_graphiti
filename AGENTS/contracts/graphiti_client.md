# Contracts: graphiti_client
_Last updated: 2026-04-25_
_Covers: `src/graphiti_client.py`_

---

## GraphitiMemoryClient.initialize

**Summary**: Creates OpenAI clients, constructs Graphiti instance, and awaits schema readiness.
**File**: `src/graphiti_client.py:39`

**Side effects**:
- Connects Neo4j driver (happens inside `Graphiti.__init__`)
- Calls `build_indices_and_constraints()` — blocks until Neo4j schema is confirmed ready
- Suppresses `"already exists"` errors from the schema call — safe to run on every startup

**Invariants**: Must be called before any other method. All other methods raise `RuntimeError("Graphiti not initialized")` if called before this.

**Env dependencies**:
- `OPENAI_API_KEY`, `OPENAI_API_ENDPOINT` (optional, for Azure)
- `OPENAI_EMBEDDING_API_KEY`, `OPENAI_EMBEDDING_ENDPOINT` (optional, separate resource)
- `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDING_MODEL`
- `GRAPHITI_LLM_MODEL` (optional — if unset, falls back to `OPENAI_CHAT_MODEL`)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

**Failure modes**:
- Neo4j unreachable → raises `ServiceUnavailable` from neo4j driver — means Docker is not running
- Bad API key → raises from OpenAI client construction
- `"Index initialization warning: ..."` (non-"already exists") → unexpected schema issue, check Neo4j logs

---

## GraphitiMemoryClient.add_episode

**Summary**: Stores a conversation turn as an Episodic node in the knowledge graph.
**File**: `src/graphiti_client.py:113`

**Non-obvious inputs**:
- `source`: Accepted values are `"text"`, `"json"`, `"md"` / `"markdown"`. Any other string defaults to `EpisodeType.text`. The agent always passes `"agent_conversation"` which maps to `text`.
- `group_id`: Must be passed for user isolation. Omitting it stores data without scoping — leaks across users.

**Side effects**:
- Creates `Episodic` node in Neo4j
- Triggers Graphiti's asynchronous entity extraction pipeline (LLM calls happen after this returns)

**Idempotency**: NOT SAFE — each call creates a new node. There is no deduplication.

**Failure modes**:
- Raises the original exception on any error (after logging it) — caller is responsible for retry

---

## GraphitiMemoryClient.search

**Summary**: Vector searches the knowledge graph for relevant memories.
**File**: `src/graphiti_client.py:157`

**Non-obvious inputs**:
- `user_id`: Must be passed as a positional/keyword argument. Internally passed as `group_ids=[user_id]` — the Graphiti API requires a list, not a string.

**Returns**: List of result objects from Graphiti (format varies by version — can be dicts or typed objects). Caller must handle both.

**Failure modes**:
- Raises on any exception (after logging)

→ See also: `01_hazards.md#graphiti-search-requires-group_ids-as-a-list`

---

## GraphitiMemoryClient.get_context_for_query

**Summary**: Search + format — returns a string ready for injection into the LLM system prompt.
**File**: `src/graphiti_client.py:214`

**Returns**:
- `"No relevant memories found."` when search returns empty results — not empty string
- `"Error retrieving memories."` on exception — never raises
- A multi-line string starting with `"Relevant memories:\n- ..."` on success

**Consumed by**: `MemoryAgent.process_message()` — result is further capped at 1200 chars there

**Produces**: Memory context string — injected into system prompt by MemoryAgent

→ See also: `02_business_logic.md#memory-context-retrieval`

---

## GraphitiMemoryClient.list_users

**Summary**: Queries Neo4j directly for all `group_id` values and their episode counts.
**File**: `src/graphiti_client.py:179`

**Returns**: `[{"user_id": str, "episode_count": int}, ...]` ordered by `episode_count DESC`. Returns `[]` if no users have data.

**Non-obvious behavior**: Queries `Episodic` nodes only. A user who has entities but no episodes (impossible in normal use) would not appear here.

**Failure modes**: Raises on Neo4j query error.

---

## GraphitiMemoryClient.delete_user

**Summary**: Permanently deletes all knowledge graph data for a user.
**File**: `src/graphiti_client.py:196`

**Returns**:
- `{"deleted": True, "episodes_removed": int}` on success
- `{"deleted": False, "reason": "User '{user_id}' not found in knowledge graph"}` if user doesn't exist

**Side effects**: Calls `clear_data(driver, group_ids=[user_id])` from `graphiti_core` — removes Episodic nodes, Entity nodes, and all edges scoped to the user.

**Idempotency**: SAFE — deleting a non-existent user returns `{"deleted": False}` without error.

**Failure modes**: Raises on Neo4j error after logging.

→ See also: `01_hazards.md#never-call-clear_data-without-scoping-to-group_ids`
