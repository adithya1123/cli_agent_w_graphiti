# Contracts: tools
_Last updated: 2026-04-25_
_Covers: `src/tools.py`_

---

## WebSearchTool.search

**Summary**: Calls Tavily API and returns the raw JSON response.
**File**: `src/tools.py:26`

**Returns**:
- On success: dict with `"answer"` (str), `"results"` (list of dicts with `title`, `url`, `content`)
- On Tavily init failure: `{"error": "Search service not available", "results": []}`
- On search failure after 2 retries: `{"error": "Search failed: {msg}", "results": []}`

**Idempotency**: NOT SAFE — each call hits the Tavily API and incurs usage cost.

**Failure modes**:
- Tavily client is `None` (init failed) → returns error dict, does not raise
- Tavily API errors → retries once, then returns error dict

---

## WebSearchTool.format_search_results

**Summary**: Formats a raw Tavily response into a text string for the LLM.
**File**: `src/tools.py:66`

**Returns**:
- `"Search error: {msg}"` if `"error"` key present in response
- `"No results found"` if no answer and no results
- Multi-part string starting with `"Answer: ..."` (if present) then `"Sources:\n1. ..."` otherwise

**Non-obvious behavior**: Content per result is capped at 300 characters — truncated with `"..."`.

**Produces**: Formatted search result string — consumed by `MemoryAgent._handle_tool_calls()` as tool result content

---

## ToolRegistry.call_tool

**Summary**: Dispatches a tool call by name and returns the result as a string.
**File**: `src/tools.py:121`

**Returns**: Always returns a string. On unknown tool: `"Tool '{name}' not found"`. On tool exception: `"Error calling tool '{name}': {e}"`.

**Non-obvious behavior**: Tools are called synchronously. The agent wraps calls in `asyncio.to_thread()` with a 30-second timeout.

**Consumed by**: `MemoryAgent._execute_tool_call()` via `asyncio.to_thread()`

→ See also: `playbooks/add_tool.md`, `contracts/agent.md`
