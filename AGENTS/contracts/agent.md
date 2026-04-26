# Contracts: agent
_Last updated: 2026-04-25_
_Covers: `src/agent.py`_

---

## MemoryAgent.__init__

**Summary**: Initializes the async agent — creates OpenAI client, configures memory client, initializes tool registry.
**File**: `src/agent.py:32`

**Non-obvious inputs**:
- `loop`: Passed from `SyncMemoryAgent` but not stored on `MemoryAgent` — only used to signal intent. The actual event loop management is in `SyncMemoryAgent`.

**Side effects**:
- Creates `AsyncOpenAI` client with optional `base_url` for Azure
- Sets `self.memory_available = True` (memory failures are non-fatal here — `initialize()` may still fail later)

**Failure modes**:
- `RuntimeError("Cannot initialize LLM client: ...")` → bad OpenAI config
- `RuntimeError("Cannot initialize tools: ...")` → Tavily init failed

---

## MemoryAgent.process_message

**Summary**: Main turn handler — retrieves memory, calls LLM, optionally calls tools, stores episode.
**File**: `src/agent.py:275`

**Non-obvious inputs**:
- Empty or whitespace-only input returns `"Please provide a message."` immediately without any LLM call.

**Returns**:
- Always returns a non-empty string
- Returns an error-prefix string (e.g. `"Connection error: ..."`) on LLM failure — these are NOT added to conversation history

**Side effects**:
- Appends `user_message` + `final_response` to `self.conversation_history` (unless response is an error string)
- Fires `_store_episode_background()` via `asyncio.ensure_future()` — does not wait for it

**Consumed by**: `SyncMemoryAgent.process_message()` via `run_until_complete()`

**Failure modes**:
- Memory timeout (15s) → silently continues with empty context, logs warning
- Tool timeout (30s) → returns `"Web search timed out."` as the tool result, LLM synthesizes from that
- LLM API errors → returns an error-prefix string, does not raise

---

## MemoryAgent._get_ai_response

**Summary**: Routing LLM call — decides whether to answer directly or invoke a tool.
**File**: `src/agent.py:118`

**Non-obvious inputs**:
- `tools`: If provided, adds `tool_choice="auto"` to the request. Pass `None` to get a text-only response.

**Returns**:
- `{"content": str | None, "tool_calls": list | None}`
- `content` is `None` when the model returns only tool calls (normal behavior)
- On error: `{"content": "<error message>", "tool_calls": None}`

**Idempotency**: NOT SAFE — retries on `APIConnectionError` up to 3 times, but each attempt is a new LLM call.

**Failure modes**:
- `APIConnectionError` → retries 3x, then returns `"Connection error: Could not reach Azure OpenAI service"`
- 401/403 → returns `"Authentication error: Please check your API credentials"`
- 429 → returns `"Rate limited: Too many requests."`
- 404 → returns `"Deployment not found: Please check your Azure deployment configuration"`

---

## MemoryAgent._handle_tool_calls

**Summary**: Executes all tool calls in parallel, then makes a synthesis LLM call to produce the final response.
**File**: `src/agent.py:227`

**Non-obvious inputs**:
- `messages`: Should contain `[system, user_message, assistant_with_tool_calls]`. History is intentionally excluded — only current turn context needed.

**Returns**: `(final_response_str, updated_messages_list)`

**Side effects**:
- Each tool result is appended to `messages` as a `role: "tool"` message
- Makes a second LLM call with `tool_choice="none"` and `max_completion_tokens=16000`

**Failure modes**:
- Individual tool exceptions are caught and converted to `"Tool error: {e}"` strings
- Synthesis LLM failure → returns `"Error processing tool results: {e}"`

→ See also: `01_hazards.md#never-use-tool_choice-auto-on-the-synthesis-llm-call`

---

## MemoryAgent._store_episode_background

**Summary**: Fire-and-forget writer — stores the conversation turn in Graphiti with retry.
**File**: `src/agent.py:371`

**Non-obvious inputs**: None — always stores the full `"User: ...\nAgent: ..."` string.

**Side effects**:
- Writes `Episodic` node to Neo4j via `GraphitiMemoryClient.add_episode()`
- On retry: sleeps 2s before attempt 2, 4s before attempt 3

**Idempotency**: NOT SAFE — each call creates a new node with a unique ISO timestamp name.

**Failure modes**:
- 3 failed attempts → logs error, silently discards — user is never notified
- `"WARNING Episode storage failed (attempt N/3)"` in logs → transient, will retry
- `"ERROR Episode storage permanently failed"` → Graphiti or Neo4j is down

---

## SyncMemoryAgent.__init__

**Summary**: Creates the event loop, initializes MemoryAgent, and eagerly initializes Graphiti.
**File**: `src/agent.py:407`

**Side effects**:
- Creates and sets a new `asyncio` event loop via `asyncio.new_event_loop()`
- Runs `memory_client.initialize()` to completion before returning

**Invariants**: Must be called from a thread that does NOT already have a running event loop (i.e., the main thread).

**Failure modes**:
- Any exception during init propagates as-is — the agent is not safe to use if `__init__` raises

---

## SyncMemoryAgent.close

**Summary**: Closes Graphiti client, async agent, and event loop.
**File**: `src/agent.py:451`

**Side effects**:
- Calls `memory_client.close()` then `_async_agent.close()` then `self._loop.close()`
- Swallows exceptions from each step to ensure loop is always closed

**Non-obvious behavior**: Checks `self._async_agent.memory_client._graphiti` directly to decide whether to close — will silently skip if Graphiti never initialized.

→ See also: `01_hazards.md`, `02_business_logic.md`, `contracts/graphiti_client.md`
